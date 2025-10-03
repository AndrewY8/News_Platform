"""
Quick test to see what date format Tavily returns
Run this to debug published_date issues
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deep_research_agent.retrievers.tavily.trusted_news_retriever import TrustedNewsRetriever

# Test search
retriever = TrustedNewsRetriever(query="Apple Inc latest news", topic="general")
results = retriever.search(search_depth="basic", max_results=3, days=7)

print("\n" + "="*80)
print("TAVILY DATE FORMAT TEST")
print("="*80)

for idx, result in enumerate(results, 1):
    print(f"\nArticle {idx}:")
    print(f"  Title: {result.get('title', 'N/A')[:60]}")
    print(f"  URL: {result.get('url', 'N/A')[:60]}")
    print(f"  Published Date: {result.get('published_date', 'N/A')}")
    print(f"  Type: {type(result.get('published_date'))}")
    print(f"  Score: {result.get('score', 'N/A')}")

print("\n" + "="*80)
print(f"Total results: {len(results)}")
print("="*80 + "\n")
