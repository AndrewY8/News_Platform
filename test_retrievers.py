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

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from news_agent.retrievers.tavily.tavily_search import TavilySearch
from news_agent.retrievers.duckduckgo.duckduckgo import Duckduckgo


class RetrieverTester:
    """Test suite for all retriever implementations"""
    
    def __init__(self):
        self.test_queries = [
            "Python web scraping best practices",
            "artificial intelligence news 2024",
            "climate change research latest",
            "cryptocurrency market analysis"
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
                retriever = TavilySearch(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "TavilySearch")
                
                print(f"✓ Query completed in {end_time - start_time:.2f}s")
                print(f"✓ Found {len(results)} results")
                if results:
                    print(f"✓ Sample URL: {results[0].get('href', 'N/A')}")
                    print(f"✓ Sample body length: {len(results[0].get('body', ''))}")
                
                self.results[f"tavily_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"✗ Error with query '{query}': {str(e)}")
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
                retriever = Duckduckgo(query=query)
                start_time = time.time()
                results = retriever.search(max_results=5)
                end_time = time.time()
                
                # Validate results
                success = self._validate_retriever_results(results, "DuckDuckGo")
                
                print(f"✓ Query completed in {end_time - start_time:.2f}s")
                print(f"✓ Found {len(results)} results")
                if results:
                    # DuckDuckGo results have different format
                    sample_result = results[0] if results else {}
                    print(f"✓ Sample URL: {sample_result.get('href', sample_result.get('link', 'N/A'))}")
                    print(f"✓ Sample body: {sample_result.get('body', sample_result.get('title', 'N/A'))[:100]}...")
                
                self.results[f"duckduckgo_{query}"] = {
                    "success": success,
                    "count": len(results),
                    "time": end_time - start_time,
                    "results": results[:2]  # Store first 2 for inspection
                }
                
            except Exception as e:
                print(f"✗ Error with query '{query}': {str(e)}")
                self.results[f"duckduckgo_{query}"] = {
                    "success": False,
                    "error": str(e)
                }
    
    def _validate_retriever_results(self, results: List[Dict], retriever_name: str) -> bool:
        """Validate that retriever results follow expected format"""
        if not isinstance(results, list):
            print(f"✗ {retriever_name}: Results should be a list")
            return False
        
        if len(results) == 0:
            print(f"⚠ {retriever_name}: No results found")
            return True  # Empty results can be valid
        
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                print(f"✗ {retriever_name}: Result {i} should be a dictionary")
                return False
            
            # Check for URL field (could be 'href' or 'link' depending on retriever)
            if not ('href' in result or 'link' in result or 'url' in result):
                print(f"✗ {retriever_name}: Result {i} missing URL field")
                return False
            
            # Check for content field (could be 'body', 'content', 'title', etc.)
            content_fields = ['body', 'content', 'title', 'snippet']
            if not any(field in result for field in content_fields):
                print(f"✗ {retriever_name}: Result {i} missing content field")
                return False
        
        print(f"✓ {retriever_name}: Results format validated")
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
                print(f"✓ {retriever.upper()}: '{query}'")
                print(f"  └── Results: {result.get('count', 0)}, Time: {result.get('time', 0):.2f}s")
            else:
                print(f"✗ {retriever.upper()}: '{query}'")
                print(f"  └── Error: {result.get('error', 'Unknown error')}")
        
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
    
    # Generate final report
    all_passed = tester.generate_report()
    
    if all_passed:
        print("\n🎉 All retriever tests passed!")
        return 0
    else:
        print("\n⚠️  Some retriever tests failed. Check the report above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)