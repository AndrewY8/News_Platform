"""
Update Google ticker from GOOGL to GOOG in Supabase database
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from deep_news_agent.db.research_db_manager import ResearchDBManager

# Load environment
load_dotenv(Path(__file__).parent.parent / '.env')

def update_google_ticker():
    """Update Google company ticker from GOOGL to GOOG"""

    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return

    # Initialize database manager
    print("🔌 Connecting to Supabase...")
    db_manager = ResearchDBManager(supabase_url, supabase_key)

    print("\n" + "="*80)
    print("📊 GOOGLE TICKER UPDATE")
    print("="*80)

    # Step 1: Check current Google company record
    print("\n1️⃣ Checking for GOOGL company record...")

    try:
        googl_result = db_manager.supabase.table("companies").select("*").eq("name", "GOOGL").execute()

        if googl_result.data:
            company = googl_result.data[0]
            print(f"✅ Found GOOGL company:")
            print(f"   ID: {company['id']}")
            print(f"   Name: {company['name']}")
            print(f"   Business Areas: {company.get('business_areas', 'N/A')}")
            print(f"   Created: {company.get('created_at', 'N/A')}")

            company_id = company['id']

            # Step 2: Check if GOOG already exists
            print("\n2️⃣ Checking if GOOG already exists...")
            goog_result = db_manager.supabase.table("companies").select("*").eq("name", "GOOG").execute()

            if goog_result.data:
                print("⚠️  GOOG company already exists!")
                print(f"   ID: {goog_result.data[0]['id']}")
                print("\n❓ Options:")
                print("   A) Keep both GOOGL and GOOG separate")
                print("   B) Merge GOOGL into GOOG (delete GOOGL)")
                print("   C) Update GOOGL name to GOOG (overwrites GOOG)")
                return

            # Step 3: Check how many topics are associated with GOOGL
            print("\n3️⃣ Checking topics for GOOGL...")
            topics_result = db_manager.supabase.table("topics").select("id, name").eq("company_id", company_id).execute()

            topic_count = len(topics_result.data) if topics_result.data else 0
            print(f"   Found {topic_count} topics associated with GOOGL")

            if topic_count > 0:
                print(f"\n   Sample topics:")
                for i, topic in enumerate(topics_result.data[:5], 1):
                    print(f"   {i}. {topic['name']}")

            # Step 4: Update company name from GOOGL to GOOG
            print(f"\n4️⃣ Updating company name from GOOGL to GOOG...")

            update_result = db_manager.supabase.table("companies").update({
                "name": "GOOG"
            }).eq("id", company_id).execute()

            if update_result.data:
                print(f"✅ Successfully updated company ticker!")
                print(f"   Company ID {company_id} is now named 'GOOG'")

                # Verify the update
                print(f"\n5️⃣ Verifying update...")
                verify_result = db_manager.supabase.table("companies").select("*").eq("name", "GOOG").execute()

                if verify_result.data:
                    updated_company = verify_result.data[0]
                    print(f"✅ Verification successful!")
                    print(f"   ID: {updated_company['id']}")
                    print(f"   Name: {updated_company['name']}")
                    print(f"   Topics: {topic_count} topics now accessible with GOOG ticker")

                    print(f"\n🎉 SUCCESS!")
                    print(f"   You can now query Google topics using: GOOG")
                    print(f"   API endpoint: /api/topics-by-interests?tickers=GOOG")
                    print(f"   Chat query: 'Show me Google AI strategy'")
                else:
                    print(f"⚠️  Could not verify update")
            else:
                print(f"❌ Update failed")

        else:
            print("❌ No GOOGL company found in database")
            print("\n🔍 Searching for GOOG instead...")

            goog_result = db_manager.supabase.table("companies").select("*").eq("name", "GOOG").execute()

            if goog_result.data:
                print(f"✅ GOOG already exists!")
                print(f"   ID: {goog_result.data[0]['id']}")
                print(f"   No update needed - you can already use GOOG ticker")
            else:
                print(f"❌ Neither GOOGL nor GOOG found in database")
                print(f"   You may need to run deep research for Google first")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    update_google_ticker()
