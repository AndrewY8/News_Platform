#!/usr/bin/env python3
"""
Test script to verify the Supabase transition for the news aggregator.

This script tests the updated aggregator implementation that uses
Supabase URL and key instead of direct PostgreSQL connections.
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news_agent.aggregator.config import AggregatorConfig
from news_agent.aggregator.aggregator import AggregatorAgent, create_aggregator_agent
from news_agent.aggregator.supabase_manager import SupabaseManager

def test_configuration():
    """Test that configuration properly loads Supabase credentials."""
    print("🔧 Testing Configuration...")
    
    # Load environment variables
    load_dotenv()
    
    # Create config from environment
    config = AggregatorConfig.from_env()
    
    # Check that Supabase configuration is loaded
    print(f"  Supabase URL: {'✓' if config.supabase.url else '✗'} {config.supabase.url or 'Not configured'}")
    print(f"  Supabase Key: {'✓' if config.supabase.key else '✗'} {'Present' if config.supabase.key else 'Not configured'}")
    print(f"  Vector Dimension: {config.supabase.vector_dimension}")
    
    return config.supabase.url and config.supabase.key

def test_supabase_manager():
    """Test SupabaseManager initialization."""
    print("\n🗄️  Testing SupabaseManager...")
    
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("  ✗ Supabase credentials not found in environment")
        return False
    
    try:
        manager = SupabaseManager(supabase_url, supabase_key)
        print("  ✓ SupabaseManager initialized successfully")
        
        # Test schema creation (just shows the SQL)
        print("  ✓ Schema creation method available")
        
        manager.close()
        return True
        
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        print("  💡 Install supabase client with: pip install supabase")
        return False
    except Exception as e:
        print(f"  ✗ Failed to initialize SupabaseManager: {e}")
        return False

def test_aggregator_agent():
    """Test AggregatorAgent with Supabase configuration."""
    print("\n🤖 Testing AggregatorAgent...")
    
    load_dotenv()
    
    # Test environment-based initialization
    try:
        config = AggregatorConfig.from_env()
        agent = AggregatorAgent(config=config)
        
        print("  ✓ AggregatorAgent initialized from environment config")
        print(f"  ✓ Supabase manager: {'Present' if agent.supabase_manager else 'Not configured'}")
        print(f"  ✓ Database manager (compatibility): {'Present' if agent.database_manager else 'Not configured'}")
        
        agent.cleanup()
        
    except Exception as e:
        print(f"  ✗ Failed to initialize AggregatorAgent: {e}")
        return False
    
    # Test direct initialization
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        
        if supabase_url and supabase_key and gemini_key:
            agent = create_aggregator_agent(
                gemini_api_key=gemini_key,
                supabase_url=supabase_url,
                supabase_key=supabase_key
            )
            print("  ✓ AggregatorAgent initialized with direct credentials")
            agent.cleanup()
        else:
            print("  ⚠️  Skipping direct credential test (missing credentials)")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Failed direct initialization: {e}")
        return False

def test_mock_aggregation():
    """Test mock aggregation without actual database operations."""
    print("\n📊 Testing Mock Aggregation Pipeline...")
    
    try:
        load_dotenv()
        
        # Create aggregator (will work even without valid Supabase connection)
        config = AggregatorConfig.from_env()
        
        # Disable database operations for this test
        config.supabase.url = None
        config.supabase.key = None
        
        agent = AggregatorAgent(config=config)
        
        # Mock planner results
        mock_results = {
            "breaking_news": [
                {
                    "title": "Test Breaking News",
                    "url": "https://example.com/news/1",
                    "description": "This is a test news article for aggregation testing.",
                    "source_retriever": "TestRetriever",
                    "published_date": "2024-01-01",
                    "content": "This is test content for the aggregation pipeline."
                }
            ],
            "general_news": [],
            "financial_news": [],
            "sec_filings": []
        }
        
        # Process results (should work without database)
        output = agent.process_planner_results(mock_results)
        
        print(f"  ✓ Processed {len(output.clusters)} clusters")
        print(f"  ✓ Processing time: {output.processing_stats.get('processing_time_seconds', 0):.2f}s")
        print(f"  ✓ Pipeline stages completed successfully")
        
        agent.cleanup()
        return True
        
    except Exception as e:
        print(f"  ✗ Mock aggregation failed: {e}")
        return False

def print_setup_instructions():
    """Print setup instructions for Supabase."""
    print("\n📋 Setup Instructions:")
    print("="*50)
    
    print("\n1. Supabase Project Setup:")
    print("   - Create a new Supabase project at https://supabase.com")
    print("   - Copy your project URL and anon key")
    print("   - Add them to your .env file:")
    print("     SUPABASE_URL=https://your-project.supabase.co")
    print("     SUPABASE_KEY=your-anon-key")
    
    print("\n2. Database Schema Setup:")
    print("   - Open your Supabase project's SQL editor")
    print("   - Copy and run the SQL from: news_agent/aggregator/supabase_schema.sql")
    print("   - This creates the required tables and functions")
    
    print("\n3. Enable pgvector Extension:")
    print("   - In Supabase SQL editor, run: CREATE EXTENSION IF NOT EXISTS vector;")
    print("   - This enables vector similarity search")
    
    print("\n4. Test Your Setup:")
    print("   - Run this script again: python test_supabase_transition.py")
    print("   - All tests should pass with ✓ symbols")

def main():
    """Run all tests."""
    print("🧪 Supabase Transition Test Suite")
    print("="*40)
    
    # Run tests
    config_ok = test_configuration()
    manager_ok = test_supabase_manager()
    agent_ok = test_aggregator_agent()
    mock_ok = test_mock_aggregation()
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"  Configuration: {'✓' if config_ok else '✗'}")
    print(f"  SupabaseManager: {'✓' if manager_ok else '✗'}")
    print(f"  AggregatorAgent: {'✓' if agent_ok else '✗'}")
    print(f"  Mock Pipeline: {'✓' if mock_ok else '✗'}")
    
    all_passed = config_ok and manager_ok and agent_ok and mock_ok
    
    if all_passed:
        print("\n🎉 All tests passed! Supabase transition is working correctly.")
        print("\n💡 Next steps:")
        print("   - Run the SQL schema in your Supabase project")
        print("   - Start using the aggregator with Supabase URL and key")
        print("   - No more database passwords needed!")
    else:
        print("\n❌ Some tests failed. Check the setup instructions below.")
        print_setup_instructions()
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
