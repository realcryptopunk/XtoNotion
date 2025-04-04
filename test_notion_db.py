#!/usr/bin/env python3
"""
Test script to check access to a Notion database.
"""
import os
import sys
import logging
from notion_client import Client

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables manually
def load_env_file():
    """Load environment variables from .env file manually."""
    try:
        with open(".env", "r") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Set it in the environment
                    os.environ[key] = value
        
        logger.info("Successfully loaded environment variables from .env file")
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")

# Format Notion ID with dashes if needed
def format_notion_id(id_str):
    """Format a Notion ID by inserting dashes in the correct positions."""
    # Remove any existing dashes and non-hex characters
    clean_id = ''.join(c for c in id_str if c.isalnum())
    
    # Insert dashes in the correct positions (8-4-4-4-12 format)
    formatted_id = f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    
    return formatted_id

# Load environment variables
load_env_file()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

def test_database_access():
    """Test access to the Notion database."""
    if not NOTION_API_KEY:
        logger.error("Missing NOTION_API_KEY in .env file")
        return False
    
    if not NOTION_DATABASE_ID:
        logger.error("Missing NOTION_DATABASE_ID in .env file")
        return False
    
    # Format database ID correctly
    formatted_db_id = format_notion_id(NOTION_DATABASE_ID)
    
    try:
        # Initialize Notion client
        notion = Client(auth=NOTION_API_KEY)
        
        print(f"\nTesting access to Notion database: {formatted_db_id}")
        print("------------------------------------------------")
        
        # Try to query the database
        print(f"Trying to access database...")
        response = notion.databases.retrieve(database_id=formatted_db_id)
        
        # Print database info
        print(f"✅ Successfully accessed database!")
        print(f"Database title: {response['title'][0]['plain_text'] if response['title'] else 'Untitled'}")
        
        # Print database properties
        print(f"\nDatabase properties:")
        for prop_name, prop_details in response["properties"].items():
            prop_type = prop_details["type"]
            print(f"  • {prop_name} ({prop_type})")
        
        return True
    except Exception as e:
        logger.error(f"Error accessing Notion database: {e}")
        print(f"\n❌ Failed to access Notion database: {formatted_db_id}")
        print(f"Error message: {str(e)}")
        print("\nPossible solutions:")
        print("  1. Verify your database ID is correct")
        print("  2. Make sure the database is shared with your integration")
        print("  3. If you haven't created the database yet, run setup_notion_db.py")
        print("\nTrying to search for databases you have access to...")
        
        try:
            # List all the available pages
            search_results = notion.search(filter={"property": "object", "value": "database"})
            if search_results["results"]:
                print("\nFound these databases accessible to your integration:")
                for idx, db in enumerate(search_results["results"], 1):
                    db_id = db["id"]
                    db_title = db["title"][0]["plain_text"] if db["title"] else "Untitled"
                    print(f"  {idx}. {db_title} (ID: {db_id})")
                
                print("\nYou can use one of these database IDs in your .env file.")
            else:
                print("\nNo databases found. Create a database with setup_notion_db.py")
        except Exception as search_error:
            logger.error(f"Error searching Notion: {search_error}")
            print("Could not search for databases.")
        
        return False

if __name__ == "__main__":
    test_database_access() 