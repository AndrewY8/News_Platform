#!/usr/bin/env python3
"""
Output format validation tests for the news_agent retriever and scraper system.
Validates that all components produce output in the expected format.
"""

import asyncio
import json
import os
import sys
from typing import List, Dict, Any, Union

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from news_agent.retrievers.tavily.tavily_search import TavilySearch
from news_agent.retrievers.duckduckgo.duckduckgo import Duckduckgo
from news_agent.scraper.scraper import Scraper
from gpt_researcher.utils.workers import WorkerPool


class OutputValidationTester:
    """Validates output format consistency across all components"""
    
    def __init__(self):
        self.validation_results = {}
        self.expected_formats = {
            'retriever_result': {
                'type': list,
                'item_type': dict,
                'required_fields': ['href', 'body'],
                'optional_fields': ['title', 'snippet']
            },
            'scraper_result': {
                'type': dict,
                'required_fields': ['url', 'raw_content', 'image_urls', 'title'],
                'field_types': {
                    'url': str,
                    'raw_content': (str, type(None)),
                    'image_urls': list,
                    'title': str
                }
            },
            'image_url_format': {
                'type': dict,
                'required_fields': ['url', 'score'],
                'field_types': {
                    'url': str,
                    'score': (int, float)
                }
            }
        }
        
    def validate_retriever_output_format(self):
        """Test retriever output format consistency"""
        print("\n" + "="*60)
        print("VALIDATING RETRIEVER OUTPUT FORMATS")
        print("="*60)
        
        test_query = "Python programming tutorial"
        
        # Test Tavily format
        print("\n--- Tavily Search Format Validation ---")
        try:
            tavily = TavilySearch(query=test_query)
            tavily_results = tavily.search(max_results=3)
            
            tavily_validation = self._validate_retriever_format(
                tavily_results, "TavilySearch"
            )
            self.validation_results['tavily_format'] = tavily_validation
            
        except Exception as e:
            print(f"✗ Tavily format test failed: {e}")
            self.validation_results['tavily_format'] = {'valid': False, 'error': str(e)}
        
        # Test DuckDuckGo format
        print("\n--- DuckDuckGo Search Format Validation ---")
        try:
            ddg = Duckduckgo(query=test_query)
            ddg_results = ddg.search(max_results=3)
            
            ddg_validation = self._validate_retriever_format(
                ddg_results, "DuckDuckGo"
            )
            self.validation_results['ddg_format'] = ddg_validation
            
        except Exception as e:
            print(f"✗ DuckDuckGo format test failed: {e}")
            self.validation_results['ddg_format'] = {'valid': False, 'error': str(e)}
    
    async def validate_scraper_output_format(self):
        """Test scraper output format consistency"""
        print("\n" + "="*60)
        print("VALIDATING SCRAPER OUTPUT FORMATS")
        print("="*60)
        
        # Test URLs with different content types
        test_urls = [
            "https://www.example.com",
            "https://httpbin.org/html"
        ]
        
        worker_pool = WorkerPool(max_workers=2)
        
        # Test BeautifulSoup scraper
        print("\n--- BeautifulSoup Scraper Format Validation ---")
        try:
            scraper = Scraper(
                urls=test_urls,
                user_agent='Mozilla/5.0 (Test)',
                scraper='bs',
                worker_pool=worker_pool
            )
            
            bs_results = await scraper.run()
            bs_validation = self._validate_scraper_format(bs_results, "BeautifulSoup")
            self.validation_results['bs_format'] = bs_validation
            
        except Exception as e:
            print(f"✗ BeautifulSoup format test failed: {e}")
            self.validation_results['bs_format'] = {'valid': False, 'error': str(e)}
    
    def _validate_retriever_format(self, results: List[Dict], retriever_name: str) -> Dict:
        """Validate retriever output format against expected schema"""
        validation = {
            'valid': True,
            'issues': [],
            'retriever': retriever_name,
            'results_count': len(results) if results else 0
        }
        
        if not isinstance(results, list):
            validation['valid'] = False
            validation['issues'].append(f"Results should be list, got {type(results)}")
            print(f"✗ {retriever_name}: Results should be list")
            return validation
        
        if not results:
            print(f"⚠ {retriever_name}: No results to validate (empty list)")
            return validation
        
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                issue = f"Result {i} should be dict, got {type(result)}"
                validation['issues'].append(issue)
                validation['valid'] = False
                print(f"✗ {retriever_name}: {issue}")
                continue
            
            # Check for URL field (flexible field names)
            url_fields = ['href', 'link', 'url']
            has_url = any(field in result for field in url_fields)
            
            if not has_url:
                issue = f"Result {i} missing URL field (tried: {url_fields})"
                validation['issues'].append(issue)
                validation['valid'] = False
                print(f"✗ {retriever_name}: {issue}")
            
            # Check for content field (flexible field names)
            content_fields = ['body', 'content', 'title', 'snippet']
            has_content = any(field in result for field in content_fields)
            
            if not has_content:
                issue = f"Result {i} missing content field (tried: {content_fields})"
                validation['issues'].append(issue)
                validation['valid'] = False
                print(f"✗ {retriever_name}: {issue}")
            
            # Validate URL format if present
            for url_field in url_fields:
                if url_field in result:
                    url_value = result[url_field]
                    if not isinstance(url_value, str) or not url_value.startswith(('http://', 'https://')):
                        issue = f"Result {i} {url_field} should be valid URL string"
                        validation['issues'].append(issue)
                        validation['valid'] = False
                        print(f"✗ {retriever_name}: {issue}")
        
        if validation['valid']:
            print(f"✓ {retriever_name}: All {len(results)} results have valid format")
        else:
            print(f"✗ {retriever_name}: Found {len(validation['issues'])} format issues")
        
        return validation
    
    def _validate_scraper_format(self, results: List[Dict], scraper_name: str) -> Dict:
        """Validate scraper output format against expected schema"""
        validation = {
            'valid': True,
            'issues': [],
            'scraper': scraper_name,
            'results_count': len(results) if results else 0
        }
        
        if not isinstance(results, list):
            validation['valid'] = False
            validation['issues'].append(f"Results should be list, got {type(results)}")
            print(f"✗ {scraper_name}: Results should be list")
            return validation
        
        if not results:
            print(f"⚠ {scraper_name}: No results to validate (empty list)")
            return validation
        
        required_fields = ['url', 'raw_content', 'image_urls', 'title']
        
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                issue = f"Result {i} should be dict, got {type(result)}"
                validation['issues'].append(issue)
                validation['valid'] = False
                print(f"✗ {scraper_name}: {issue}")
                continue
            
            # Check required fields
            for field in required_fields:
                if field not in result:
                    issue = f"Result {i} missing required field '{field}'"
                    validation['issues'].append(issue)
                    validation['valid'] = False
                    print(f"✗ {scraper_name}: {issue}")
            
            # Validate field types
            if 'url' in result and not isinstance(result['url'], str):
                issue = f"Result {i} 'url' should be string"
                validation['issues'].append(issue)
                validation['valid'] = False
                print(f"✗ {scraper_name}: {issue}")
            
            if 'raw_content' in result:
                content = result['raw_content']
                if content is not None and not isinstance(content, str):
                    issue = f"Result {i} 'raw_content' should be string or None"
                    validation['issues'].append(issue)
                    validation['valid'] = False
                    print(f"✗ {scraper_name}: {issue}")
            
            if 'title' in result and not isinstance(result['title'], str):
                issue = f"Result {i} 'title' should be string"
                validation['issues'].append(issue)
                validation['valid'] = False
                print(f"✗ {scraper_name}: {issue}")
            
            # Validate image_urls format
            if 'image_urls' in result:
                if not isinstance(result['image_urls'], list):
                    issue = f"Result {i} 'image_urls' should be list"
                    validation['issues'].append(issue)
                    validation['valid'] = False
                    print(f"✗ {scraper_name}: {issue}")
                else:
                    # Validate each image URL entry
                    for j, img in enumerate(result['image_urls']):
                        img_validation = self._validate_image_url_format(img, f"Result {i} image {j}")
                        if not img_validation['valid']:
                            validation['issues'].extend(img_validation['issues'])
                            validation['valid'] = False
        
        if validation['valid']:
            print(f"✓ {scraper_name}: All {len(results)} results have valid format")
        else:
            print(f"✗ {scraper_name}: Found {len(validation['issues'])} format issues")
        
        return validation
    
    def _validate_image_url_format(self, image_item: Any, context: str) -> Dict:
        """Validate individual image URL format"""
        validation = {'valid': True, 'issues': []}
        
        if isinstance(image_item, str):
            # Simple string URL format (acceptable)
            if not image_item.startswith(('http://', 'https://')):
                validation['valid'] = False
                validation['issues'].append(f"{context}: Image URL should start with http:// or https://")
        
        elif isinstance(image_item, dict):
            # Dictionary format with url and score (preferred)
            if 'url' not in image_item:
                validation['valid'] = False
                validation['issues'].append(f"{context}: Image dict missing 'url' field")
            
            if 'score' not in image_item:
                validation['valid'] = False
                validation['issues'].append(f"{context}: Image dict missing 'score' field")
            
            if 'url' in image_item and not isinstance(image_item['url'], str):
                validation['valid'] = False
                validation['issues'].append(f"{context}: Image 'url' should be string")
            
            if 'score' in image_item and not isinstance(image_item['score'], (int, float)):
                validation['valid'] = False
                validation['issues'].append(f"{context}: Image 'score' should be number")
        
        else:
            validation['valid'] = False
            validation['issues'].append(f"{context}: Image should be string URL or dict with url/score")
        
        return validation
    
    def test_cross_component_compatibility(self):
        """Test that retriever output can be properly consumed by scrapers"""
        print("\n" + "="*60)
        print("TESTING CROSS-COMPONENT COMPATIBILITY")
        print("="*60)
        
        compatibility_issues = []
        
        # Test format compatibility between components
        if 'tavily_format' in self.validation_results and self.validation_results['tavily_format'].get('valid'):
            print("✓ Tavily retriever format is valid")
        else:
            compatibility_issues.append("Tavily retriever format issues")
        
        if 'ddg_format' in self.validation_results and self.validation_results['ddg_format'].get('valid'):
            print("✓ DuckDuckGo retriever format is valid")
        else:
            compatibility_issues.append("DuckDuckGo retriever format issues")
        
        if 'bs_format' in self.validation_results and self.validation_results['bs_format'].get('valid'):
            print("✓ BeautifulSoup scraper format is valid")
        else:
            compatibility_issues.append("BeautifulSoup scraper format issues")
        
        # Test URL extraction compatibility
        print("\n--- URL Extraction Compatibility ---")
        test_retriever_result = [
            {'href': 'https://example.com', 'body': 'test content'},
            {'link': 'https://test.com', 'title': 'test title'}
        ]
        
        extractable_urls = []
        for result in test_retriever_result:
            url = result.get('href') or result.get('link') or result.get('url')
            if url:
                extractable_urls.append(url)
        
        if len(extractable_urls) == len(test_retriever_result):
            print("✓ All retriever results can be converted to scraper input URLs")
        else:
            compatibility_issues.append(f"URL extraction: only {len(extractable_urls)}/{len(test_retriever_result)} URLs extractable")
        
        if compatibility_issues:
            print(f"\n⚠️ Found {len(compatibility_issues)} compatibility issues:")
            for issue in compatibility_issues:
                print(f"  - {issue}")
        else:
            print("\n✅ All components have compatible formats")
        
        return len(compatibility_issues) == 0
    
    def generate_validation_report(self):
        """Generate comprehensive validation report"""
        print("\n" + "="*70)
        print("OUTPUT FORMAT VALIDATION REPORT")
        print("="*70)
        
        total_validations = len(self.validation_results)
        successful_validations = sum(1 for v in self.validation_results.values() 
                                   if v.get('valid', False))
        
        print(f"Total Validations: {total_validations}")
        print(f"Successful Validations: {successful_validations}")
        print(f"Failed Validations: {total_validations - successful_validations}")
        print(f"Validation Success Rate: {(successful_validations/total_validations)*100:.1f}%")
        
        print(f"\n{'-'*50}")
        print("DETAILED VALIDATION RESULTS")
        print(f"{'-'*50}")
        
        for component, validation in self.validation_results.items():
            if validation.get('valid'):
                print(f"✅ {component.upper()}: Valid format")
                print(f"   └── Results validated: {validation.get('results_count', 0)}")
            else:
                print(f"❌ {component.upper()}: Format issues found")
                if 'issues' in validation:
                    for issue in validation['issues'][:3]:  # Show first 3 issues
                        print(f"   └── {issue}")
                    if len(validation['issues']) > 3:
                        print(f"   └── ... and {len(validation['issues']) - 3} more issues")
                if 'error' in validation:
                    print(f"   └── Error: {validation['error']}")
        
        # Test compatibility
        compatibility_ok = self.test_cross_component_compatibility()
        
        # Save validation results
        with open('output_validation_results.json', 'w') as f:
            json.dump(self.validation_results, f, indent=2, default=str)
        
        print(f"\nValidation results saved to: output_validation_results.json")
        
        return successful_validations == total_validations and compatibility_ok


async def main():
    """Main validation test execution"""
    print("Starting Output Format Validation Suite...")
    print("This validates that all components produce consistent output formats.")
    
    tester = OutputValidationTester()
    
    # Run validation tests
    tester.validate_retriever_output_format()
    await tester.validate_scraper_output_format()
    
    # Generate validation report
    all_valid = tester.generate_validation_report()
    
    if all_valid:
        print("\n🎉 All output formats are valid and compatible!")
        return 0
    else:
        print("\n⚠️ Some output format issues found. Check the report above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)