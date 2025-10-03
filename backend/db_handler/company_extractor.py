import os
from typing import List, Dict
from openai import OpenAI
from pydantic import BaseModel

class Company(BaseModel):
    """Individual company information"""
    name: str
    ticker: str

class CompanyExtraction(BaseModel):
    """Schema for company extraction results"""
    companies: List[Company]

class CompanyExtractor:
    """Extract relevant companies from news articles using LLM"""

    def __init__(self, api_key: str = None):
        """Initialize the company extractor with OpenAI API key"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)

    def extract_companies(self, article_title: str, article_content: str, max_companies: int = 10) -> List[Dict[str, str]]:
        """
        Extract the most relevant companies from an article

        Args:
            article_title: The title of the article
            article_content: The full content/body of the article
            max_companies: Maximum number of companies to extract (default 10)

        Returns:
            List of dictionaries with company information:
            [
                {
                    "name": "Company Name",
                    "ticker": "TICKER" or "Private",
                    "relevance_reason": "Why this company is relevant"
                }
            ]
        """

        prompt = f"""Extract up to {max_companies} companies most relevant to this news:

Title: {article_title}
Content: {article_content[:500]}...

Return JSON with "companies" array. Each company needs:
- "name": Company name
- "ticker": Stock symbol or "Private"
- "relevance_reason": Brief explanation

Focus on: mentioned companies, direct competitors, major industry players affected.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst. Return ONLY a valid JSON object with a 'companies' array."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=500,
                timeout=10,
                response_format={"type": "json_object"}
            )

            # Parse the JSON response
            import json
            result = json.loads(response.choices[0].message.content)
            companies = result.get('companies', [])

            # Ensure each company has the required fields
            formatted_companies = []
            for company in companies:
                if isinstance(company, dict) and 'name' in company:
                    formatted_companies.append({
                        "name": company.get('name', ''),
                        "ticker": company.get('ticker', 'Private'),
                        "relevance_reason": company.get('relevance_reason', '')
                    })

            return formatted_companies

        except Exception as e:
            print(f"❌ Error extracting companies: {e}")
            return []

    def extract_companies_simple(self, article_title: str, article_content: str) -> List[str]:
        """
        Simple version that returns just company names as a list
        """
        companies = self.extract_companies(article_title, article_content)
        return [company["name"] for company in companies]