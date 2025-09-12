import requests
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SECService:
    def __init__(self):
        self.headers = {"User-Agent": "patbirnmail@gmail.com"}
        self.base_url = "https://www.sec.gov"
        self.data_url = "https://data.sec.gov"
        
        # Load company ticker data
        self._company_data = self._load_company_data()
    
    def _load_company_data(self) -> Dict:
        """Load company ticker to CIK mapping"""
        try:
            url = f"{self.base_url}/files/company_tickers.json"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to load company data: {e}")
            return {}
    
    def get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """Get CIK (Central Index Key) from ticker symbol"""
        ticker = ticker.upper()
        for entry in self._company_data.values():
            if entry.get("ticker") == ticker:
                return str(entry["cik_str"]).zfill(10)
        return None
    
    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Get company information from ticker"""
        ticker = ticker.upper()
        for entry in self._company_data.values():
            if entry.get("ticker") == ticker:
                return {
                    "ticker": ticker,
                    "title": entry.get("title", ""),
                    "cik": str(entry["cik_str"]).zfill(10)
                }
        return None
    
    def get_latest_filings(self, cik: str) -> Optional[Dict]:
        """Get latest filings for a company by CIK"""
        try:
            url = f"{self.data_url}/submissions/CIK{cik}.json"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get filings for CIK {cik}: {e}")
            return None
    
    def search_documents(self, query: str, limit: int = 50) -> List[Dict]:
        """Search for SEC documents by company name, ticker, or document type"""
        results = []
        query_lower = query.lower()
        
        # Search by ticker symbol first
        if len(query) <= 5 and query.isalpha():
            company_info = self.get_company_info(query)
            if company_info:
                filings = self.get_company_filings(company_info["cik"], limit=limit)
                results.extend(filings)
        
        # Search by company name
        if len(results) < limit:
            for entry in self._company_data.values():
                if (query_lower in entry.get("title", "").lower() or 
                    query_lower in entry.get("ticker", "").lower()):
                    cik = str(entry["cik_str"]).zfill(10)
                    filings = self.get_company_filings(cik)
                    results.extend(filings[:2])  # Limit per company
                    if len(results) >= limit:
                        break
        
        return results[:limit]
    
    def get_company_filings(self, cik: str, form_types: List[str] = None, limit: int = 50) -> List[Dict]:
        """Get recent filings for a company"""
        if form_types is None:
            form_types = ["10-K", "10-Q", "8-K", "DEF 14A"]
        
        filings_data = self.get_latest_filings(cik)
        if not filings_data:
            return []
        
        recent = filings_data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        dates = recent.get("filingDate", [])
        docs = recent.get("primaryDocument", [])
        
        company_name = filings_data.get("name", "Unknown Company")
        
        results = []
        for i, (form, accession, date, doc) in enumerate(zip(forms, accessions, dates, docs)):
            if form in form_types and len(results) < limit:
                # Create document URL
                acc_no_dash = accession.replace("-", "")
                doc_url = f"{self.base_url}/Archives/edgar/data/{int(cik)}/{acc_no_dash}/{doc}"
                
                results.append({
                    "id": f"{cik}_{accession}",
                    "title": f"Form {form}",
                    "company": company_name,
                    "ticker": self._get_ticker_from_cik(cik),
                    "documentType": form,
                    "filingDate": date,
                    "url": doc_url,
                    "accessionNumber": accession
                })
        
        return results
    
    def _get_ticker_from_cik(self, cik: str) -> str:
        """Get ticker symbol from CIK"""
        cik_int = int(cik)
        for entry in self._company_data.values():
            if entry.get("cik_str") == cik_int:
                return entry.get("ticker", "")
        return ""
    
    def get_document_content(self, url: str) -> Optional[str]:
        """Extract text content from SEC document"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Parse HTML and extract text
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Failed to get document content from {url}: {e}")
            return None
    
    def get_document_html(self, url: str) -> Optional[str]:
        """Get the original HTML content from SEC document for rendering"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Parse and clean the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove potentially problematic elements but keep structure
            for element in soup(["script", "meta", "link"]):
                element.decompose()
            
            # Convert relative URLs to absolute URLs for images and links
            for img in soup.find_all('img'):
                if img.get('src') and not img['src'].startswith('http'):
                    img['src'] = f"{self.base_url}{img['src']}"
            
            for link in soup.find_all('a'):
                if link.get('href') and not link['href'].startswith('http'):
                    link['href'] = f"{self.base_url}{link['href']}"
            
            # Add some basic styling to make it readable
            style_tag = soup.new_tag('style')
            style_tag.string = """
                body { 
                    font-family: Arial, sans-serif; 
                    line-height: 1.4; 
                    margin: 20px; 
                    font-size: 12px;
                }
                table { 
                    border-collapse: collapse; 
                    width: 100%; 
                    margin: 10px 0;
                }
                td, th { 
                    border: 1px solid #ddd; 
                    padding: 4px; 
                    text-align: left;
                }
                th { 
                    background-color: #f5f5f5; 
                    font-weight: bold;
                }
                .FormData { 
                    background-color: #f9f9f9; 
                    padding: 10px; 
                    margin: 10px 0;
                }
                hr { 
                    margin: 20px 0; 
                    border: 1px solid #ccc;
                }
                p { 
                    margin: 8px 0; 
                }
            """
            if soup.head:
                soup.head.append(style_tag)
            else:
                # If no head tag, create one
                head_tag = soup.new_tag('head')
                head_tag.append(style_tag)
                if soup.html:
                    soup.html.insert(0, head_tag)
                else:
                    soup.insert(0, head_tag)
            
            return str(soup)
        except Exception as e:
            logger.error(f"Failed to get document HTML from {url}: {e}")
            return None
    
    def search_document_content(self, content: str, query: str) -> List[Dict]:
        """Search for query terms within document content and return highlights"""
        if not content or not query:
            return []
        
        highlights = []
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Split content into sentences/paragraphs
        sentences = re.split(r'[.!?]\s+', content)
        
        for i, sentence in enumerate(sentences):
            if query_lower in sentence.lower() and len(sentence.strip()) > 20:
                highlights.append({
                    "text": sentence.strip(),
                    "page": (i // 20) + 1,  # Rough page estimation
                    "position": {
                        "top": (i % 20) * 30,
                        "left": 50,
                        "width": 500,
                        "height": 25
                    }
                })
                
                # Limit to 10 highlights
                if len(highlights) >= 10:
                    break
        
        return highlights

# Global instance
sec_service = SECService()