"""
Migration script for Daily Planet tables
Run this to add new tables to existing database
"""

import os
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models
from daily_planet_models import (
    Base,
    UserPreference,
    UserTopic,
    UserLayoutSection,
    ExcludedContent,
    EnhancedUserInteraction,
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./secure_news.db")


def check_table_exists(engine, table_name):
    """Check if a table already exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate():
    """Run the migration to add Daily Planet tables"""
    print(f"🔄 Starting Daily Planet migration...")
    print(f"📁 Database: {DATABASE_URL}")

    # Create engine
    engine = create_engine(DATABASE_URL)

    # Check which tables already exist
    tables_to_create = [
        ("user_preferences", UserPreference),
        ("user_topics", UserTopic),
        ("user_layout_sections", UserLayoutSection),
        ("excluded_content", ExcludedContent),
        ("enhanced_user_interactions", EnhancedUserInteraction),
    ]

    existing_tables = []
    new_tables = []

    for table_name, model in tables_to_create:
        if check_table_exists(engine, table_name):
            existing_tables.append(table_name)
        else:
            new_tables.append(table_name)

    # Report status
    if existing_tables:
        print(f"\n✅ Already exists: {', '.join(existing_tables)}")

    if new_tables:
        print(f"\n🆕 Will create: {', '.join(new_tables)}")

        # Create new tables
        try:
            Base.metadata.create_all(bind=engine, checkfirst=True)
            print(f"\n✅ Successfully created {len(new_tables)} new tables!")
        except Exception as e:
            print(f"\n❌ Error creating tables: {e}")
            sys.exit(1)
    else:
        print("\n✅ All tables already exist. No migration needed.")

    print("\n✅ Migration complete!")

    # Verify tables were created
    print("\n📊 Verifying tables...")
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()

    for table_name, _ in tables_to_create:
        if table_name in all_tables:
            print(f"  ✓ {table_name}")
        else:
            print(f"  ✗ {table_name} - FAILED TO CREATE")

    return True


def rollback():
    """Rollback migration by dropping Daily Planet tables"""
    print(f"⚠️  Rolling back Daily Planet migration...")
    print(f"📁 Database: {DATABASE_URL}")

    response = input("\n⚠️  This will DELETE all Daily Planet tables and data. Continue? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Rollback cancelled.")
        return False

    engine = create_engine(DATABASE_URL)

    tables_to_drop = [
        "enhanced_user_interactions",
        "excluded_content",
        "user_layout_sections",
        "user_topics",
        "user_preferences",
    ]

    for table_name in tables_to_drop:
        if check_table_exists(engine, table_name):
            try:
                engine.execute(f"DROP TABLE {table_name}")
                print(f"  ✓ Dropped {table_name}")
            except Exception as e:
                print(f"  ✗ Failed to drop {table_name}: {e}")
        else:
            print(f"  - {table_name} (doesn't exist)")

    print("\n✅ Rollback complete!")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Daily Planet database migration")
    parser.add_argument(
        "command",
        choices=["migrate", "rollback", "status"],
        help="Migration command to run"
    )

    args = parser.parse_args()

    if args.command == "migrate":
        migrate()
    elif args.command == "rollback":
        rollback()
    elif args.command == "status":
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()

        print(f"\n📊 Daily Planet Tables Status:")
        print(f"📁 Database: {DATABASE_URL}\n")

        dp_tables = [
            "user_preferences",
            "user_topics",
            "user_layout_sections",
            "excluded_content",
            "enhanced_user_interactions",
        ]

        for table in dp_tables:
            status = "✅ EXISTS" if table in all_tables else "❌ MISSING"
            print(f"  {table}: {status}")

            if table in all_tables:
                # Show row count
                result = engine.execute(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                print(f"    └─ {count} rows")
