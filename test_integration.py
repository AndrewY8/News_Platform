#!/usr/bin/env python3
"""
End-to-end integration test for the complete retriever + scraper workflow.
Tests the full pipeline: query -> URLs -> scraped content.
"""

import asyncio
import json
import os
import sys
import time
from typing import List, Dict, Any
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from news_agent.retrievers.tavily.tavily_search import TavilyRetriever
from news_agent.retrievers.duckduckgo.duckduckgo import DuckDuckGoRetriever
from news_agent.scraper.scraper import Scraper
from gpt_researcher.utils.workers import WorkerPool


class IntegrationTester:
    """End-to-end integration test suite for retriever + scraper pipeline"""
    
    def __init__(self):
        self.test_scenarios = [
            {
                "name": "Technology News",
                "query": "latest artificial intelligence breakthroughs 2024",
                "expected_content": ["AI", "artificial intelligence", "machine learning", "technology"],
                "max_results": 3
            },
            {
                "name": "Climate Research",
                "query": "climate change research papers latest findings",
                "expected_content": ["climate", "research", "study", "temperature", "carbon"],
                "max_results": 3
            },
            {
                "name": "Programming Tutorials",
                "query": "Python web scraping tutorial guide",
                "expected_content": ["python", "scraping", "tutorial", "web", "data"],
                "max_results": 3
            }
        ]
        self.results = {}
        self.worker_pool = WorkerPool(max_workers=5)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def test_tavily_to_scraper_pipeline(self):
        """Test complete pipeline: Tavily retriever -> Scraper"""
        print("\n" + "="*60)
        print("TESTING TAVILY → SCRAPER INTEGRATION")
        print("="*60)
        
        for scenario in self.test_scenarios:
            print(f"\n--- Scenario: {scenario['name']} ---")
            print(f"Query: '{scenario['query']}'")
            
            try:
                # Step 1: Get URLs from Tavily
                print("\n1. Retrieving URLs from Tavily...")
                retriever = TavilyRetriever(query=scenario['query'])
                start_time = time.time()
                search_results = retriever.search(max_results=scenario['max_results'])
                retrieval_time = time.time() - start_time
                
                if not search_results:
                    print("✗ No URLs found from Tavily")
                    continue
                
                urls = [result['href'] for result in search_results if 'href' in result]
                print(f"✓ Found {len(urls)} URLs in {retrieval_time:.2f}s")
                for i, url in enumerate(urls, 1):
                    print(f"  {i}. {url}")
                
                # Step 2: Scrape content from URLs
                print("\n2. Scraping content from URLs...")
                scraper = Scraper(
                    urls=urls,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    scraper='bs',  # Use BeautifulSoup scraper
                    worker_pool=self.worker_pool
                )
                
                scrape_start = time.time()
                scraped_results = await scraper.run()
                scraping_time = time.time() - scrape_start
                
                # Step 3: Validate and analyze results
                print(f"\n3. Analyzing scraped content...")
                analysis = self._analyze_scraped_content(
                    scraped_results, 
                    scenario['expected_content']
                )
                
                total_time = retrieval_time + scraping_time
                
                print(f"✓ Pipeline completed in {total_time:.2f}s")
                print(f"  └── Retrieval: {retrieval_time:.2f}s, Scraping: {scraping_time:.2f}s")
                print(f"✓ Successfully scraped {analysis['successful_scrapes']}/{len(urls)} URLs")
                print(f"✓ Total content: {analysis['total_content_length']:,} characters")
                print(f"✓ Total images: {analysis['total_images']}")
                print(f"✓ Content relevance: {analysis['relevance_score']:.1f}%")
                
                self.results[f"tavily_{scenario['name']}"] = {
                    "success": True,
                    "urls_found": len(urls),
                    "urls_scraped": analysis['successful_scrapes'],
                    "retrieval_time": retrieval_time,
                    "scraping_time": scraping_time,
                    "total_time": total_time,
                    "content_analysis": analysis,
                    "search_results": search_results,
                    "scraped_results": scraped_results
                }
                
            except Exception as e:
                print(f"✗ Pipeline failed: {str(e)}")
                self.results[f"tavily_{scenario['name']}"] = {
                    "success": False,
                    "error": str(e)
                }
    
    async def test_duckduckgo_to_scraper_pipeline(self):
        """Test complete pipeline: DuckDuckGo retriever -> Scraper"""
        print("\n" + "="*60)
        print("TESTING DUCKDUCKGO → SCRAPER INTEGRATION")
        print("="*60)
        
        for scenario in self.test_scenarios:
            print(f"\n--- Scenario: {scenario['name']} ---")
            print(f"Query: '{scenario['query']}'")
            
            try:
                # Step 1: Get URLs from DuckDuckGo
                print("\n1. Retrieving URLs from DuckDuckGo...")
                retriever = DuckDuckGoRetriever(query=scenario['query'])
                start_time = time.time()
                search_results = retriever.search(max_results=scenario['max_results'])
                retrieval_time = time.time() - start_time
                
                if not search_results:
                    print("✗ No URLs found from DuckDuckGo")
                    continue
                
                # Extract URLs (DuckDuckGo format might be different)
                urls = []
                for result in search_results:
                    if isinstance(result, dict):
                        url = result.get('href') or result.get('link') or result.get('url')
                        if url:
                            urls.append(url)
                
                print(f"✓ Found {len(urls)} URLs in {retrieval_time:.2f}s")
                for i, url in enumerate(urls, 1):
                    print(f"  {i}. {url}")
                
                if not urls:
                    print("✗ No valid URLs extracted from search results")
                    continue
                
                # Step 2: Scrape content from URLs
                print("\n2. Scraping content from URLs...")
                scraper = Scraper(
                    urls=urls,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    scraper='bs',  # Use BeautifulSoup scraper
                    worker_pool=self.worker_pool
                )
                
                scrape_start = time.time()
                scraped_results = await scraper.run()
                scraping_time = time.time() - scrape_start
                
                # Step 3: Validate and analyze results
                print(f"\n3. Analyzing scraped content...")
                analysis = self._analyze_scraped_content(
                    scraped_results, 
                    scenario['expected_content']
                )
                
                total_time = retrieval_time + scraping_time
                
                print(f"✓ Pipeline completed in {total_time:.2f}s")
                print(f"  └── Retrieval: {retrieval_time:.2f}s, Scraping: {scraping_time:.2f}s")
                print(f"✓ Successfully scraped {analysis['successful_scrapes']}/{len(urls)} URLs")
                print(f"✓ Total content: {analysis['total_content_length']:,} characters")
                print(f"✓ Total images: {analysis['total_images']}")
                print(f"✓ Content relevance: {analysis['relevance_score']:.1f}%")
                
                self.results[f"duckduckgo_{scenario['name']}"] = {
                    "success": True,
                    "urls_found": len(urls),
                    "urls_scraped": analysis['successful_scrapes'],
                    "retrieval_time": retrieval_time,
                    "scraping_time": scraping_time,
                    "total_time": total_time,
                    "content_analysis": analysis,
                    "search_results": search_results,
                    "scraped_results": scraped_results
                }
                
            except Exception as e:
                print(f"✗ Pipeline failed: {str(e)}")
                self.results[f"duckduckgo_{scenario['name']}"] = {
                    "success": False,
                    "error": str(e)
                }
    
    def _analyze_scraped_content(self, scraped_results: List[Dict], expected_keywords: List[str]) -> Dict:
        """Analyze scraped content for quality and relevance"""
        analysis = {
            "successful_scrapes": 0,
            "failed_scrapes": 0,
            "total_content_length": 0,
            "total_images": 0,
            "relevance_score": 0.0,
            "content_samples": [],
            "titles": []
        }
        
        relevant_content_count = 0
        
        for result in scraped_results:
            if result.get('raw_content') and len(result['raw_content']) > 100:
                analysis["successful_scrapes"] += 1
                content_length = len(result['raw_content'])
                analysis["total_content_length"] += content_length
                analysis["total_images"] += len(result.get('image_urls', []))
                
                # Check content relevance
                content_lower = result['raw_content'].lower()
                keyword_matches = sum(1 for keyword in expected_keywords 
                                    if keyword.lower() in content_lower)
                
                if keyword_matches > 0:
                    relevant_content_count += 1
                
                # Store sample data
                analysis["content_samples"].append({
                    "url": result.get('url'),
                    "title": result.get('title', ''),
                    "content_length": content_length,
                    "keyword_matches": keyword_matches,
                    "sample_content": result['raw_content'][:200] + "..." if content_length > 200 else result['raw_content']
                })
                
                analysis["titles"].append(result.get('title', ''))
                
            else:
                analysis["failed_scrapes"] += 1
        
        # Calculate relevance score
        if analysis["successful_scrapes"] > 0:
            analysis["relevance_score"] = (relevant_content_count / analysis["successful_scrapes"]) * 100
        
        return analysis
    
    def test_content_format_consistency(self):
        """Test that all scraped content follows the expected format"""
        print("\n" + "="*60)
        print("TESTING OUTPUT FORMAT CONSISTENCY")
        print("="*60)
        
        format_issues = []
        
        for test_name, result in self.results.items():
            if not result.get('success'):
                continue
                
            scraped_results = result.get('scraped_results', [])
            
            for i, scraped_item in enumerate(scraped_results):
                issues = self._validate_output_format(scraped_item, f"{test_name}[{i}]")
                format_issues.extend(issues)
        
        if format_issues:
            print(f"✗ Found {len(format_issues)} format issues:")
            for issue in format_issues:
                print(f"  - {issue}")
        else:
            print("✓ All output formats are consistent")
        
        return len(format_issues) == 0
    
    def _validate_output_format(self, result: Dict, context: str) -> List[str]:
        """Validate that a single result follows the expected output format"""
        issues = []
        
        # Check required fields
        required_fields = ['url', 'raw_content', 'image_urls', 'title']
        for field in required_fields:
            if field not in result:
                issues.append(f"{context}: Missing required field '{field}'")
        
        # Check field types
        if 'url' in result and not isinstance(result['url'], str):
            issues.append(f"{context}: 'url' should be string, got {type(result['url'])}")
        
        if 'raw_content' in result and result['raw_content'] is not None and not isinstance(result['raw_content'], str):
            issues.append(f"{context}: 'raw_content' should be string or None, got {type(result['raw_content'])}")
        
        if 'image_urls' in result and not isinstance(result['image_urls'], list):
            issues.append(f"{context}: 'image_urls' should be list, got {type(result['image_urls'])}")
        
        if 'title' in result and not isinstance(result['title'], str):
            issues.append(f"{context}: 'title' should be string, got {type(result['title'])}")
        
        # Check image URL format
        if 'image_urls' in result and isinstance(result['image_urls'], list):
            for j, img in enumerate(result['image_urls']):
                if isinstance(img, dict):
                    if 'url' not in img or 'score' not in img:
                        issues.append(f"{context}: image_urls[{j}] missing 'url' or 'score' field")
                elif not isinstance(img, str):
                    issues.append(f"{context}: image_urls[{j}] should be dict or string")
        
        return issues
    
    def generate_comprehensive_report(self):
        """Generate comprehensive integration test report"""
        print("\n" + "="*80)
        print("INTEGRATION TEST COMPREHENSIVE REPORT")
        print("="*80)
        
        total_tests = len([r for r in self.results.values() if 'success' in r])
        successful_tests = len([r for r in self.results.values() if r.get('success', False)])
        
        print(f"Total Integration Tests: {total_tests}")
        print(f"Successful Tests: {successful_tests}")
        print(f"Failed Tests: {total_tests - successful_tests}")
        print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        # Performance metrics
        successful_results = [r for r in self.results.values() if r.get('success', False)]
        
        if successful_results:
            print(f"\n{'-'*50}")
            print("PERFORMANCE METRICS")
            print(f"{'-'*50}")
            
            avg_total_time = sum(r.get('total_time', 0) for r in successful_results) / len(successful_results)
            avg_retrieval_time = sum(r.get('retrieval_time', 0) for r in successful_results) / len(successful_results)
            avg_scraping_time = sum(r.get('scraping_time', 0) for r in successful_results) / len(successful_results)
            
            total_urls_found = sum(r.get('urls_found', 0) for r in successful_results)
            total_urls_scraped = sum(r.get('urls_scraped', 0) for r in successful_results)
            
            print(f"Average Total Time: {avg_total_time:.2f}s")
            print(f"Average Retrieval Time: {avg_retrieval_time:.2f}s")
            print(f"Average Scraping Time: {avg_scraping_time:.2f}s")
            print(f"Total URLs Found: {total_urls_found}")
            print(f"Total URLs Successfully Scraped: {total_urls_scraped}")
            print(f"Scraping Success Rate: {(total_urls_scraped/total_urls_found)*100:.1f}%")
            
            # Content analysis
            total_content = sum(r.get('content_analysis', {}).get('total_content_length', 0) for r in successful_results)
            total_images = sum(r.get('content_analysis', {}).get('total_images', 0) for r in successful_results)
            avg_relevance = sum(r.get('content_analysis', {}).get('relevance_score', 0) for r in successful_results) / len(successful_results)
            
            print(f"Total Content Extracted: {total_content:,} characters")
            print(f"Total Images Found: {total_images}")
            print(f"Average Content Relevance: {avg_relevance:.1f}%")
        
        # Detailed results
        print(f"\n{'-'*50}")
        print("DETAILED TEST RESULTS")
        print(f"{'-'*50}")
        
        for test_name, result in self.results.items():
            retriever, scenario = test_name.split('_', 1)
            
            if result.get('success'):
                print(f"✓ {retriever.upper()} → {scenario}")
                print(f"  └── URLs: {result.get('urls_found', 0)} found, {result.get('urls_scraped', 0)} scraped")
                print(f"  └── Time: {result.get('total_time', 0):.2f}s total")
                print(f"  └── Content: {result.get('content_analysis', {}).get('total_content_length', 0):,} chars")
                print(f"  └── Relevance: {result.get('content_analysis', {}).get('relevance_score', 0):.1f}%")
            else:
                print(f"✗ {retriever.upper()} → {scenario}")
                print(f"  └── Error: {result.get('error', 'Unknown error')}")
        
        # Test format consistency
        format_ok = self.test_content_format_consistency()
        
        # Save detailed results
        with open('integration_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: integration_test_results.json")
        
        return successful_tests == total_tests and format_ok


async def main():
    """Main integration test execution function"""
    print("Starting Integration Testing Suite...")
    print("This will test the complete retriever → scraper pipeline.")
    
    tester = IntegrationTester()
    
    # Run integration tests
    await tester.test_tavily_to_scraper_pipeline()
    await tester.test_duckduckgo_to_scraper_pipeline()
    
    # Generate comprehensive report
    all_passed = tester.generate_comprehensive_report()
    
    if all_passed:
        print("\n🎉 All integration tests passed!")
        return 0
    else:
        print("\n⚠️  Some integration tests failed. Check the report above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)