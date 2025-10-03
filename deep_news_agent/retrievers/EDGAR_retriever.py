# SEC EDGAR API Retriever

# libraries
import os
import requests
import json
import re
from typing import List, Dict, Optional, Union
from bs4 import BeautifulSoup


class EDGARRetriever:
    """
    SEC EDGAR API Retriever for company filings and information
    """

    def __init__(
        self, form_types: Optional[List[str]] = None, query_domains=None
    ):
        """
        Initializes the EDGAR retriever object.

        Args:
            query (str): Company name, ticker symbol, or CIK number
            form_types (list, optional): List of form types to filter (e.g., ['10-K', '10-Q', '8-K'])
            query_domains: Not used for EDGAR but kept for consistency with other retrievers
        """
        self.query = ""
        self.form_types = form_types or ["10-K", "10-Q", "8-K", "DEF 14A"]
        self.base_url = "https://data.sec.gov"
        self.sec_files_url = "https://www.sec.gov"
        self.headers = {
            "User-Agent": "News Agent Retriever (andre@example.com)",  # SEC requires User-Agent header
            "Accept": "application/json",
        }
        self.company_tickers = None
    
    def setQuery(self, query):
        """
        Updates the self.query object"""
        self.query = query

    def _load_company_tickers(self) -> Dict:
        """
        Load the company tickers JSON file from SEC to map tickers to CIK numbers.

        Returns:
            Dict containing company ticker mappings
        """
        if self.company_tickers is not None:
            return self.company_tickers

        try:
            url = f"{self.sec_files_url}/files/company_tickers.json"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            self.company_tickers = response.json()
            return self.company_tickers
        except Exception as e:
            print(f"Error loading company tickers: {e}")
            return {}

    def _find_cik_by_ticker(self, ticker: str) -> Optional[str]:
        """
        Find CIK number by ticker symbol.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            CIK number as string with leading zeros, or None if not found
        """
        tickers_data = self._load_company_tickers()
        ticker = ticker.upper().strip()

        for entry in tickers_data.values():
            if isinstance(entry, dict) and entry.get("ticker", "").upper() == ticker:
                cik = entry.get("cik_str")
                if cik:
                    return str(cik).zfill(10)  # Pad with leading zeros to 10 digits
        return None

    def _find_cik_by_name(self, company_name: str) -> Optional[str]:
        """
        Find CIK number by company name (fuzzy matching).

        Args:
            company_name: Company name to search for

        Returns:
            CIK number as string with leading zeros, or None if not found
        """
        tickers_data = self._load_company_tickers()
        company_name = company_name.lower().strip()

        # First try exact match
        for entry in tickers_data.values():
            if isinstance(entry, dict):
                title = entry.get("title", "").lower()
                if company_name in title or title in company_name:
                    cik = entry.get("cik_str")
                    if cik:
                        return str(cik).zfill(10)
        return None

    def _normalize_cik(self, cik: Union[str, int]) -> str:
        """
        Normalize CIK to 10-digit string with leading zeros.

        Args:
            cik: CIK number as string or integer

        Returns:
            Normalized CIK string
        """
        return str(cik).zfill(10)

    def _get_company_submissions(self, cik: str, max_results: int = 10) -> List[Dict]:
        """
        Get recent filings for a company by CIK.

        Args:
            cik: 10-digit CIK number
            max_results: Maximum number of results to return

        Returns:
            List of filing information dictionaries
        """
        try:
            url = f"{self.base_url}/submissions/CIK{cik}.json"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            filings = data.get("filings", {}).get("recent", {})
            if not filings:
                return []

            results = []
            forms = filings.get("form", [])
            filing_dates = filings.get("filingDate", [])
            accession_numbers = filings.get("accessionNumber", [])
            primary_documents = filings.get("primaryDocument", [])

            for i, form_type in enumerate(forms):
                if len(results) >= max_results:
                    break

                # Filter by form types if specified
                if self.form_types and form_type not in self.form_types:
                    continue

                if i < len(filing_dates) and i < len(accession_numbers):
                    accession_no = accession_numbers[i].replace("-", "")
                    document_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no}/{primary_documents[i] if i < len(primary_documents) else 'filing-details.html'}"

                    filing_info = {
                        "href": document_url,
                        "body": f"Form {form_type} filed on {filing_dates[i]} by {data.get('name', 'Unknown Company')}. "
                        f"CIK: {cik}. Access filing details and documents at SEC.gov.",
                        "title": f"{data.get('name', 'Company')} - Form {form_type}",
                        "filing_date": filing_dates[i],
                        "form_type": form_type,
                        "cik": cik,
                        "accession_number": accession_numbers[i],
                    }
                    results.append(filing_info)

            return results

        except Exception as e:
            print(f"Error fetching company submissions for CIK {cik}: {e}")
            return []

    def get_company_facts(self, cik: str = None) -> Dict:
        """
        Get company facts (XBRL data) for a specific CIK.

        Args:
            cik: CIK number. If None, uses the CIK from current query.

        Returns:
            Dict containing company facts data
        """
        if cik is None:
            if self.query.isdigit():
                cik = self._normalize_cik(self.query)
            else:
                cik = self._find_cik_by_ticker(self.query) or self._find_cik_by_name(
                    self.query
                )

        if not cik:
            return {}

        try:
            url = f"{self.base_url}/api/xbrl/companyfacts/CIK{cik}.json"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching company facts for CIK {cik}: {e}")
            return {}

    def get_transcript_content(self, filing_url: str) -> Optional[str]:
        """
        Fetches the content of a given filing URL and attempts to extract the transcript.
        This is a simplified example and may need more robust parsing for different filing structures.

        Args:
            filing_url (str): The URL of the SEC filing document (e.g., an 8-K HTML document).

        Returns:
            Optional[str]: The extracted transcript content as a single string, or None if extraction fails.
        """
        try:
            print(f"Attempting to fetch transcript from: {filing_url}")
            response = requests.get(filing_url, headers=self.headers, timeout=60)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script_or_style in soup(["script", "style"]):
                script_or_style.extract()

            text = soup.get_text()
            
            # Break into lines and remove leading/trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)

            # Further refinement: look for common transcript patterns
            # This part might need to be more sophisticated depending on the actual HTML structure
            # For now, we'll return the cleaned text.
            return text

        except requests.exceptions.RequestException as e:
            print(f"Error fetching filing from {filing_url}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing transcript from {filing_url}: {e}")
            return None

    def get_transcript_content(self, filing_url: str) -> Optional[str]:
        """
        Fetches and extracts content from an SEC filing URL.
        Handles both HTML and plain text filings.

        Args:
            filing_url (str): The URL of the SEC filing document.

        Returns:
            Optional[str]: The extracted content, or None if extraction fails.
        """
        try:
            print(f"Fetching content from: {filing_url}")
            response = requests.get(filing_url, headers=self.headers, timeout=60)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script, style, and meta elements
                for element in soup(["script", "style", "meta", "link"]):
                    element.extract()
                
                # Extract text
                text = soup.get_text(separator=' ', strip=True)
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
            else:
                # Plain text content
                text = response.text
            
            # Basic validation - ensure we got substantial content
            if len(text.strip()) < 100:
                print(f"Warning: Retrieved content is suspiciously short ({len(text)} chars)")
                return None
                
            return text
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching filing from {filing_url}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing content from {filing_url}: {e}")
            return None


    def transcript(
        self, 
        cik: Optional[str] = None, 
        form_type: str = "8-K", 
        max_results: int = 1,
        return_metadata: bool = False
    ) -> Optional[Union[str, Dict]]:
        """
        Retrieves the most recent filing content for a company.
        
        Note: This method retrieves the full filing content. For actual earnings call
        transcripts, you may need to use specialized services like AlphaSense or 
        Seeking Alpha, as raw SEC filings may not contain the full transcript text.

        Args:
            cik (str, optional): The CIK number. If None, derives from self.query.
            form_type (str): The SEC form type to search for (default: "8-K").
                            Common types: "8-K" (current reports), "10-Q" (quarterly),
                            "10-K" (annual), "DEF 14A" (proxy statements).
            max_results (int): Maximum number of filings to retrieve (default: 1).
            return_metadata (bool): If True, returns dict with content and metadata.

        Returns:
            Optional[Union[str, Dict]]: The filing content as string, or dict with
                                        metadata if return_metadata=True, or None if not found.
        """
        # Resolve CIK if not provided
        if cik is None:
            if self.query.isdigit():
                cik = self._normalize_cik(self.query)
            else:
                cik = self._find_cik_by_ticker(self.query) or self._find_cik_by_name(self.query)
        
        if not cik:
            print(f"Error: Could not resolve CIK for query '{self.query}'")
            return None
        
        # Temporarily override form_types for this search
        original_form_types = self.form_types
        self.form_types = [form_type]
        
        try:
            filings = self._get_company_submissions(cik, max_results=max_results)
            
            if not filings:
                print(f"No {form_type} filings found for CIK {cik}")
                return None
            
            # Get the most recent filing
            filing = filings[0]
            filing_url = filing.get("href")
            
            if not filing_url:
                print("Error: No URL found for filing")
                return None
            
            content = self.get_transcript_content(filing_url)
            
            if content is None:
                print("Failed to retrieve filing content")
                return None
            
            if return_metadata:
                return {
                    "content": content,
                    "filing_date": filing.get("filing_date"),
                    "form_type": filing.get("form_type"),
                    "url": filing_url,
                    "accession_number": filing.get("accession_number"),
                    "cik": cik
                }
            
            return content
            
        finally:
            # Restore original form_types
            self.form_types = original_form_types


    def systemPrompt(self, company_name: Optional[str] = None) -> str:
        """
        Returns a system prompt for financial analysis of SEC filings.
        
        Args:
            company_name (str, optional): Name of the company to customize the prompt.
                                        If None, uses generic "the company".
        
        Returns:
            str: System prompt for analyzing SEC filing content.
        """
        company_ref = company_name if company_name else "the company"
        
        return f"""You are an experienced financial analyst specializing in SEC filings analysis.

    Your task is to extract and summarize the most significant insights from this SEC filing that could materially impact {company_ref}'s business, financial performance, or stock valuation.

    Focus on identifying:

    **Financial Performance & Guidance**
    - Revenue growth or decline by segment/product line with underlying drivers
    - Margin trends and cost structure changes
    - Guidance revisions and management commentary on outlook
    - Cash flow, liquidity, and capital allocation decisions

    **Strategic Developments**
    - New product launches, market expansions, or business model changes  
    - Mergers, acquisitions, divestitures, or restructuring activities
    - Capital investments (factories, R&D, infrastructure)
    - Strategic partnerships or joint ventures

    **Operational & Market Dynamics**
    - Supply chain disruptions, dependencies, or optimizations
    - Competitive positioning and market share trends
    - Customer concentration or changes in key relationships
    - Operational efficiency improvements or challenges

    **Risk Factors & External Events**
    - Regulatory changes, litigation, or compliance issues
    - Geopolitical impacts (tariffs, trade restrictions, sanctions)
    - Macroeconomic sensitivities (interest rates, inflation, FX)
    - Technology disruptions or cybersecurity concerns

    **Management Insights**
    - Changes in executive leadership or board composition
    - Management's tone and confidence level
    - Long-term strategic vision and priorities

    For each key insight, briefly explain:
    1. What changed or was disclosed
    2. Why it matters to the company's future performance
    3. The potential impact (positive, negative, or uncertain)

    Prioritize material information that investors would find actionable. Avoid restating routine disclosures or boilerplate language."""