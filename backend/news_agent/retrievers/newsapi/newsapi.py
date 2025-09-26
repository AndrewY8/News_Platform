# NewsAPI Retriever

# libraries
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class NewsAPIRetriever:
    """
    NewsAPI Retriever for fetching news articles
    API Documentation: https://newsapi.org/docs
    """

    def __init__(
        self, query: str, sources: Optional[List[str]] = None, query_domains=None
    ):
        """
        Initializes the NewsAPI retriever object.

        Args:
            query (str): Search query for news articles
            sources (list, optional): List of news sources to search (e.g., ['bbc-news', 'cnn'])
            query_domains: Not used for NewsAPI but kept for consistency with other retrievers
        """
        self.query = query
        self.sources = sources
        self.base_url = "https://newsapi.org/v2"
        self.api_key = self._get_api_key()
        self.headers = {"X-API-KEY": self.api_key, "User-Agent": "News Agent Retriever"}

    def _get_api_key(self) -> str:
        """
        Retrieves the NewsAPI key from environment variables.

        Returns:
            The API key

        Raises:
            Exception: If the API key is not found
        """
        try:
            api_key = os.environ["NEWS_API_KEY"]
            if not api_key or api_key == "":
                raise KeyError("Empty API key")
            return api_key
        except KeyError:
            raise Exception(
                "NewsAPI key not found. Please set the NEWS_API_KEY environment variable. "
                "You can get a free API key from https://newsapi.org/"
            )

    def get_top_headlines(
        self,
        max_results: int = 10,
        country: str = "us",
        category: Optional[str] = None,
        language: str = "en",
    ) -> List[Dict]:
        """
        Get top headlines from NewsAPI.

        Args:
            max_results: Maximum number of results to return (max 100)
            country: Country code for headlines (e.g., 'us', 'gb', 'ca')
            category: News category (business, entertainment, general, health, science, sports, technology)
            language: Language code (e.g., 'en', 'es', 'fr')

        Returns:
            List of news article dictionaries
        """
        try:
            url = f"{self.base_url}/top-headlines"
            params = {
                "q": self.query,
                "country": country,
                "language": language,
                "pageSize": min(max_results, 100),  # NewsAPI limit is 100
            }

            if category:
                params["category"] = category

            if self.sources:
                # Remove country param if sources are specified (NewsAPI requirement)
                del params["country"]
                params["sources"] = ",".join(self.sources)

            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                print(f"NewsAPI Error: {data.get('message', 'Unknown error')}")
                return []

            articles = data.get("articles", [])
            return self._format_articles(articles)

        except Exception as e:
            print(f"Error fetching top headlines: {e}")
            return []

    def get_everything(
        self,
        max_results: int = 10,
        sort_by: str = "publishedAt",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: str = "en",
    ) -> List[Dict]:
        """
        Search through millions of articles from over 80,000 large and small news sources and blogs.

        Args:
            max_results: Maximum number of results to return (max 100)
            sort_by: Sort order (publishedAt, relevancy, popularity)
            from_date: Oldest article date (YYYY-MM-DD format)
            to_date: Newest article date (YYYY-MM-DD format)
            language: Language code (e.g., 'en', 'es', 'fr')

        Returns:
            List of news article dictionaries
        """
        try:
            url = f"{self.base_url}/everything"
            params = {
                "q": self.query,
                "sortBy": sort_by,
                "language": language,
                "pageSize": min(max_results, 100),  # NewsAPI limit is 100
            }

            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date

            if self.sources:
                params["sources"] = ",".join(self.sources)

            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                print(f"NewsAPI Error: {data.get('message', 'Unknown error')}")
                return []

            articles = data.get("articles", [])
            return self._format_articles(articles)

        except Exception as e:
            print(f"Error fetching everything search: {e}")
            return []

    def _format_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Format NewsAPI articles to match the standard retriever format.

        Args:
            articles: List of articles from NewsAPI

        Returns:
            List of formatted articles
        """
        formatted_articles = []

        for article in articles:
            # Skip articles with null/missing essential fields
            if not article.get("url") or not article.get("title"):
                continue

            formatted_article = {
                "href": article.get("url", ""),
                "title": article.get("title", "No title"),
                "body": article.get("description")
                or article.get("content")
                or "No description available",
                "author": article.get("author", "Unknown"),
                "source": article.get("source", {}).get("name", "Unknown"),
                "published_at": article.get("publishedAt", ""),
                "url_to_image": article.get("urlToImage", ""),
            }

            # Add source info to body for context
            source_name = formatted_article["source"]
            pub_date = (
                formatted_article["published_at"][:10]
                if formatted_article["published_at"]
                else "Unknown date"
            )

            formatted_article["body"] = (
                f"{formatted_article['body']} | Source: {source_name} | Published: {pub_date}"
            )

            formatted_articles.append(formatted_article)

        return formatted_articles

    def search(
        self, max_results: int = 10, search_type: str = "everything"
    ) -> List[Dict]:
        """
        Main search method that can use either top headlines or everything search.

        Args:
            max_results: Maximum number of results to return
            search_type: Type of search ('headlines' or 'everything')

        Returns:
            List of formatted news articles
        """
        try:
            if search_type == "headlines":
                return self.get_top_headlines(max_results=max_results)
            else:
                # Default to everything search for comprehensive results
                # Set from_date to last 30 days to get recent articles
                from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                return self.get_everything(
                    max_results=max_results, from_date=from_date, sort_by="publishedAt"
                )
        except Exception as e:
            print(f"Error in NewsAPI search: {e}")
            return []

    def get_sources(
        self,
        country: Optional[str] = None,
        language: str = "en",
        category: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get available news sources.

        Args:
            country: Country code to filter sources
            language: Language code to filter sources
            category: Category to filter sources

        Returns:
            List of available news sources
        """
        try:
            url = f"{self.base_url}/sources"
            params = {"language": language}

            if country:
                params["country"] = country
            if category:
                params["category"] = category

            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                print(f"NewsAPI Error: {data.get('message', 'Unknown error')}")
                return []

            return data.get("sources", [])

        except Exception as e:
            print(f"Error fetching sources: {e}")
            return []
