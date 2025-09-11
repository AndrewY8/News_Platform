#!/usr/bin/env python3
"""
Test script for various retrievers to validate URL discovery functionality.
Tests each retriever's ability to find relevant URLs and return proper format.
"""

import asyncio
import json
import os
import sys
from typing import List, Dict, Any
import time

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from news_agent.retrievers.tavily.tavily_search import TavilyRetriever
from news_agent.retrievers.duckduckgo.duckduckgo import DuckDuckGoRetriever
from news_agent.retrievers.exa.exa import ExaRetriever
from news_agent.retrievers.google.google import GoogleRetriever
from news_agent.retrievers.searchapi.searchapi import SearchAPIRetriever
from news_agent.retrievers.serpapi.serpapi import SerpAPIRetriever
from news_agent.retrievers.serper.serper import SerperRetriever
from news_agent.retrievers.EDGAR.EDGAR import EDGARRetriever
from news_agent.retrievers.newsapi.newsapi import NewsAPIRetriever


class RetrieverTester:
    """Test suite for all retriever implementations"""
    
    def __init__(self):
        self.test_queries = [
            "CRCL news",
            "CRCL latest updates", 
            "CRCL civil rights violations",
            "CRCL complaints investigation"
        ]
        self.edgar_test_queries = [
            "AAPL",  # Apple Inc.
            "MSFT",  # Microsoft Corporation
            "TSLA",  # Tesla Inc.
            "Apple Inc"  # Company name
        ]
        self.results = {}
    
    def test_tavily_search(self):
        """Test Tavily Search retriever"""
        print("\n" + "="*50)
        print("TESTING TAVILY SEARCH RETRIEVER")
        print("="*50)
        
        for query in self.test_queries:
            print(f"\nTesting query: '{query}'")
            try:
                retriever = TavilyRetriever(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "TavilySearch")
                
                print(f"[OK] Query completed in {end_time - start_time:.2f}s")
                print(f"[OK] Found {len(results)} results")
                if results:
                    print(f"[OK] Sample URL: {results[0].get('href', 'N/A')}")
                    print(f"[OK] Sample body length: {len(results[0].get('body', ''))}")
                
                self.results[f"tavily_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"[ERROR] Error with query '{query}': {str(e)}")
                self.results[f"tavily_{query}"] = {
                    "success": False,
                    "error": str(e)
                }
    
    def test_duckduckgo_search(self):
        """Test DuckDuckGo retriever"""
        print("\n" + "="*50)
        print("TESTING DUCKDUCKGO SEARCH RETRIEVER")
        print("="*50)
        
        for query in self.test_queries:
            print(f"\nTesting query: '{query}'")
            try:
                retriever = DuckDuckGoRetriever(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "DuckDuckGo")
                
                print(f"[OK] Query completed in {end_time - start_time:.2f}s")
                print(f"[OK] Found {len(results)} results")
                if results:
                    # DuckDuckGo results have different format
                    sample_result = results[0] if results else {}
                    print(f"[OK] Sample URL: {sample_result.get('href', sample_result.get('link', 'N/A'))}")
                    print(f"[OK] Sample body: {sample_result.get('body', sample_result.get('title', 'N/A'))[:100]}...")
                
                self.results[f"duckduckgo_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"[ERROR] Error with query '{query}': {str(e)}")
                self.results[f"duckduckgo_{query}"] = {
                    "success": False,
                    "error": str(e)
                }
    
    def test_exa_search(self):
        """Test Exa retriever"""
        print("\n" + "="*50)
        print("TESTING EXA SEARCH RETRIEVER")
        print("="*50)
        
        for query in self.test_queries:
            print(f"\nTesting query: '{query}'")
            try:
                retriever = ExaRetriever(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "Exa")
                
                print(f"[OK] Query completed in {end_time - start_time:.2f}s")
                print(f"[OK] Found {len(results)} results")
                if results:
                    print(f"[OK] Sample URL: {results[0].get('href', 'N/A')}")
                    print(f"[OK] Sample body length: {len(results[0].get('body', ''))}")
                
                self.results[f"exa_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"[ERROR] Error with query '{query}': {str(e)}")
                self.results[f"exa_{query}"] = {
                    "success": False,
                    "error": str(e)
                }

    def test_google_search(self):
        """Test Google retriever"""
        print("\n" + "="*50)
        print("TESTING GOOGLE SEARCH RETRIEVER")
        print("="*50)
        
        for query in self.test_queries:
            print(f"\nTesting query: '{query}'")
            try:
                retriever = GoogleRetriever(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "Google")
                
                print(f"[OK] Query completed in {end_time - start_time:.2f}s")
                print(f"[OK] Found {len(results)} results")
                if results:
                    print(f"[OK] Sample URL: {results[0].get('href', 'N/A')}")
                    print(f"[OK] Sample body length: {len(results[0].get('body', ''))}")
                
                self.results[f"google_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"[ERROR] Error with query '{query}': {str(e)}")
                self.results[f"google_{query}"] = {
                    "success": False,
                    "error": str(e)
                }

    def test_searchapi_search(self):
        """Test SearchAPI retriever"""
        print("\n" + "="*50)
        print("TESTING SEARCHAPI RETRIEVER")
        print("="*50)
        
        for query in self.test_queries:
            print(f"\nTesting query: '{query}'")
            try:
                retriever = SearchAPIRetriever(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "SearchAPI")
                
                print(f"[OK] Query completed in {end_time - start_time:.2f}s")
                print(f"[OK] Found {len(results)} results")
                if results:
                    print(f"[OK] Sample URL: {results[0].get('href', 'N/A')}")
                    print(f"[OK] Sample body length: {len(results[0].get('body', ''))}")
                
                self.results[f"searchapi_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"[ERROR] Error with query '{query}': {str(e)}")
                self.results[f"searchapi_{query}"] = {
                    "success": False,
                    "error": str(e)
                }

    def test_serpapi_search(self):
        """Test SerpAPI retriever"""
        print("\n" + "="*50)
        print("TESTING SERPAPI RETRIEVER")
        print("="*50)
        
        for query in self.test_queries:
            print(f"\nTesting query: '{query}'")
            try:
                retriever = SerpAPIRetriever(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "SerpAPI")
                
                print(f"[OK] Query completed in {end_time - start_time:.2f}s")
                print(f"[OK] Found {len(results)} results")
                if results:
                    print(f"[OK] Sample URL: {results[0].get('href', 'N/A')}")
                    print(f"[OK] Sample body length: {len(results[0].get('body', ''))}")
                
                self.results[f"serpapi_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"[ERROR] Error with query '{query}': {str(e)}")
                self.results[f"serpapi_{query}"] = {
                    "success": False,
                    "error": str(e)
                }

    def test_serper_search(self):
        """Test Serper retriever"""
        print("\n" + "="*50)
        print("TESTING SERPER RETRIEVER")
        print("="*50)
        
        for query in self.test_queries:
            print(f"\nTesting query: '{query}'")
            try:
                retriever = SerperRetriever(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "Serper")
                
                print(f"[OK] Query completed in {end_time - start_time:.2f}s")
                print(f"[OK] Found {len(results)} results")
                if results:
                    print(f"[OK] Sample URL: {results[0].get('href', 'N/A')}")
                    print(f"[OK] Sample body length: {len(results[0].get('body', ''))}")
                
                self.results[f"serper_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"[ERROR] Error with query '{query}': {str(e)}")
                self.results[f"serper_{query}"] = {
                    "success": False,
                    "error": str(e)
                }

    def test_edgar_search(self):
        """Test EDGAR retriever"""
        print("\n" + "="*50)
        print("TESTING SEC EDGAR RETRIEVER")
        print("="*50)
        
        for query in self.edgar_test_queries:
            print(f"\nTesting query: '{query}'")
            try:
                retriever = EDGARRetriever(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "EDGAR")
                
                print(f"[OK] Query completed in {end_time - start_time:.2f}s")
                print(f"[OK] Found {len(results)} results")
                if results:
                    print(f"[OK] Sample URL: {results[0].get('href', 'N/A')}")
                    print(f"[OK] Sample body length: {len(results[0].get('body', ''))}")
                
                self.results[f"edgar_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"[ERROR] Error with query '{query}': {str(e)}")
                self.results[f"edgar_{query}"] = {
                    "success": False,
                    "error": str(e)
                }

    def test_newsapi_search(self):
        """Test NewsAPI retriever"""
        print("\n" + "="*50)
        print("TESTING NEWSAPI RETRIEVER")
        print("="*50)
        
        for query in self.test_queries:
            print(f"\nTesting query: '{query}'")
            try:
                retriever = NewsAPIRetriever(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "NewsAPI")
                
                print(f"[OK] Query completed in {end_time - start_time:.2f}s")
                print(f"[OK] Found {len(results)} results")
                if results:
                    print(f"[OK] Sample URL: {results[0].get('href', 'N/A')}")
                    print(f"[OK] Sample body length: {len(results[0].get('body', ''))}")
                
                self.results[f"newsapi_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"[ERROR] Error with query '{query}': {str(e)}")
                self.results[f"newsapi_{query}"] = {
                    "success": False,
                    "error": str(e)
                }
    
    def _validate_retriever_results(self, results: List[Dict], retriever_name: str) -> bool:
        """Validate that retriever results follow expected format"""
        if not isinstance(results, list):
            print(f"[ERROR] {retriever_name}: Results should be a list")
            return False
        
        if len(results) == 0:
            print(f"[WARN] {retriever_name}: No results found")
            return True  # Empty results can be valid
        
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                print(f"[ERROR] {retriever_name}: Result {i} should be a dictionary")
                return False
            
            # Check for URL field (could be 'href' or 'link' depending on retriever)
            if not ('href' in result or 'link' in result or 'url' in result):
                print(f"[ERROR] {retriever_name}: Result {i} missing URL field")
                return False
            
            # Check for content field (could be 'body', 'content', 'title', etc.)
            content_fields = ['body', 'content', 'title', 'snippet']
            if not any(field in result for field in content_fields):
                print(f"[ERROR] {retriever_name}: Result {i} missing content field")
                return False
        
        print(f"[OK] {retriever_name}: Results format validated")
        return True
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*70)
        print("RETRIEVER TEST SUMMARY REPORT")
        print("="*70)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results.values() if r.get('success', False))
        
        print(f"Total Tests Run: {total_tests}")
        print(f"Successful Tests: {successful_tests}")
        print(f"Failed Tests: {total_tests - successful_tests}")
        print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        print("\n" + "-"*50)
        print("DETAILED RESULTS:")
        print("-"*50)
        
        for test_name, result in self.results.items():
            retriever = test_name.split('_')[0]
            query = '_'.join(test_name.split('_')[1:])
            
            if result.get('success'):
                print(f"[OK] {retriever.upper()}: '{query}'")
                print(f"  --> Results: {result.get('count', 0)}, Time: {result.get('time', 0):.2f}s")
            else:
                print(f"[ERROR] {retriever.upper()}: '{query}'")
                print(f"  --> Error: {result.get('error', 'Unknown error')}")
        
        # Save detailed results to JSON file
        with open('retriever_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: retriever_test_results.json")
        
        return successful_tests == total_tests


def main():
    """Main test execution function"""
    print("Starting Retriever Testing Suite...")
    print("This will test various retrievers with multiple queries.")
    
    tester = RetrieverTester()
    
    # Run all retriever tests
    tester.test_tavily_search()
    tester.test_duckduckgo_search()
    tester.test_exa_search()
    tester.test_google_search()
    tester.test_searchapi_search()
    tester.test_serpapi_search()
    tester.test_serper_search()
    tester.test_edgar_search()
    tester.test_newsapi_search()
    
    # Generate final report
    all_passed = tester.generate_report()
    
    if all_passed:
        print("\n[SUCCESS] All retriever tests passed!")
        return 0
    else:
        print("\n[WARN]  Some retriever tests failed. Check the report above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)