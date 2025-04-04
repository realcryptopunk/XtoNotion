#!/usr/bin/env python3
"""
Utility script to create a Notion database with the required structure for the X to Notion bot.
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
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Set it in the environment
                os.environ[key] = value
        
        logger.info("Successfully loaded environment variables from .env file")
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")

# Load environment variables
load_env_file()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID")  # ID of the page where you want to create the database

def create_notion_database():
    """Create a Notion database with the required structure for the X to Notion bot."""
    if not NOTION_API_KEY:
        logger.error("Missing NOTION_API_KEY in .env file")
        sys.exit(1)
    
    if not NOTION_PARENT_PAGE_ID:
        logger.error("Missing NOTION_PARENT_PAGE_ID in .env file. Add the ID of the page where you want to create the database.")
        sys.exit(1)
    
    try:
        # Initialize Notion client
        notion = Client(auth=NOTION_API_KEY)
        
        # Create the database
        response = notion.databases.create(
            parent={"type": "page_id", "page_id": NOTION_PARENT_PAGE_ID},
            title=[{"type": "text", "text": {"content": "Twitter/X Posts"}}],
            properties={
                "Title": {
                    "title": {}
                },
                "URL": {
                    "url": {}
                },
                "Category": {
                    "select": {
                        "options": [
                            {"name": "Technology", "color": "blue"},
                            {"name": "Politics", "color": "red"},
                            {"name": "Entertainment", "color": "purple"},
                            {"name": "Business", "color": "green"},
                            {"name": "Sports", "color": "orange"},
                            {"name": "Science", "color": "pink"},
                            {"name": "Health", "color": "yellow"},
                            {"name": "Other", "color": "gray"}
                        ]
                    }
                },
                "Summary": {
                    "rich_text": {}
                },
                "Importance": {
                    "number": {}
                },
                "Date Added": {
                    "created_time": {}
                }
            }
        )
        
        # Log success
        database_id = response["id"]
        database_url = f"https://notion.so/{database_id.replace('-', '')}"
        
        logger.info(f"Successfully created Notion database!")
        logger.info(f"Database ID: {database_id}")
        logger.info(f"Database URL: {database_url}")
        
        # Add to .env file if it exists
        env_file = ".env"
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                env_contents = f.read()
            
            if "NOTION_DATABASE_ID" not in env_contents:
                with open(env_file, "a") as f:
                    f.write(f"\nNOTION_DATABASE_ID={database_id}\n")
                logger.info(f"Added NOTION_DATABASE_ID to {env_file}")
            else:
                logger.warning(f"NOTION_DATABASE_ID already exists in {env_file}. Not updating.")
        
        print("\n======= SETUP COMPLETE =======")
        print(f"Your Notion database is ready at: {database_url}")
        print(f"Database ID: {database_id}")
        print("Add this ID to your .env file as NOTION_DATABASE_ID if it wasn't added automatically.")
        print("===============================\n")
        
        return database_id
    except Exception as e:
        logger.error(f"Error creating Notion database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Setting up Notion database for X to Notion bot...")
    database_id = create_notion_database()
    print(f"Setup complete! Use this database ID in your .env file: {database_id}")
    print("You can now run the bot with: python main.py") 