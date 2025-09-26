#!/usr/bin/env python3
"""
Startup script for the News Intelligence Backend
Handles environment setup and runs the FastAPI application
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['NEWSAPI_KEY', 'GEMINI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file")
        print("See README.md for setup instructions")
        return False
    
    print("✅ Environment variables configured")
    return True

def check_database():
    """Check if database exists and is accessible"""
    db_path = Path("secure_news.db")
    if not db_path.exists():
        print("⚠️  Database not found. Run 'python database_utils.py init' first")
        return False
    
    print("✅ Database found")
    return True

def main():
    """Main startup function"""
    print("🚀 Starting News Intelligence Backend...")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check database
    if not check_database():
        print("\nTo initialize database, run:")
        print("  python database_utils.py init")
        print("\nContinuing anyway...")
    
    print("\n🌐 Starting server on http://localhost:8004")
    print("📱 Frontend should be running on http://localhost:3000")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Run the FastAPI app
    port = int(os.getenv("PORT", 8004))  # EB can override it
    uvicorn.run(
        "main_app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level="info"
    )

if __name__ == "__main__":
    main()
