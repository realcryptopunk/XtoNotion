#!/usr/bin/env python3
"""
Utility to format a Notion ID correctly with dashes.
"""

def format_notion_id(id_str):
    """Format a Notion ID by inserting dashes in the correct positions."""
    # Remove any existing dashes and non-hex characters
    clean_id = ''.join(c for c in id_str if c.isalnum())
    
    # Check if we have the right length (32 characters)
    if len(clean_id) != 32:
        print(f"⚠️ Warning: Expected 32 characters, but got {len(clean_id)}")
        print("This might not be a valid Notion ID.")
    
    # Insert dashes in the correct positions (8-4-4-4-12 format)
    formatted_id = f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    
    return formatted_id

if __name__ == "__main__":
    print("Notion ID Formatter")
    print("-------------------")
    print("This utility formats a Notion ID by inserting dashes in the correct positions (8-4-4-4-12 format).")
    print("Example: 1cab9534753980cc8de6f88c0a2c19f4 → 1cab9534-7539-80cc-8de6-f88c0a2c19f4\n")
    
    # Try to get the ID from the .env file first
    try:
        with open(".env", "r") as f:
            env_content = f.read()
            for line in env_content.split('\n'):
                if "NOTION_PARENT_PAGE_ID" in line and "=" in line:
                    _, value = line.split("=", 1)
                    original_id = value.strip()
                    print(f"Found ID in .env file: {original_id}")
                    break
            else:
                original_id = input("Enter your Notion page ID: ")
    except:
        original_id = input("Enter your Notion page ID: ")
    
    # Format the ID
    formatted_id = format_notion_id(original_id)
    
    print(f"\nOriginal ID: {original_id}")
    print(f"Formatted ID: {formatted_id}")
    
    # Ask if user wants to update .env file
    update_env = input("\nUpdate NOTION_PARENT_PAGE_ID in .env file? (y/n): ").lower()
    if update_env == 'y':
        try:
            with open(".env", "r") as f:
                env_content = f.read()
            
            # Replace the ID
            updated_content = []
            for line in env_content.split('\n'):
                if "NOTION_PARENT_PAGE_ID" in line and "=" in line:
                    key, _ = line.split("=", 1)
                    updated_line = f"{key}={formatted_id}"
                    updated_content.append(updated_line)
                else:
                    updated_content.append(line)
            
            # Write the updated content
            with open(".env", "w") as f:
                f.write('\n'.join(updated_content))
            
            print("✅ Updated .env file with formatted ID.")
        except Exception as e:
            print(f"❌ Error updating .env file: {e}")
    
    print("\nRemember to share your Notion page with your integration!")
    print("1. Open your Notion page")
    print("2. Click 'Share' in the top right")
    print("3. Search for and select your integration")
    print("4. Make sure the integration has proper permissions") 