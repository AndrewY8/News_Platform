#!/usr/bin/env python3
"""
Quick test to verify Supabase configuration is loaded correctly.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=== Supabase Configuration Test ===")

# Check environment variables
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
gemini_key = os.getenv('GEMINI_API_KEY')

print(f"SUPABASE_URL: {'✓' if supabase_url else '✗'} {supabase_url or 'Not set'}")
print(f"SUPABASE_KEY: {'✓' if supabase_key else '✗'} {'Present' if supabase_key else 'Not set'}")
print(f"GEMINI_API_KEY: {'✓' if gemini_key else '✗'} {'Present' if gemini_key else 'Not set'}")

# Test configuration loading
try:
    from news_agent.aggregator.config import AggregatorConfig
    config = AggregatorConfig.from_env()
    
    print(f"\nConfiguration from AggregatorConfig.from_env():")
    print(f"  config.supabase.url: {'✓' if config.supabase.url else '✗'} {config.supabase.url or 'Not configured'}")
    print(f"  config.supabase.key: {'✓' if config.supabase.key else '✗'} {'Present' if config.supabase.key else 'Not configured'}")
    
    # Test aggregator creation
    if supabase_url and supabase_key and gemini_key:
        from news_agent.aggregator.aggregator import create_aggregator_agent
        
        print(f"\nTesting aggregator creation with Supabase...")
        aggregator = create_aggregator_agent(
            gemini_api_key=gemini_key,
            supabase_url=supabase_url,
            supabase_key=supabase_key
        )
        
        print(f"  Aggregator created: ✓")
        print(f"  Supabase manager: {'✓' if hasattr(aggregator, 'supabase_manager') and aggregator.supabase_manager else '✗'}")
        print(f"  Database manager (compatibility): {'✓' if hasattr(aggregator, 'database_manager') and aggregator.database_manager else '✗'}")
        
        aggregator.cleanup()
    else:
        print(f"\nSkipping aggregator test - missing credentials")
        
except Exception as e:
    print(f"\nConfiguration test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Configuration Test Complete ===")
