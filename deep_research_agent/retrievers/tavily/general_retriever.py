# General Sources Tavily Retriever (excludes trusted news domains)

import os
from typing import Literal, List, Optional
import requests
import json
from .trusted_news_retriever import TrustedNewsRetriever

class GeneralRetriever:
    """
    Tavily API Retriever that excludes trusted news sources to find diverse, alternative sources
    """

    def __init__(self, query: str, headers: Optional[dict] = None, topic: str = "general"):
        """
        Initializes the GeneralRetriever object.

        Args:
            query (str): The search query string.
            headers (dict, optional): Additional headers to include in the request. Defaults to None.
            topic (str, optional): The topic for the search. Defaults to "general".
        """
        self.query = query
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}",
        }
        self.topic = topic
        self.base_url = "https://api.tavily.com/search"
        self.api_key = self.get_api_key()
        # Use the same trusted domains list but for exclusion
        self.excluded_domains = TrustedNewsRetriever.TRUSTED_DOMAINS

    def get_api_key(self) -> str:
        """
        Gets the Tavily API key
        """
        api_key = self.headers.get("tavily_api_key")
        if not api_key:
            try:
                api_key = os.environ["TAVILY_API_KEY"]
            except KeyError:
                print(
                    "Tavily API key not found, set to blank. If you need a retriever, please set the TAVILY_API_KEY environment variable."
                )
                return ""
        return api_key

    def _search(
        self,
        query: str,
        search_depth: Literal["basic", "advanced"] = "advanced",
        topic: str = "general",
        days: int = 30,
        max_results: int = 10,
        include_answer: bool = False,
    ) -> dict:
        """
        Internal search method to send the request to the API.
        """

        data = {
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "days": days,
            "max_results": max_results,
            "include_answer": include_answer,
            "exclude_domains": self.excluded_domains  # Exclude trusted domains
        }

        print(f"GeneralRetriever searching: {query}")
        print(f"Excluding domains: {len(self.excluded_domains)} trusted sources")

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=data,
            timeout=100
        )

        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def search(self,
        search_depth: Literal["basic", "advanced"] = "advanced",
        topic: str = "general",
        days: int = 30,
        max_results: int = 10,
        include_answer: bool = False
    ) -> List[dict]:
        """
        Searches the query against general sources (excluding trusted news)
        """
        try:
            # Search the query
            results = self._search(
                self.query,
                search_depth,
                topic,
                days,
                max_results,
                include_answer
            )
            sources = results.get("results", [])
            if not sources:
                print(f"No results found from general sources for query: {self.query}")
                return []

            # Return the results with complete metadata
            search_response = [
                {
                    "href": obj.get("url"),
                    "url": obj.get("url"),
                    "body": obj.get("content"),
                    "content": obj.get("content"),
                    "title": obj.get("title"),
                    "source": obj.get("domain") or obj.get("url", "").split("//")[-1].split("/")[0] if obj.get("url") else "Unknown",
                    "published_date": obj.get("published_date"),
                    "score": obj.get("score"),
                    "raw_content": obj.get("raw_content"),
                    "retriever_type": "general"  # Tag for identification
                } for obj in sources
            ]

            print(f"GeneralRetriever found {len(search_response)} results")
            return search_response

        except Exception as e:
            print(f"Error in GeneralRetriever: {e}. Failed fetching sources. Resulting in empty response.")
            return []