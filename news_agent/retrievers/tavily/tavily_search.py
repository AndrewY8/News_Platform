# Tavily API Retriever

# libraries
import os
from typing import Literal, Sequence, Optional
import requests
import json


class TavilyRetriever:
    """
    Tavily API Retriever
    """

    def __init__(self, query, headers=None, topic="general", query_domains=None):
        """
        Initializes the TavilySearch object.

        Args:
            query (str): The search query string.
            headers (dict, optional): Additional headers to include in the request. Defaults to None.
            topic (str, optional): The topic for the search. Defaults to "general".
            query_domains (list, optional): List of domains to include in the search. Defaults to None.
        """
        self.query = query
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}",
        }
        self.topic = topic
        self.base_url = "https://api.tavily.com/search"
        self.api_key = self.get_api_key()
        # self.headers = {
        #     "Content-Type": "application/json",
        # }
        self.query_domains = query_domains or None

    def get_api_key(self):
        """
        Gets the Tavily API key
        Returns:

        """
        api_key = self.headers.get("tavily_api_key")
        if not api_key:
            try:
                api_key = os.environ["TAVILY_API_KEY"]
            except KeyError:
                print(
                    "Tavily API key not found, set to blank. If you need a retriver, please set the TAVILY_API_KEY environment variable."
                )
                return ""
        return api_key


    def _search(
        self,
        query: str,
        search_depth: Literal["basic", "advanced"] = "basic",
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
        # "topic": topic,
        "days": days,
        "max_results": max_results,
        "include_answer": include_answer,
    }
        # if include_domains:
        #     data["include_domains"] = include_domains
        # if exclude_domains:
        #     data["exclude_domains"] = exclude_domains
        print(data)
        
        response = requests.post(
        self.base_url,
        headers=self.headers,
        json=data,   # ✅ better than data=json.dumps(...)
        timeout=100
    )

        if response.status_code == 200:
            return response.json()
        else:
            # Raises a HTTPError if the HTTP request returned an unsuccessful status code
            response.raise_for_status()

    def search(self, 
        search_depth: Literal["basic", "advanced"] = "basic",
        topic: str = "general",
        days: int = 30,
        max_results: int = 10,
        include_answer: bool = False):
        """
        Searches the query
        Returns:

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
                raise Exception("No results found with Tavily API search.")
            # Return the results
            search_response = [
                {"href": obj["url"], "body": obj["content"]} for obj in sources
            ]
        except Exception as e:
            print(f"Error: {e}. Failed fetching sources. Resulting in empty response.")
            search_response = []
        return search_response
