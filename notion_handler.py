import os
import logging
import datetime
from notion_client import Client

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
        
        logger.debug("Successfully loaded environment variables from .env file")
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")

# Load environment variables
load_env_file()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

class NotionHandler:
    def __init__(self, api_key=None, database_id=None):
        """Initialize the Notion handler with API key and database ID."""
        self.api_key = api_key or NOTION_API_KEY
        self.database_id = database_id or NOTION_DATABASE_ID
        self.client = Client(auth=self.api_key)
    
    async def create_tweet_entry(self, tweet_data, tweet_url):
        """Create a new entry in the Notion database for a tweet."""
        try:
            # Extract tweet content if available
            extracted_tweet = tweet_data.get("extracted_tweet", {})
            tweet_content = extracted_tweet.get("content", "Content not available")
            tweet_author = extracted_tweet.get("author", "Unknown")
            
            # Map the AI-generated category to one of our preferred categories
            mapped_category = self.map_to_preferred_category(tweet_data["category"])
            
            # Get emoji if available, default to a generic one if not
            emoji = tweet_data.get("emoji", "🐦")
            
            # Include emoji in the title for better visual categorization
            title_with_emoji = f"{emoji} {tweet_data['title']}"
            
            # Basic properties that all databases should have
            properties = {
                "Title": {
                    "title": [
                        {
                            "text": {
                                "content": title_with_emoji
                            }
                        }
                    ]
                },
                "URL": {
                    "url": tweet_url
                },
                "Category": {
                    "select": {
                        "name": mapped_category
                    }
                },
                "Summary": {
                    "rich_text": [
                        {
                            "text": {
                                "content": tweet_data["summary"]
                            }
                        }
                    ]
                },
                "Importance": {
                    "number": int(tweet_data["importance"])
                }
            }
            
            # Check if the database has the enhanced properties and add them if they exist
            try:
                db = self.client.databases.retrieve(self.database_id)
                
                # Add Key Points if the property exists
                if "Key Points" in db["properties"] and "key_points" in tweet_data:
                    # Format bullet points as a string
                    if isinstance(tweet_data["key_points"], list):
                        key_points_text = "\n• " + "\n• ".join(tweet_data["key_points"])
                    else:
                        key_points_text = str(tweet_data["key_points"])
                    
                    properties["Key Points"] = {
                        "rich_text": [
                            {
                                "text": {
                                    "content": key_points_text
                                }
                            }
                        ]
                    }
                
                # Add Action Items if the property exists
                if "Action Items" in db["properties"] and "action_items" in tweet_data:
                    # Format action items as a string
                    if isinstance(tweet_data["action_items"], list):
                        action_items_text = "\n• " + "\n• ".join(tweet_data["action_items"])
                    else:
                        action_items_text = str(tweet_data["action_items"])
                    
                    properties["Action Items"] = {
                        "rich_text": [
                            {
                                "text": {
                                    "content": action_items_text
                                }
                            }
                        ]
                    }
                
                # Add Personal Reflection if the property exists
                if "Personal Reflection" in db["properties"] and "personal_reflection" in tweet_data:
                    properties["Personal Reflection"] = {
                        "rich_text": [
                            {
                                "text": {
                                    "content": tweet_data["personal_reflection"]
                                }
                            }
                        ]
                    }
                
                # Add Emoji property if it exists
                if "Emoji" in db["properties"]:
                    emoji_type = db["properties"]["Emoji"]["type"]
                    if emoji_type == "rich_text":
                        properties["Emoji"] = {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": emoji
                                    }
                                }
                            ]
                        }
                    elif emoji_type == "select":
                        properties["Emoji"] = {
                            "select": {
                                "name": emoji
                            }
                        }
            except Exception as e:
                logger.error(f"Error adding enhanced properties: {e}")
                # Continue without the enhanced properties if there's an error
            
            # Create page blocks
            page_blocks = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Tweet Content"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Author: {tweet_author}"
                                },
                                "annotations": {
                                    "bold": True
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": tweet_content
                                }
                            }
                        ]
                    }
                }
            ]
            
            # Add Key Points section to page content if available
            if "key_points" in tweet_data:
                page_blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Key Points"
                                }
                            }
                        ]
                    }
                })
                
                # Add each key point as a bulleted list item
                if isinstance(tweet_data["key_points"], list):
                    for point in tweet_data["key_points"]:
                        page_blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": point
                                        }
                                    }
                                ]
                            }
                        })
                else:
                    # If not a list, add as paragraph
                    page_blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": str(tweet_data["key_points"])
                                    }
                                }
                            ]
                        }
                    })
            
            # Add Action Items section if available
            if "action_items" in tweet_data:
                page_blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Action Items"
                                }
                            }
                        ]
                    }
                })
                
                # Add each action item as a bulleted list item
                if isinstance(tweet_data["action_items"], list):
                    for item in tweet_data["action_items"]:
                        page_blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": item
                                        }
                                    }
                                ]
                            }
                        })
                else:
                    # If not a list, add as paragraph
                    page_blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": str(tweet_data["action_items"])
                                    }
                                }
                            ]
                        }
                    })
            
            # Add Personal Reflection section if available
            if "personal_reflection" in tweet_data:
                page_blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Personal Reflection"
                                }
                            }
                        ]
                    }
                })
                
                page_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": tweet_data["personal_reflection"]
                                }
                            }
                        ]
                    }
                })
            
            # Add the Original URL block
            page_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Original URL: "
                            },
                            "annotations": {
                                "bold": True
                            }
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": tweet_url,
                                "link": {
                                    "url": tweet_url
                                }
                            }
                        }
                    ]
                }
            })
            
            # Create the page with properties and content
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=page_blocks
            )
            
            logger.info(f"Successfully created Notion entry: {response['url']}")
            return response
        except Exception as e:
            logger.error(f"Error creating Notion entry: {e}")
            return None
    
    async def check_database_structure(self):
        """Check if the Notion database has the required structure."""
        try:
            db = self.client.databases.retrieve(self.database_id)
            required_properties = ["Title", "URL", "Category", "Summary", "Importance"]
            recommended_properties = ["Key Points", "Action Items", "Personal Reflection", "Author", "Emoji"]
            missing_properties = []
            missing_recommended = []
            
            for prop in required_properties:
                if prop not in db["properties"]:
                    missing_properties.append(prop)
            
            for prop in recommended_properties:
                if prop not in db["properties"]:
                    missing_recommended.append(prop)
            
            # Check property types
            if not missing_properties:
                property_checks = [
                    # Title should be a title property
                    ("Title", "title"),
                    # URL should be a URL property
                    ("URL", "url"),
                    # Category should be a select property
                    ("Category", "select"),
                    # Summary should be a rich_text property
                    ("Summary", "rich_text"),
                    # Importance should be a number property
                    ("Importance", "number")
                ]
                
                if "Key Points" in db["properties"]:
                    property_checks.append(("Key Points", "rich_text"))
                if "Action Items" in db["properties"]:
                    property_checks.append(("Action Items", "rich_text"))
                if "Personal Reflection" in db["properties"]:
                    property_checks.append(("Personal Reflection", "rich_text"))
                
                # For Author, we accept multiple types
                if "Author" in db["properties"]:
                    author_type = db["properties"]["Author"]["type"]
                    if author_type not in ["rich_text", "people", "select"]:
                        logger.warning(f"Author property is of type '{author_type}', which may not be fully supported. Recommended: 'rich_text', 'people', or 'select'")
                
                # For Emoji, we accept multiple types
                if "Emoji" in db["properties"]:
                    emoji_type = db["properties"]["Emoji"]["type"]
                    if emoji_type not in ["rich_text", "select"]:
                        logger.warning(f"Emoji property is of type '{emoji_type}', which may not be fully supported. Recommended: 'rich_text' or 'select'")
                
                type_issues = []
                for prop_name, expected_type in property_checks:
                    actual_type = db["properties"][prop_name]["type"]
                    if actual_type != expected_type:
                        type_issues.append(f"{prop_name} should be type '{expected_type}' but is '{actual_type}'")
                
                if type_issues:
                    logger.warning(f"Property type issues in Notion database: {', '.join(type_issues)}")
                    return False, type_issues
            
            if missing_properties:
                logger.warning(f"Missing required properties in Notion database: {', '.join(missing_properties)}")
                return False, missing_properties
            
            if missing_recommended:
                logger.info(f"Missing recommended properties in Notion database: {', '.join(missing_recommended)}")
                # We don't return False for missing recommended properties
            
            logger.info("Notion database structure validated successfully")
            return True, []
        except Exception as e:
            logger.error(f"Error checking Notion database: {e}")
            return False, [f"Could not access database: {str(e)}"]
    
    def get_database_url(self):
        """Get the URL of the Notion database."""
        return f"https://notion.so/{self.database_id.replace('-', '')}"
    
    def get_current_date(self):
        """Get the current date in ISO format for Notion."""
        return datetime.datetime.now().date().isoformat()
    
    async def create_website_entry(self, website_data, page_url=None):
        """Create a new website entry in Notion."""
        try:
            # Map the AI-generated category to one of our preferred categories
            mapped_category = self.map_to_preferred_category(website_data.get("category", "Other"))
            
            # Get the author from the website data
            author = website_data.get("author", "Unknown")
            
            # Get emoji if available, default to a generic one if not
            emoji = website_data.get("emoji", "🔗")
            
            # Include emoji in the title for better visual categorization
            title_with_emoji = f"{emoji} {website_data.get('title', 'Unknown Website')}"
            
            # Basic properties without author (we'll add author separately based on type)
            properties = {
                "Title": {"title": [{"text": {"content": title_with_emoji}}]},
                "URL": {"url": page_url or ""},
                "Category": {"select": {"name": mapped_category}},
                # Use the Importance property with a default value of 5
                "Importance": {"number": 5},
                # Add a summary of the description
                "Summary": {
                    "rich_text": [
                        {
                            "text": {
                                "content": website_data.get("description", "")[:2000] if website_data.get("description") else ""
                            }
                        }
                    ]
                }
            }
            
            # Check the database to determine the type of Author property
            try:
                db = self.client.databases.retrieve(self.database_id)
                
                # Add Author property only if it exists in the database
                if "Author" in db["properties"]:
                    author_type = db["properties"]["Author"]["type"]
                    
                    # Format Author property based on its type
                    if author_type == "people":
                        # For people type, we skip it as we don't have user IDs
                        # This will prevent errors when creating the entry
                        pass
                    elif author_type == "rich_text":
                        # For rich_text type, add as text
                        properties["Author"] = {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": author
                                    }
                                }
                            ]
                        }
                    elif author_type == "select":
                        # For select type, use as option
                        properties["Author"] = {
                            "select": {
                                "name": author
                            }
                        }
                    else:
                        # For other types, don't include the property
                        logger.warning(f"Author property is type '{author_type}', which is not supported for automatic population")
                
                # Add Emoji property if it exists in the database
                if "Emoji" in db["properties"]:
                    emoji_type = db["properties"]["Emoji"]["type"]
                    if emoji_type == "rich_text":
                        properties["Emoji"] = {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": emoji
                                    }
                                }
                            ]
                        }
                    elif emoji_type == "select":
                        properties["Emoji"] = {
                            "select": {
                                "name": emoji
                            }
                        }
            except Exception as e:
                logger.warning(f"Error checking property types: {e}")
                # Continue without the properties if there's an error
            
            # Add description as rich text
            description = website_data.get("description", "")
            use_cases = website_data.get("use_cases", [])
            alternatives = website_data.get("alternatives", [])
            website_type = website_data.get("type", "Resource")
            
            # Format use cases and alternatives for rich text
            use_cases_text = "\n".join([f"- {uc}" for uc in use_cases]) if isinstance(use_cases, list) else use_cases
            alternatives_text = "\n".join([f"- {alt}" for alt in alternatives]) if isinstance(alternatives, list) else alternatives
            
            # Combine all information
            combined_text = f"{description}\n\n**Type:** {website_type}\n\n**Use Cases:**\n{use_cases_text}\n\n**Alternatives:**\n{alternatives_text}"
            
            # Create page blocks
            page_blocks = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Website Details"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": combined_text
                                }
                            }
                        ]
                    }
                }
            ]
            
            # Add Author as a block in the content instead
            page_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Created by: "
                            },
                            "annotations": {
                                "bold": True
                            }
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": author
                            }
                        }
                    ]
                }
            })
            
            # Add URL block
            page_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Original URL: "
                            },
                            "annotations": {
                                "bold": True
                            }
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": page_url or "",
                                "link": {
                                    "url": page_url or ""
                                }
                            }
                        }
                    ]
                }
            })
            
            # Create page with properties and content
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=page_blocks
            )
            
            # Return created page ID
            return response.id
            
        except Exception as e:
            logger.error(f"Error creating website entry: {e}")
            return None
    
    async def url_exists_in_database(self, url):
        """Check if a URL already exists in the database."""
        try:
            # Query the database for the URL
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "URL",
                    "url": {
                        "equals": url
                    }
                },
                page_size=1  # We only need to check if at least one exists
            )
            
            # If there are results, the URL exists
            return len(response["results"]) > 0
        except Exception as e:
            logger.error(f"Error checking if URL exists: {e}")
            return False  # Assume it doesn't exist if there's an error 
    
    def map_to_preferred_category(self, ai_category):
        """Map AI-generated categories to preferred categories or keep if it's a good fit."""
        # Define preferred categories
        preferred_categories = [
            "VibeCoding Help",
            "Cool AI",
            "Ecommerce", 
            "Business Ideas",
            "Cool Tool",
            "App Idea", 
            "Ios Development"
        ]
        
        # Keywords to match for each category
        category_keywords = {
            "VibeCoding Help": ["coding", "programming", "developer", "software", "web development", "html", "css", "javascript", "python", "java"],
            "Cool AI": ["ai", "artificial intelligence", "machine learning", "deep learning", "nlp", "gpt", "model", "neural", "llm"],
            "Ecommerce": ["ecommerce", "e-commerce", "shop", "shopping", "marketplace", "retail", "online store", "commerce"],
            "Business Ideas": ["business", "startup", "entrepreneur", "idea", "venture", "opportunity", "market"],
            "Cool Tool": ["tool", "utility", "productivity", "automation", "service", "platform"],
            "App Idea": ["app", "application", "mobile", "concept", "idea"],
            "Ios Development": ["ios", "swift", "apple", "iphone", "ipad", "xcode", "mobile development", "app development"]
        }
        
        # Normalize the AI category to lowercase for matching
        ai_category_lower = ai_category.lower()
        
        # Check for exact matches first
        for category in preferred_categories:
            if ai_category_lower == category.lower():
                return category
        
        # Check for keyword matches
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in ai_category_lower:
                    return category
        
        # If it's clearly a new useful category, keep the AI suggestion
        # Otherwise default to "Cool Tool" as a fallback
        return ai_category if len(ai_category) < 25 else "Cool Tool" 
    
    async def setup_enhanced_properties(self):
        """Add the enhanced properties to the Notion database if they don't exist."""
        try:
            # Check if the database exists
            db = self.client.databases.retrieve(self.database_id)
            
            # Define the enhanced properties to add
            properties_to_add = {
                "Key Points": {
                    "rich_text": {}
                },
                "Action Items": {
                    "rich_text": {}
                },
                "Personal Reflection": {
                    "rich_text": {}
                },
                "Emoji": {
                    "rich_text": {}
                }
            }
            
            # Check if Author property exists and what type it is before deciding to add it
            if "Author" not in db["properties"]:
                # See if there are existing people properties to determine best format for Author
                has_people_property = any(prop["type"] == "people" for prop in db["properties"].values())
                
                # If database already uses people properties, use that format for consistency
                if has_people_property:
                    properties_to_add["Author"] = {
                        "people": {}
                    }
                else:
                    # Otherwise use rich_text as default
                    properties_to_add["Author"] = {
                        "rich_text": {}
                    }
            
            # Check which properties need to be added
            properties_to_update = {}
            for prop_name, prop_config in properties_to_add.items():
                if prop_name not in db["properties"]:
                    properties_to_update[prop_name] = prop_config
            
            # If there are properties to add, update the database
            if properties_to_update:
                response = self.client.databases.update(
                    database_id=self.database_id,
                    properties=properties_to_update
                )
                
                added_properties = list(properties_to_update.keys())
                logger.info(f"Added enhanced properties to database: {', '.join(added_properties)}")
                return True, added_properties
            else:
                logger.info("All enhanced properties already exist in the database.")
                return True, []
        
        except Exception as e:
            logger.error(f"Error setting up enhanced properties: {e}")
            return False, [str(e)] 