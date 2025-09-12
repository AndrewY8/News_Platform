"""
Database Utilities

Simple utilities for database management and initialization.
"""

import os
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def init_database(database_url: str = None):
    """Initialize database with correct schema"""
    if not database_url:
        database_url = os.getenv("DATABASE_URL", "sqlite:///./secure_news.db")
    
    try:
        from app import Base
        
        engine = create_engine(database_url)
        Base.metadata.create_all(bind=engine)
        
        print(f"✅ Database initialized: {database_url}")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


def get_database_stats(database_path: str = "secure_news.db"):
    """Get basic database statistics"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Get table counts
        tables = ['users', 'articles', 'user_interactions']
        stats = {}
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats[table] = count
            except sqlite3.OperationalError:
                stats[table] = "Table not found"
        
        # Get recent articles with relevance scores
        cursor.execute("""
            SELECT COUNT(*) FROM articles 
            WHERE relevance_score IS NOT NULL AND relevance_score > 0.5
        """)
        relevant_articles = cursor.fetchone()[0]
        stats['relevant_articles'] = relevant_articles
        
        conn.close()
        
        return stats
        
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # CLI interface
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_database()
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        stats = get_database_stats()
        print("\nDatabase Statistics:")
        print("-" * 20)
        for table, count in stats.items():
            print(f"{table}: {count}")
    else:
        print("Usage:")
        print("  python database_utils.py init   # Initialize database")
        print("  python database_utils.py stats  # Show statistics")