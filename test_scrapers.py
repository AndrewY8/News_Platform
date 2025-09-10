#!/usr/bin/env python3
"""
Test script for various scrapers to validate content extraction functionality.
Tests each scraper's ability to extract content from different URL types.
"""

import asyncio
import json
import os
import sys
import time
import requests
from typing import List, Dict, Any

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from news_agent.scraper.beautiful_soup.beautiful_soup import BeautifulSoupScraper
from news_agent.scraper.scraper import Scraper
from gpt_researcher.utils.workers import WorkerPool


class ScraperTester:
    """Test suite for all scraper implementations"""
    
    def __init__(self):
        # Test URLs covering different content types
        self.test_urls = {
            "news": [
                "https://www.bbc.com/news",
                "https://techcrunch.com",
                "https://www.reuters.com"
            ],
            "blogs": [
                "https://blog.python.org",
                "https://medium.com/@example",
                "https://dev.to"
            ],
            "academic": [
                "https://arxiv.org/abs/2301.00001",
                "https://scholar.google.com"
            ],
            "pdf": [
                "https://arxiv.org/pdf/2301.00001.pdf"
            ]
        }
        self.results = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def test_beautiful_soup_scraper(self):
        """Test BeautifulSoup scraper directly"""
        print("\n" + "="*50)
        print("TESTING BEAUTIFULSOUP SCRAPER")
        print("="*50)
        
        test_urls = self.test_urls["news"] + self.test_urls["blogs"]
        
        for url in test_urls:
            print(f"\nTesting URL: {url}")
            try:
                scraper = BeautifulSoupScraper(url, self.session)
                start_time = time.time()
                content, image_urls, title = scraper.scrape()
                end_time = time.time()
                
                # Validate results
                success = self._validate_scraper_results(content, image_urls, title, "BeautifulSoup")
                
                print(f"✓ Scraping completed in {end_time - start_time:.2f}s")
                print(f"✓ Title: {title[:50]}..." if title else "⚠ No title extracted")
                print(f"✓ Content length: {len(content)} characters")
                print(f"✓ Images found: {len(image_urls)}")
                
                self.results[f"bs_{url}"] = {
                    "success": success,
                    "content_length": len(content),
                    "images_count": len(image_urls),
                    "time": end_time - start_time,
                    "title": title,
                    "has_content": len(content) > 100
                }
                
            except Exception as e:
                print(f"✗ Error with URL '{url}': {str(e)}")
                self.results[f"bs_{url}"] = {
                    "success": False,
                    "error": str(e)
                }
    
    async def test_scraper_with_worker_pool(self):
        """Test main Scraper class with worker pool for different scraper types"""
        print("\n" + "="*50)
        print("TESTING MAIN SCRAPER CLASS")
        print("="*50)
        
        # Create worker pool
        worker_pool = WorkerPool(max_workers=3)
        
        # Test different scraper types
        scraper_configs = [
            ("bs", "BeautifulSoup"),
            ("browser", "Browser"),
            ("web_base_loader", "WebBaseLoader")
        ]
        
        for scraper_type, scraper_name in scraper_configs:
            print(f"\n--- Testing {scraper_name} Scraper ---")
            
            test_urls = self.test_urls["news"][:2]  # Limit to 2 URLs for each scraper type
            
            try:
                scraper = Scraper(
                    urls=test_urls,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    scraper=scraper_type,
                    worker_pool=worker_pool
                )
                
                start_time = time.time()
                results = await scraper.run()
                end_time = time.time()
                
                print(f"✓ {scraper_name} completed in {end_time - start_time:.2f}s")
                print(f"✓ Processed {len(results)} URLs successfully")
                
                for result in results:
                    url = result.get('url', 'Unknown')
                    content_len = len(result.get('raw_content', ''))
                    title = result.get('title', '')
                    images = len(result.get('image_urls', []))
                    
                    print(f"  └── {url}")
                    print(f"      Content: {content_len} chars, Images: {images}")
                    print(f"      Title: {title[:50]}..." if title else "      No title")
                    
                    # Validate individual result
                    success = self._validate_scraper_result_dict(result, scraper_name)
                    
                    self.results[f"{scraper_type}_{url}"] = {
                        "success": success,
                        "content_length": content_len,
                        "images_count": images,
                        "time": end_time - start_time,
                        "title": title,
                        "scraper_type": scraper_name
                    }
                
            except Exception as e:
                print(f"✗ Error with {scraper_name} scraper: {str(e)}")
                self.results[f"{scraper_type}_error"] = {
                    "success": False,
                    "error": str(e),
                    "scraper_type": scraper_name
                }
    
    def test_url_accessibility(self):
        """Test if URLs are accessible before scraping"""
        print("\n" + "="*50)
        print("TESTING URL ACCESSIBILITY")
        print("="*50)
        
        all_urls = []
        for category, urls in self.test_urls.items():
            all_urls.extend(urls)
        
        accessible_urls = []
        
        for url in all_urls:
            try:
                print(f"Testing: {url}")
                response = self.session.head(url, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    print(f"✓ Accessible (200 OK)")
                    accessible_urls.append(url)
                elif 300 <= response.status_code < 400:
                    print(f"✓ Redirected ({response.status_code})")
                    accessible_urls.append(url)
                else:
                    print(f"⚠ Status: {response.status_code}")
                    
            except Exception as e:
                print(f"✗ Error: {str(e)}")
        
        print(f"\nAccessible URLs: {len(accessible_urls)}/{len(all_urls)}")
        return accessible_urls
    
    def _validate_scraper_results(self, content: str, image_urls: List, title: str, scraper_name: str) -> bool:
        """Validate scraper results format for direct scraper calls"""
        if not isinstance(content, str):
            print(f"✗ {scraper_name}: Content should be string, got {type(content)}")
            return False
        
        if not isinstance(image_urls, list):
            print(f"✗ {scraper_name}: Image URLs should be list, got {type(image_urls)}")
            return False
        
        if not isinstance(title, str):
            print(f"✗ {scraper_name}: Title should be string, got {type(title)}")
            return False
        
        if len(content) < 50:  # Minimum content threshold
            print(f"⚠ {scraper_name}: Content seems too short ({len(content)} chars)")
        
        print(f"✓ {scraper_name}: Results format validated")
        return True
    
    def _validate_scraper_result_dict(self, result: Dict, scraper_name: str) -> bool:
        """Validate scraper result dictionary from main Scraper class"""
        required_fields = ['url', 'raw_content', 'image_urls', 'title']
        
        for field in required_fields:
            if field not in result:
                print(f"✗ {scraper_name}: Missing required field '{field}'")
                return False
        
        if result['raw_content'] is None:
            print(f"⚠ {scraper_name}: Content is None")
            return True  # This can be valid for failed scraping
        
        if not isinstance(result['raw_content'], str):
            print(f"✗ {scraper_name}: raw_content should be string")
            return False
        
        if not isinstance(result['image_urls'], list):
            print(f"✗ {scraper_name}: image_urls should be list")
            return False
        
        if not isinstance(result['title'], str):
            print(f"✗ {scraper_name}: title should be string")
            return False
        
        print(f"✓ {scraper_name}: Result dictionary validated")
        return True
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*70)
        print("SCRAPER TEST SUMMARY REPORT")
        print("="*70)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results.values() if r.get('success', False))
        
        print(f"Total Tests Run: {total_tests}")
        print(f"Successful Tests: {successful_tests}")
        print(f"Failed Tests: {total_tests - successful_tests}")
        print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        print("\n" + "-"*50)
        print("PERFORMANCE METRICS:")
        print("-"*50)
        
        # Calculate average content lengths and scraping times
        successful_results = [r for r in self.results.values() if r.get('success', False)]
        
        if successful_results:
            avg_content_length = sum(r.get('content_length', 0) for r in successful_results) / len(successful_results)
            avg_time = sum(r.get('time', 0) for r in successful_results) / len(successful_results)
            total_images = sum(r.get('images_count', 0) for r in successful_results)
            
            print(f"Average Content Length: {avg_content_length:.0f} characters")
            print(f"Average Scraping Time: {avg_time:.2f} seconds")
            print(f"Total Images Found: {total_images}")
            print(f"URLs with Substantial Content (>100 chars): {sum(1 for r in successful_results if r.get('has_content', False))}")
        
        print("\n" + "-"*50)
        print("DETAILED RESULTS:")
        print("-"*50)
        
        for test_name, result in self.results.items():
            if result.get('success'):
                scraper_type = test_name.split('_')[0]
                url = '_'.join(test_name.split('_')[1:]) if len(test_name.split('_')) > 1 else 'N/A'
                
                print(f"✓ {scraper_type.upper()}: {url[:50]}...")
                print(f"  └── Content: {result.get('content_length', 0)} chars, "
                      f"Images: {result.get('images_count', 0)}, "
                      f"Time: {result.get('time', 0):.2f}s")
            else:
                print(f"✗ {test_name}")
                print(f"  └── Error: {result.get('error', 'Unknown error')}")
        
        # Save detailed results to JSON file
        with open('scraper_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: scraper_test_results.json")
        
        return successful_tests == total_tests


async def main():
    """Main test execution function"""
    print("Starting Scraper Testing Suite...")
    print("This will test various scrapers with multiple URL types.")
    
    tester = ScraperTester()
    
    # First test URL accessibility
    accessible_urls = tester.test_url_accessibility()
    
    # Run scraper tests
    tester.test_beautiful_soup_scraper()
    await tester.test_scraper_with_worker_pool()
    
    # Generate final report
    all_passed = tester.generate_report()
    
    if all_passed:
        print("\n🎉 All scraper tests passed!")
        return 0
    else:
        print("\n⚠️  Some scraper tests failed. Check the report above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)