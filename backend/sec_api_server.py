#!/usr/bin/env python3
"""
Standalone SEC API Server
This provides the SEC document search functionality without the dependency conflicts
"""

import sys
import os
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import logging

# Import SEC service
from sec_service import sec_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SEC Document Search API",
    description="Search and retrieve SEC documents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class SECSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

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

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "SEC Document Search API", "status": "running"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "sec-api"}

@app.post("/api/sec/search")
async def search_sec_documents(request: SECSearchRequest):
    """Search for SEC documents by company name, ticker, or document type"""
    try:
        logger.info(f"SEC search request: {request.query}")
        
        # Search for documents
        documents = sec_service.search_documents(request.query, request.limit)
        
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

@app.get("/api/sec/document/{doc_id}")
async def get_sec_document(
    doc_id: str,
    query: Optional[str] = None
):
    """Get full SEC document content with optional query highlighting"""
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

@app.get("/api/sec/company/{ticker}")
async def get_company_filings(
    ticker: str,
    limit: Optional[int] = 10
):
    """Get recent SEC filings for a specific company by ticker"""
    try:
        # Get CIK from ticker
        cik = sec_service.get_cik_from_ticker(ticker)
        if not cik:
            raise HTTPException(status_code=404, detail=f"Company not found for ticker: {ticker}")
        
        # Get company filings
        filings = sec_service.get_company_filings(cik)
        
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

if __name__ == "__main__":
    print("🔍 Starting SEC Document Search API...")
    print("=" * 50)
    print("🌐 Server will run on: http://localhost:8004")
    print("📚 API docs available at: http://localhost:8004/docs")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    uvicorn.run(
        "sec_api_server:app",
        host="0.0.0.0",
        port=8004,  # Use the standard backend port
        reload=True,
        log_level="info"
    )