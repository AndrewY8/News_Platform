# SEC EDGAR API Retriever

# libraries
import os
import requests
import json
import re
from typing import List, Dict, Optional, Union


class EDGARRetriever:
    """
    SEC EDGAR API Retriever for company filings and information
    """

    def __init__(
        self, query: str, form_types: Optional[List[str]] = None, query_domains=None
    ):
        """
        Initializes the EDGAR retriever object.

        Args:
            query (str): Company name, ticker symbol, or CIK number
            form_types (list, optional): List of form types to filter (e.g., ['10-K', '10-Q', '8-K'])
            query_domains: Not used for EDGAR but kept for consistency with other retrievers
        """
        self.query = query
        self.form_types = form_types or ["10-K", "10-Q", "8-K", "DEF 14A"]
        self.base_url = "https://data.sec.gov"
        self.sec_files_url = "https://www.sec.gov"
        self.headers = {
            "User-Agent": "News Agent Retriever (andre@example.com)",  # SEC requires User-Agent header
            "Accept": "application/json",
        }
        self.company_tickers = None

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

    def search(self, max_results: int = 10) -> List[Dict]:
        """
        Search for company filings based on the query.

        Args:
            max_results: Maximum number of results to return

        Returns:
            List of search results with href, body, title, and additional metadata
        """
        try:
            # Check if query is already a CIK number
            if self.query.isdigit():
                cik = self._normalize_cik(self.query)
            else:
                # Try to find CIK by ticker first
                cik = self._find_cik_by_ticker(self.query)

                # If not found by ticker, try by company name
                if not cik:
                    cik = self._find_cik_by_name(self.query)

            if not cik:
                print(f"Could not find CIK for query: {self.query}")
                return []

            print(f"Found CIK {cik} for query '{self.query}'")

            # Get company submissions
            results = self._get_company_submissions(cik, max_results)

            if not results:
                # Return basic company info if no recent filings
                tickers_data = self._load_company_tickers()
                company_name = "Unknown Company"
                ticker = ""

                for entry in tickers_data.values():
                    if isinstance(entry, dict) and entry.get("cik_str") == int(cik):
                        company_name = entry.get("title", company_name)
                        ticker = entry.get("ticker", "")
                        break

                return [
                    {
                        "href": f"https://www.sec.gov/edgar/browse/?CIK={cik}",
                        "body": f"Company: {company_name} (Ticker: {ticker}, CIK: {cik}). "
                        f"View all SEC filings and company information on EDGAR database.",
                        "title": f"{company_name} - SEC EDGAR Profile",
                        "cik": cik,
                        "company_name": company_name,
                        "ticker": ticker,
                    }
                ]

            return results

        except Exception as e:
            print(f"Error searching EDGAR for '{self.query}': {e}")
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
