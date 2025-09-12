#!/usr/bin/env python3
"""
Add SEC routes to the main app.py file
This script will safely add the SEC endpoints to the main backend
"""

import os
import sys

def add_sec_routes():
    """Add SEC routes to the existing app.py"""
    
    # Read the current app.py
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check if SEC routes are already added
    if '/api/sec/search' in content:
        print("✅ SEC routes already present in app.py")
        return
    
    # Find the position to insert the SEC routes (before the database creation)
    insert_position = content.find('# Create database tables')
    
    if insert_position == -1:
        print("❌ Could not find insertion point in app.py")
        return
    
    # SEC routes to add
    sec_routes = '''

# SEC Document Endpoints - Added by add_sec_routes.py
try:
    from sec_service import sec_service
    SEC_SERVICE_AVAILABLE = True
except ImportError:
    print("Warning: SEC service not available")
    SEC_SERVICE_AVAILABLE = False

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

@app.post("/api/sec/search")
@limiter.limit("20/minute")
async def search_sec_documents(
    request: SECSearchRequest, 
    req: Request,
    current_user: Optional[UserInfo] = Depends(get_current_user_optional)
):
    """Search for SEC documents by company name, ticker, or document type"""
    if not SEC_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="SEC service not available")
    
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
@limiter.limit("10/minute") 
async def get_sec_document(
    doc_id: str,
    req: Request,
    query: Optional[str] = None,
    current_user: Optional[UserInfo] = Depends(get_current_user_optional)
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

@app.get("/api/sec/company/{ticker}")
@limiter.limit("15/minute")
async def get_company_filings(
    ticker: str,
    req: Request,
    limit: Optional[int] = 10,
    current_user: Optional[UserInfo] = Depends(get_current_user_optional)
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


'''
    
    # Insert the SEC routes
    new_content = content[:insert_position] + sec_routes + content[insert_position:]
    
    # Write the updated content
    with open('app.py', 'w') as f:
        f.write(new_content)
    
    print("✅ SEC routes added to app.py successfully")

if __name__ == "__main__":
    add_sec_routes()