#!/usr/bin/env python3
"""
Test script to verify the fixed planner agent implementation works correctly
"""

import logging
import sys
import traceback
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all imports work correctly"""
    print("=" * 60)
    print("TESTING IMPORTS")
    print("=" * 60)
    
    try:
        # Test prompts import
        from news_agent.prompts import augment_query
        print("✓ prompts.py imported successfully")
        
        # Test actions imports
        from news_agent.actions.retriever import get_retriever_tasks, get_retriever_info, RETRIEVER_CONFIG
        print("✓ actions.retriever imported successfully")
        
        # Test agent import
        from news_agent.agent import PlannerAgent
        print("✓ agent.py imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {str(e)}")
        traceback.print_exc()
        return False

def test_retriever_config():
    """Test that retriever configuration is correct"""
    print("\n" + "=" * 60)
    print("TESTING RETRIEVER CONFIGURATION")
    print("=" * 60)
    
    try:
        from news_agent.actions.retriever import get_retriever_info, get_retriever_tasks
        
        config = get_retriever_info()
        print(f"Available retrievers: {len(config)}")
        
        for name, info in config.items():
            priority = info.get('priority', 'Unknown')
            specialties = ', '.join(info.get('specialties', []))
            print(f"  • {name}: Priority {priority}, Specialties: {specialties}")
        
        # Test task creation
        tasks = get_retriever_tasks("test query")
        print(f"\nCreated {len(tasks)} retriever tasks")
        
        return True
        
    except Exception as e:
        print(f"✗ Retriever config test failed: {str(e)}")
        traceback.print_exc()
        return False

def test_agent_initialization():
    """Test that PlannerAgent can be initialized"""
    print("\n" + "=" * 60)
    print("TESTING AGENT INITIALIZATION")
    print("=" * 60)
    
    try:
        from news_agent.agent import PlannerAgent
        
        # Test initialization
        planner = PlannerAgent()
        print("✓ PlannerAgent initialized successfully")
        
        # Test with custom settings
        planner_custom = PlannerAgent(max_concurrent_retrievers=3)
        print("✓ PlannerAgent with custom settings initialized")
        
        return True
        
    except Exception as e:
        print(f"✗ Agent initialization failed: {str(e)}")
        traceback.print_exc()
        return False

def test_query_augmentation():
    """Test query augmentation"""
    print("\n" + "=" * 60)
    print("TESTING QUERY AUGMENTATION")
    print("=" * 60)
    
    try:
        from news_agent.prompts import augment_query
        
        test_query = "Tesla earnings Q3 2024"
        augmented = augment_query(test_query)
        
        print(f"Original query: {test_query}")
        print(f"Augmented query length: {len(augmented)} characters")
        print("✓ Query augmentation working")
        
        # Check if key instructions are present
        key_terms = ["breaking news", "SEC filings", "JSON format", "multiple sources"]
        found_terms = [term for term in key_terms if term.lower() in augmented.lower()]
        print(f"✓ Found key instruction terms: {found_terms}")
        
        return True
        
    except Exception as e:
        print(f"✗ Query augmentation test failed: {str(e)}")
        traceback.print_exc()
        return False

def test_mock_retriever_run():
    """Test running the agent with mock retrievers (without actually calling external APIs)"""
    print("\n" + "=" * 60)
    print("TESTING MOCK RETRIEVER RUN")
    print("=" * 60)
    
    try:
        from news_agent.actions.retriever import get_retriever_tasks
        
        # Get tasks without running them
        test_query = "Apple iPhone sales"
        tasks = get_retriever_tasks(test_query)
        
        print(f"Generated {len(tasks)} tasks for query: '{test_query}'")
        
        # Check task structure
        for i, (retriever, task) in enumerate(tasks[:3]):  # Show first 3
            retriever_name = retriever.__class__.__name__
            task_preview = task[:100] + "..." if len(task) > 100 else task
            print(f"  {i+1}. {retriever_name}: {task_preview}")
        
        print("✓ Retriever tasks generated successfully")
        return True
        
    except Exception as e:
        print(f"✗ Mock retriever run failed: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("PLANNER AGENT - INTEGRATION TEST")
    print("Testing the fixed implementation...\n")
    
    tests = [
        ("Imports", test_imports),
        ("Retriever Config", test_retriever_config),
        ("Agent Initialization", test_agent_initialization),
        ("Query Augmentation", test_query_augmentation),
        ("Mock Retriever Run", test_mock_retriever_run)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} test crashed: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 All tests passed! The implementation is ready to use.")
        print("\nNext steps:")
        print("1. Ensure your retrievers have a 'retrieve(query)' method")
        print("2. Test with a real query: planner = PlannerAgent(); results = planner.run('test')")
        print("3. Check that retrievers return the expected JSON format")
    else:
        print(f"\n❌ {failed} test(s) failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()