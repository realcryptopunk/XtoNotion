#!/usr/bin/env python3
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

# Load environment variables
load_env_file()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")

def test_notion_connection():
    """Test basic connectivity to the Notion API."""
    if not NOTION_API_KEY:
        logger.error("Missing NOTION_API_KEY in .env file")
        sys.exit(1)
    
    try:
        # Initialize Notion client
        notion = Client(auth=NOTION_API_KEY)
        
        # Try listing users
        response = notion.users.list()
        
        # Print user info
        print("\nNotion Connection Test:")
        print("------------------------")
        
        if response["results"]:
            print(f"✅ Successfully connected to Notion API")
            print(f"  Bot User: {response['results'][0]['name']}")
            print(f"  Bot ID: {response['results'][0]['id']}")
            print(f"  Bot Type: {response['results'][0]['type']}")
        else:
            print("⚠️ Connected to Notion API but got an empty response")
        
        # List workspaces
        print("\nAvailable Workspaces:")
        if "bot" in response["results"][0] and "workspace_name" in response["results"][0]["bot"]:
            print(f"  • {response['results'][0]['bot']['workspace_name']}")
        else:
            print("  • No workspace information available")
        
        print("\n🔑 Your Notion API key is valid. To fix the database creation issue:")
        print("  1. Verify the Notion page ID is correct")
        print("  2. Make sure you've shared the page with your integration")
        print("  3. Check that the integration has 'Full Access' capability")
        
        return True
    except Exception as e:
        logger.error(f"Error connecting to Notion API: {e}")
        print("\n❌ Failed to connect to Notion API.")
        print(f"Error message: {str(e)}")
        print("\nPlease check:")
        print("  1. Your Notion API key is correct")
        print("  2. Your internet connection is working")
        print("  3. The Notion API service is available")
        return False

if __name__ == "__main__":
    print("Testing Notion API connection...")
    success = test_notion_connection()
    sys.exit(0 if success else 1) 