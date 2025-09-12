#!/usr/bin/env python3
"""
Master test runner for the news_agent retriever and scraper testing suite.
Runs all tests in sequence and provides a consolidated report.
"""

import asyncio
import sys
import time
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import test modules
import test_retrievers
import test_scrapers
import test_integration
import test_aggregator_e2e


class MasterTestRunner:
    """Orchestrates all tests and provides consolidated reporting"""
    
    def __init__(self):
        self.start_time = None
        self.results = {}
        
    async def run_all_tests(self):
        """Run all test suites in sequence"""
        print("="*80)
        print("NEWS AGENT RETRIEVER & SCRAPER TEST SUITE")
        print("="*80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        self.start_time = time.time()
        
        # Test 1: Retrievers
        print("\n🔍 PHASE 1: TESTING RETRIEVERS")
        print("-" * 50)
        try:
            retriever_result = test_retrievers.main()
            self.results['retrievers'] = {
                'success': retriever_result == 0,
                'exit_code': retriever_result
            }
        except Exception as e:
            print(f"✗ Retriever tests failed with exception: {e}")
            self.results['retrievers'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 2: Scrapers
        print("\n🕷️ PHASE 2: TESTING SCRAPERS")
        print("-" * 50)
        try:
            scraper_result = await test_scrapers.main()
            self.results['scrapers'] = {
                'success': scraper_result == 0,
                'exit_code': scraper_result
            }
        except Exception as e:
            print(f"✗ Scraper tests failed with exception: {e}")
            self.results['scrapers'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 3: Integration
        print("\n🔄 PHASE 3: TESTING INTEGRATION")
        print("-" * 50)
        try:
            integration_result = await test_integration.main()
            self.results['integration'] = {
                'success': integration_result == 0,
                'exit_code': integration_result
            }
        except Exception as e:
            print(f"✗ Integration tests failed with exception: {e}")
            self.results['integration'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 4: Aggregator End-to-End
        print("\n🧠 PHASE 4: TESTING AGGREGATOR END-TO-END")
        print("-" * 50)
        try:
            aggregator_result = await test_aggregator_e2e.main()
            self.results['aggregator_e2e'] = {
                'success': aggregator_result == 0,
                'exit_code': aggregator_result
            }
        except Exception as e:
            print(f"✗ Aggregator E2E tests failed with exception: {e}")
            self.results['aggregator_e2e'] = {
                'success': False,
                'error': str(e)
            }
    
    def generate_master_report(self):
        """Generate the master test report"""
        end_time = time.time()
        total_time = end_time - self.start_time
        
        print("\n" + "="*80)
        print("MASTER TEST SUITE RESULTS")
        print("="*80)
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total execution time: {total_time:.2f} seconds")
        print("="*80)
        
        # Count successes and failures
        total_phases = len(self.results)
        successful_phases = sum(1 for r in self.results.values() if r.get('success', False))
        
        print(f"\nOVERALL SUMMARY:")
        print(f"├── Total test phases: {total_phases}")
        print(f"├── Successful phases: {successful_phases}")
        print(f"├── Failed phases: {total_phases - successful_phases}")
        print(f"└── Overall success rate: {(successful_phases/total_phases)*100:.1f}%")
        
        # Detailed phase results
        print(f"\nPHASE DETAILS:")
        phase_icons = {
            'retrievers': '🔍',
            'scrapers': '🕷️',
            'integration': '🔄',
            'aggregator_e2e': '🧠'
        }
        
        for phase, result in self.results.items():
            icon = phase_icons.get(phase, '📋')
            if result.get('success'):
                print(f"├── {icon} {phase.upper()}: ✅ PASSED")
            else:
                print(f"├── {icon} {phase.upper()}: ❌ FAILED")
                if 'error' in result:
                    print(f"│   └── Error: {result['error']}")
                elif 'exit_code' in result:
                    print(f"│   └── Exit code: {result['exit_code']}")
        
        # Output files generated
        print(f"\nGENERATED FILES:")
        output_files = [
            'retriever_test_results.json',
            'scraper_test_results.json',
            'integration_test_results.json',
            'aggregator_e2e_test_results.json'
        ]
        
        for file in output_files:
            if os.path.exists(file):
                print(f"├── 📄 {file}")
            else:
                print(f"├── ❓ {file} (not found)")
        
        # Recommendations
        print(f"\nRECOMMENDATIONS:")
        if successful_phases == total_phases:
            print("🎉 All tests passed! Your news aggregation system is working correctly.")
            print("   ✓ Retrievers are finding relevant URLs")
            print("   ✓ Scrapers are extracting content successfully")
            print("   ✓ Integration between components is working")
            print("   ✓ Aggregator is clustering and summarizing content")
            print("   ✓ Output formats are consistent")
        else:
            print("⚠️  Some tests failed. Please review the detailed reports above.")
            
            if not self.results.get('retrievers', {}).get('success'):
                print("   • Check retriever API keys and network connectivity")
                print("   • Verify retriever implementations match expected interface")
            
            if not self.results.get('scrapers', {}).get('success'):
                print("   • Check URL accessibility and scraper dependencies")
                print("   • Verify HTML parsing and content extraction logic")
            
            if not self.results.get('integration', {}).get('success'):
                print("   • Check compatibility between retrievers and scrapers")
                print("   • Verify data flow and format consistency")
            
            if not self.results.get('aggregator_e2e', {}).get('success'):
                print("   • Check Gemini API key configuration")
                print("   • Verify aggregator component dependencies")
                print("   • Review clustering and summarization performance")
        
        # Next steps
        print(f"\nNEXT STEPS:")
        print("1. Review detailed JSON reports for specific failure analysis")
        print("2. Check individual test outputs for debugging information")
        print("3. Verify API keys and environment variables if needed")
        print("4. Test with different queries and URL types")
        print("5. Monitor performance metrics for optimization opportunities")
        
        return successful_phases == total_phases


async def main():
    """Main execution function"""
    runner = MasterTestRunner()
    
    try:
        await runner.run_all_tests()
        all_passed = runner.generate_master_report()
        
        if all_passed:
            print("\n🎯 SUCCESS: All tests completed successfully!")
            return 0
        else:
            print("\n⚠️  WARNING: Some tests failed. See report above.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 2
    except Exception as e:
        print(f"\n❌ Test suite failed with unexpected error: {e}")
        return 3


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"Fatal error running test suite: {e}")
        sys.exit(4)
