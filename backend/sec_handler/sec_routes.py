"""
SEC Routes Module
Contains all SEC-related FastAPI endpoints that can be imported into the main app.
"""

import logging
from typing import List, Dict, Optional
from fastapi import HTTPException, Request, Depends
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

# Import services
from sec_service import sec_service

logger = logging.getLogger(__name__)

# Initialize rate limiter (will use the same one from main app)
limiter = Limiter(key_func=get_remote_address)

# Import auth dependencies (these will be passed from main app)
get_current_user_optional = None  # Will be set when routes are added

# SEC service availability check
try:
    SEC_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("SEC service not available")
    SEC_SERVICE_AVAILABLE = False

# SEC RAG service availability check
try:
    from sec_rag_service import sec_rag_service
    SEC_RAG_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("SEC RAG service not available")
    SEC_RAG_SERVICE_AVAILABLE = False

# Pydantic Models
class SECSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 50

class SECDocumentResponse(BaseModel):
    id: str
    title: str
    company: str
    ticker: str
    documentType: str
    filingDate: str
    url: str
    content: Optional[str] = None
    html_content: Optional[str] = None
    highlights: Optional[List[Dict]] = None

class SECRAGQueryRequest(BaseModel):
    document_id: str
    query: str
    top_k: Optional[int] = 5

class SECRAGResponse(BaseModel):
    answer: str
    chunks: List[Dict]
    document_info: Optional[Dict] = None
    metadata: Optional[Dict] = None
    query: str
    error: Optional[str] = None

# SEC Route Functions
async def search_sec_documents(
    sec_request: SECSearchRequest,
    request: Request,
    current_user = None
):
    """Search for SEC documents by company name, ticker, or document type"""
    if not SEC_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC service not available")

    try:
        logger.info(f"SEC search request: {sec_request.query}")

        # Search for documents
        documents = sec_service.search_documents(sec_request.query, sec_request.limit)

        # Format response
        response_docs = []
        for doc in documents:
            response_docs.append(SECDocumentResponse(
                id=doc["id"],
                title=doc["title"],
                company=doc["company"],
                ticker=doc["ticker"],
                documentType=doc["documentType"],
                filingDate=doc["filingDate"],
                url=doc["url"]
            ))

        return {"documents": response_docs}

    except Exception as e:
        logger.error(f"Error in SEC search: {e}")
        raise HTTPException(status_code=500, detail="Failed to search SEC documents")

async def get_sec_document(
    doc_id: str,
    query: Optional[str] = None,
    request: Request = None,
    current_user = None
):
    """Get full SEC document content with optional query highlighting"""
    if not SEC_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC service not available")

    try:
        # Parse document ID (format: cik_accession)
        parts = doc_id.split("_", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid document ID format")

        cik, accession = parts

        # Get document URL
        acc_no_dash = accession.replace("-", "")
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}"

        # Get filings to find the primary document
        filings_data = sec_service.get_latest_filings(cik)
        if not filings_data:
            raise HTTPException(status_code=404, detail="Document not found")

        # Find the specific filing
        recent = filings_data.get("filings", {}).get("recent", {})
        accessions = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])

        primary_doc = None
        form_type = None
        filing_date = None

        for i, acc in enumerate(accessions):
            if acc == accession:
                primary_doc = docs[i] if i < len(docs) else None
                form_type = forms[i] if i < len(forms) else "Unknown"
                filing_date = dates[i] if i < len(dates) else "Unknown"
                break

        if not primary_doc:
            raise HTTPException(status_code=404, detail="Primary document not found")

        # Construct full URL
        full_url = f"{doc_url}/{primary_doc}"

        # Get document content (both text and HTML)
        content = sec_service.get_document_content(full_url)
        html_content = sec_service.get_document_html(full_url)
        if not content and not html_content:
            raise HTTPException(status_code=404, detail="Failed to retrieve document content")

        # Generate highlights if query provided
        highlights = []
        if query:
            highlights = sec_service.search_document_content(content, query)

        # Get company name
        company_name = filings_data.get("name", "Unknown Company")
        ticker = sec_service._get_ticker_from_cik(cik)

        return SECDocumentResponse(
            id=doc_id,
            title=f"Form {form_type}",
            company=company_name,
            ticker=ticker,
            documentType=form_type,
            filingDate=filing_date,
            url=full_url,
            content=content,
            html_content=html_content,
            highlights=highlights
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SEC document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")

async def get_company_filings(
    ticker: str,
    limit: Optional[int] = 50,
    request: Request = None,
    current_user = None
):
    """Get recent SEC filings for a specific company by ticker"""
    if not SEC_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC service not available")

    try:
        # Get CIK from ticker
        cik = sec_service.get_cik_from_ticker(ticker)
        if not cik:
            raise HTTPException(status_code=404, detail=f"Company not found for ticker: {ticker}")

        # Get company filings
        filings = sec_service.get_company_filings(cik, limit=limit)

        # Format response
        response_docs = []
        for filing in filings[:limit]:
            response_docs.append(SECDocumentResponse(
                id=filing["id"],
                title=filing["title"],
                company=filing["company"],
                ticker=filing["ticker"],
                documentType=filing["documentType"],
                filingDate=filing["filingDate"],
                url=filing["url"]
            ))

        return {"documents": response_docs}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting filings for ticker {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve company filings")

# SEC RAG Route Functions
async def query_sec_document_rag(
    rag_request: SECRAGQueryRequest,
    request: Request,
    current_user = None
):
    """Query a SEC document using RAG (Retrieval-Augmented Generation)"""
    if not SEC_RAG_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC RAG service not available")

    try:
        logger.info(f"SEC RAG query for document {rag_request.document_id}: {rag_request.query}")

        # First, ensure document is processed
        document_processed = await sec_rag_service.process_document(rag_request.document_id)
        if not document_processed:
            raise HTTPException(status_code=500, detail="Failed to process document for RAG")

        # Query the document
        result = sec_rag_service.query_document(rag_request.document_id, rag_request.query, rag_request.top_k)

        return SECRAGResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in SEC RAG query: {e}")
        raise HTTPException(status_code=500, detail="Failed to process RAG query")

async def process_sec_document_for_rag(
    doc_id: str,
    request: Request,
    force_refresh: Optional[bool] = False,
    current_user = None
):
    """Process a SEC document for RAG queries"""
    if not SEC_RAG_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC RAG service not available")

    try:
        logger.info(f"Processing SEC document for RAG: {doc_id}")

        success = await sec_rag_service.process_document(doc_id, force_refresh=force_refresh)

        if success:
            status_info = sec_rag_service.get_document_status(doc_id)
            return {
                "status": "success",
                "document_id": doc_id,
                "message": f"Document processed successfully into {status_info['chunk_count']} chunks",
                **status_info
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process document")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process document for RAG")

async def get_sec_document_rag_status(
    doc_id: str,
    request: Request,
    current_user = None
):
    """Get RAG processing status for a SEC document"""
    if not SEC_RAG_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC RAG service not available")

    try:
        status_info = sec_rag_service.get_document_status(doc_id)
        return {
            "document_id": doc_id,
            **status_info
        }

    except Exception as e:
        logger.error(f"Error getting RAG status for document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document status")

# Function to add all SEC routes to the FastAPI app
def add_sec_routes(app, limiter_instance, get_current_user_optional_func):
    """
    Add all SEC routes to the FastAPI app

    Args:
        app: FastAPI application instance
        limiter_instance: Rate limiter instance from main app
        get_current_user_optional_func: Authentication dependency function
    """
    global limiter, get_current_user_optional
    limiter = limiter_instance
    get_current_user_optional = get_current_user_optional_func

    # Add SEC Document Search endpoints
    @app.post("/api/sec/search")
    @limiter.limit("20/minute")
    async def sec_search_endpoint(
        sec_request: SECSearchRequest,
        request: Request,
        current_user = Depends(get_current_user_optional)
    ):
        return await search_sec_documents(sec_request, request, current_user)

    @app.get("/api/sec/document/{doc_id}")
    @limiter.limit("10/minute")
    async def sec_document_endpoint(
        doc_id: str,
        query: Optional[str] = None,
        request: Request = None,
        current_user = Depends(get_current_user_optional)
    ):
        return await get_sec_document(doc_id, query, request, current_user)

    @app.get("/api/sec/company/{ticker}")
    @limiter.limit("15/minute")
    async def sec_company_endpoint(
        ticker: str,
        limit: Optional[int] = 50,
        request: Request = None,
        current_user = Depends(get_current_user_optional)
    ):
        return await get_company_filings(ticker, limit, request, current_user)

    # Add SEC RAG endpoints
    @app.post("/api/sec/rag/query")
    @limiter.limit("10/minute")
    async def sec_rag_query_endpoint(
        rag_request: SECRAGQueryRequest,
        request: Request,
        current_user = Depends(get_current_user_optional)
    ):
        return await query_sec_document_rag(rag_request, request, current_user)

    @app.post("/api/sec/rag/process/{doc_id}")
    @limiter.limit("5/minute")
    async def sec_rag_process_endpoint(
        doc_id: str,
        request: Request,
        force_refresh: Optional[bool] = False,
        current_user = Depends(get_current_user_optional)
    ):
        return await process_sec_document_for_rag(doc_id, request, force_refresh, current_user)

    @app.get("/api/sec/rag/status/{doc_id}")
    @limiter.limit("20/minute")
    async def sec_rag_status_endpoint(
        doc_id: str,
        request: Request,
        current_user = Depends(get_current_user_optional)
    ):
        return await get_sec_document_rag_status(doc_id, request, current_user)

    logger.info("✅ SEC routes added to FastAPI app")