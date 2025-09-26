import os
import praw
from typing import List, Dict, Any
import datetime
import time

class RedditRetriever:
    """
    Reddit API Retriever for r/wallstreetbets
    """
    def __init__(self, query: str, subreddit_name: str = "wallstreetbets"):
        """
        Initializes the RedditRetriever object.
        Args:
            query (str): The search query string (usually a ticker).
            subreddit_name (str): The name of the subreddit to scrape. Defaults to "wallstreetbets".
        """
        self.query = query
        self.subreddit_name = subreddit_name
        self.reddit = self._authenticate_reddit()

    def _authenticate_reddit(self):
        """
        Authenticates with the Reddit API using PRAW.
        Expects REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT
        to be set as environment variables.
        """
        try:
            reddit = praw.Reddit(
                client_id=os.environ["REDDIT_CLIENT_ID"],
                client_secret=os.environ["REDDIT_CLIENT_SECRET"],
                user_agent=os.environ["REDDIT_USER_AGENT"],
                check_for_async=False,  # Disable async check for better performance
            )
            return reddit
        except KeyError as e:
            raise ValueError(f"Missing Reddit API environment variable: {e}. "
                           "Please set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT.")
        except Exception as e:
            raise ConnectionError(f"Failed to authenticate with Reddit API: {e}")

    def _get_hot_posts(self, limit: int = 10) -> List[Any]:
        """
        Internal method to fetch hot posts from the specified subreddit.
        """
        subreddit = self.reddit.subreddit(self.subreddit_name)
        posts = []
        try:
            for submission in subreddit.hot(limit=limit):
                posts.append(submission)
                # Add small delay to respect rate limits
                time.sleep(0.1)  # 100ms delay between requests
        except praw.exceptions.RedditAPIException as e:
            print(f"Reddit API error: {e}")
        except Exception as e:
            print(f"Error fetching posts from r/{self.subreddit_name}: {e}")
        return posts

    def get_hot_posts(self, limit: int = 10, filter_query: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieves hot posts from the specified subreddit and optionally filters by query.
        Args:
            limit (int): The maximum number of posts to retrieve. Defaults to 10.
            filter_query (bool): Whether to filter posts by the query string. Defaults to True.
        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a formatted post.
        """
        search_response = []
        try:
            posts = self._get_hot_posts(limit=limit * 3 if filter_query else limit)  # Get more posts if filtering
            for post in posts:
                # If filtering is enabled, check if query appears in title or selftext
                if filter_query:
                    query_lower = self.query.lower()
                    title_match = query_lower in post.title.lower()
                    content_match = query_lower in post.selftext.lower()
                    
                    if not (title_match or content_match):
                        continue
                
                # Convert Unix timestamp to ISO 8601 format
                published_date = datetime.datetime.fromtimestamp(post.created_utc, tz=datetime.timezone.utc).isoformat()
                search_response.append({
                    "href": f"https://www.reddit.com{post.permalink}",
                    "url": f"https://www.reddit.com{post.permalink}",
                    "body": post.selftext,
                    "content": post.selftext,
                    "title": post.title,
                    "source": f"reddit.com/r/{self.subreddit_name}",
                    "published_date": published_date,
                    "score": post.score,
                    "raw_content": post.selftext,
                    "author": post.author.name if post.author else "Unknown",
                    "num_comments": post.num_comments,
                })
                
                # Stop if we have enough filtered results
                if filter_query and len(search_response) >= limit:
                    break
                    
        except Exception as e:
            print(f"Error retrieving hot posts: {e}. Resulting in empty response.")
            search_response = []
        return search_response