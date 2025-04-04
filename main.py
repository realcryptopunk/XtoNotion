#!/usr/bin/env python3
import os
import re
import json
import logging
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import sys
import argparse

# Import custom handlers
from notion_handler import NotionHandler
from openai_handler import OpenAIHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
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
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# URL patterns
TWITTER_URL_PATTERN = r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[^/\s]+/status/\d+'
GENERAL_URL_PATTERN = r'https?://(?:www\.)?[\w.-]+\.[a-zA-Z]{2,}(?:/\S*)?'

# Initialize handlers
notion_handler = None
openai_handler = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    
    # Check if Notion database is properly configured
    valid, missing = await notion_handler.check_database_structure()
    
    welcome_message = f"Hi {user.mention_html()}! I'm your Web-to-Notion bot. Send me any URL, and I'll analyze it using AI and save it to your Notion database. I handle both Twitter/X links and general websites."
    
    if not valid:
        welcome_message += "\n\n⚠️ Warning: Your Notion database might not be properly configured. "
        if missing:
            welcome_message += f"Missing properties: {', '.join(missing)}"
    
    await update.message.reply_html(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Just send me any URL, and I'll process it for you!\n\n"
        "For Twitter/X links: I'll extract content, categorize, and provide:\n"
        "• Summary and key bullet points\n"
        "• Suggested action items and personal reflections\n"
        "• Category and importance rating\n\n"
        "For other websites: I'll categorize (Tool, Resource, etc.) and describe what it does.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/setup - Add enhanced properties to your Notion database\n\n"
        "Everything gets saved to your Notion database for future reference."
    )

async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set up the Notion database with enhanced properties."""
    await update.message.reply_text("Setting up enhanced properties in your Notion database...")
    
    success, added_properties = await notion_handler.setup_enhanced_properties()
    
    if success:
        if added_properties:
            await update.message.reply_text(
                f"✅ Successfully added the following properties to your Notion database:\n• {', '.join(added_properties)}\n\n"
                "These properties will be used for enhanced summaries and AI-generated insights."
            )
        else:
            await update.message.reply_text(
                "✅ Your Notion database already has all the enhanced properties set up!\n\n"
                "The bot will use these properties for enhanced summaries and AI-generated insights."
            )
    else:
        await update.message.reply_text(
            f"❌ Failed to set up enhanced properties: {added_properties[0] if added_properties else 'Unknown error'}\n\n"
            "Please check your Notion API key and database ID."
        )

async def process_message(update=None, context=None, text=None):
    """
    Process a message containing URLs.
    Can be called from Telegram handler or directly from command line.
    """
    # Create handlers if they weren't passed
    global notion_handler, openai_handler
    local_notion_handler = notion_handler or NotionHandler()
    local_openai_handler = openai_handler or OpenAIHandler()
    
    # Determine message text source
    if update and hasattr(update, 'message') and update.message:
        # Called from Telegram
        message_text = update.message.text
        processing_message = None
    else:
        # Called from command line or elsewhere
        message_text = text
        if not message_text:
            logger.error("No message text provided")
            return False
    
    try:
        # First, check for Twitter/X URLs
        twitter_urls = re.findall(TWITTER_URL_PATTERN, message_text)
        
        # Then, check for general website URLs (exclude anything that could be a Twitter URL)
        general_urls = []
        for url in re.findall(GENERAL_URL_PATTERN, message_text):
            # Check if this URL is related to Twitter/X
            if 'twitter.com' in url or 'x.com' in url:
                # Extract the base Twitter URL if this is a Twitter URL with parameters
                base_twitter_url = re.search(r'(https?://(?:www\.)?(?:twitter\.com|x\.com)/[^/\s]+/status/\d+)', url)
                if base_twitter_url and base_twitter_url.group(1) in twitter_urls:
                    # This is a Twitter URL we already have, so skip it
                    continue
            
            # Not a Twitter URL we've already found
            general_urls.append(url)
        
        if not twitter_urls and not general_urls:
            logger.info("No URLs found in message.")
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_text("No URL found in your message. Please send a valid URL.")
            return False
        
        # Let the user know we're processing if in Telegram
        if update and hasattr(update, 'message') and update.message:
            urls_to_process = twitter_urls + general_urls
            first_url = urls_to_process[0] if urls_to_process else "URL"
            processing_message = await update.message.reply_text(f"Processing URL: {first_url} ⏳")
        
        results = []
        
        # Process Twitter/X URLs
        for url in twitter_urls:
            logger.info(f"Processing Twitter URL: {url}")
            result = await process_twitter_url(url, local_notion_handler, local_openai_handler, update, processing_message)
            if result:
                results.append(result)
        
        # Process general website URLs
        for url in general_urls:
            logger.info(f"Processing general website URL: {url}")
            result = await process_website_url(url, local_notion_handler, local_openai_handler, update, processing_message)
            if result:
                results.append(result)
        
        return True
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text(f"Sorry, an error occurred while processing your request: {str(e)}")
        return False
    finally:
        # Ensure cleanup happens if we created new handlers
        if local_openai_handler != openai_handler:
            await local_openai_handler.close()

async def process_twitter_url(url, notion_handler, openai_handler, update=None, processing_message=None):
    """Process a Twitter/X URL."""
    try:
        # First check if the URL already exists in the database
        if await notion_handler.url_exists_in_database(url):
            logger.info(f"Tweet URL already exists in database: {url}")
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_text(f"This tweet is already saved in your Notion database: {url}")
            return None
        
        # Get tweet data using OpenAI
        tweet_data = await openai_handler.analyze_tweet(url)
        
        if not tweet_data:
            logger.warning(f"Failed to analyze tweet: {url}")
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_text("Sorry, I couldn't analyze that tweet. Please try again later.")
            return None
        
        # Update processing message if in Telegram
        if processing_message:
            try:
                await processing_message.edit_text(f"Analyzed tweet! Now saving to Notion... ⏳")
            except Exception as e:
                logger.error(f"Error updating processing message: {e}")
        
        # Map category before creating entry
        mapped_category = notion_handler.map_to_preferred_category(tweet_data["category"])
        
        # Get emoji for the tweet
        emoji = tweet_data.get("emoji", "🐦")
        
        # Create Notion entry
        entry_id = await notion_handler.create_tweet_entry(tweet_data, url)
        
        if entry_id:
            logger.info(f"Successfully created Notion entry for tweet: {url}")
            
            # If in Telegram, send a nicely formatted response
            if update and hasattr(update, 'message') and update.message:
                # Extract tweet data for the message
                extracted_tweet = tweet_data.get("extracted_tweet", {})
                tweet_author = extracted_tweet.get("author", "Unknown")
                tweet_content = extracted_tweet.get("content", "Content not available")
                tweet_stats = extracted_tweet.get("stats", {})
                
                stats_text = ""
                if tweet_stats:
                    stats_parts = []
                    if "replies" in tweet_stats:
                        stats_parts.append(f"💬 {tweet_stats['replies']} replies")
                    if "retweets" in tweet_stats:
                        stats_parts.append(f"🔄 {tweet_stats['retweets']} retweets")
                    if "likes" in tweet_stats:
                        stats_parts.append(f"❤️ {tweet_stats['likes']} likes")
                    
                    if stats_parts:
                        stats_text = "\n" + " • ".join(stats_parts)
                
                # Format key points as bullet points if available
                key_points_text = ""
                if "key_points" in tweet_data and tweet_data["key_points"]:
                    key_points_text = "\n\n📋 <b>Key Points:</b>"
                    if isinstance(tweet_data["key_points"], list):
                        for point in tweet_data["key_points"]:
                            key_points_text += f"\n• {point}"
                    else:
                        key_points_text += f"\n{tweet_data['key_points']}"
                
                # Format action items if available
                action_items_text = ""
                if "action_items" in tweet_data and tweet_data["action_items"]:
                    action_items_text = "\n\n🎯 <b>Action Items:</b>"
                    if isinstance(tweet_data["action_items"], list):
                        for item in tweet_data["action_items"]:
                            action_items_text += f"\n• {item}"
                    else:
                        action_items_text += f"\n{tweet_data['action_items']}"
                
                # Add personal reflection if available
                personal_reflection_text = ""
                if "personal_reflection" in tweet_data and tweet_data["personal_reflection"]:
                    personal_reflection_text = f"\n\n💭 <b>Personal Reflection:</b>\n{tweet_data['personal_reflection']}"
                
                # Build the complete message
                message = (
                    f"✅ Tweet successfully analyzed and saved to Notion!\n\n"
                    f"{emoji} <b>{tweet_data['title']}</b>\n\n"
                )
                
                # Add a note if the analysis was based on limited information
                if tweet_data.get("confident") is False:
                    message += f"⚠️ <i>Note: Analysis based on limited information as tweet content couldn't be fully extracted</i>\n\n"
                
                message += (
                    f"👤 <b>Author:</b> {tweet_author}\n"
                    f"🏷️ <b>Category:</b> {mapped_category}\n"
                    f"📊 <b>Importance:</b> {tweet_data['importance']}/10{stats_text}\n\n"
                    f"<b>Tweet Content:</b>\n{tweet_content[:300]}{'...' if len(tweet_content) > 300 else ''}\n\n"
                    f"📝 <b>Summary:</b> {tweet_data['summary']}"
                    f"{key_points_text}"
                    f"{action_items_text}"
                    f"{personal_reflection_text}\n\n"
                    f"🔗 <a href='{notion_handler.get_database_url()}'>View in Notion</a>"
                )
                
                # Send the message with HTML formatting
                await update.message.reply_html(message)
            
            return entry_id
        else:
            logger.warning(f"Failed to create Notion entry for tweet: {url}")
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_text("Sorry, I couldn't save to Notion. Please check your API keys and database ID.")
            return None
    
    except Exception as e:
        logger.error(f"Error processing Twitter URL {url}: {e}")
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text(f"Error processing tweet: {str(e)}")
        return None

async def process_website_url(url, notion_handler, openai_handler, update=None, processing_message=None):
    """Process a general website URL."""
    try:
        # First check if the URL already exists in the database
        if await notion_handler.url_exists_in_database(url):
            logger.info(f"Website URL already exists in database: {url}")
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_text(f"This website is already saved in your Notion database: {url}")
            return None
        
        # Get website data using OpenAI
        website_data = await openai_handler.analyze_website(url)
        
        if not website_data:
            logger.warning(f"Failed to analyze website: {url}")
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_text("Sorry, I couldn't analyze that website. Please try again later.")
            return None
        
        # Update processing message if in Telegram
        if processing_message:
            try:
                await processing_message.edit_text(f"Analyzed website! Now saving to Notion... ⏳")
            except Exception as e:
                logger.error(f"Error updating processing message: {e}")
        
        # Map category before creating entry
        mapped_category = notion_handler.map_to_preferred_category(website_data.get("category", "Other"))
        
        # Get emoji for the website
        emoji = website_data.get("emoji", "🔗")
        
        # Create Notion entry
        entry_id = await notion_handler.create_website_entry(website_data, url)
        
        if entry_id:
            logger.info(f"Successfully created Notion entry for website: {url}")
            
            # If in Telegram, send a nicely formatted response
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_html(
                    f"✅ Website successfully analyzed and saved to Notion!\n\n"
                    f"{emoji} <b>{website_data['title']}</b>\n\n"
                    f"🌐 <b>URL:</b> {url}\n"
                    f"👤 <b>Author:</b> {website_data.get('author', 'Unknown')}\n"
                    f"🏷️ <b>Category:</b> {mapped_category}\n"
                    f"🔧 <b>Type:</b> {website_data['type']}\n\n"
                    f"📋 <b>Description:</b> {website_data['description'][:300]}{'...' if len(website_data['description']) > 300 else ''}\n\n"
                    f"🔗 <a href='{notion_handler.get_database_url()}'>View in Notion</a>"
                )
            
            return entry_id
        else:
            logger.warning(f"Failed to create Notion entry for website: {url}")
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_text("Sorry, I couldn't save to Notion. Please check your API keys and database ID.")
            return None
    
    except Exception as e:
        logger.error(f"Error processing website URL {url}: {e}")
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text(f"Error processing website: {str(e)}")
        return None

async def main_cli():
    """Command-line interface main function."""
    parser = argparse.ArgumentParser(description="Process URLs from X/Twitter or websites and add them to Notion.")
    parser.add_argument("--message", type=str, help="Message containing URLs")
    parser.add_argument("--file", type=str, help="File containing URLs, one per line")
    parser.add_argument("--bot", action="store_true", help="Run as a Telegram bot")
    
    args = parser.parse_args()
    
    if args.bot:
        await run_telegram_bot()
    elif args.message:
        await process_message(text=args.message)
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                urls = f.readlines()
            
            for url in urls:
                await process_message(text=url.strip())
        except Exception as e:
            logger.error(f"Error processing file: {e}")
    else:
        logger.error("Either --message, --file, or --bot must be provided.")
        parser.print_help()

async def run_telegram_bot():
    """Start the Telegram bot."""
    global notion_handler, openai_handler
    
    # Initialize handlers
    notion_handler = NotionHandler()
    openai_handler = OpenAIHandler()
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setup", setup_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    try:
        # Initialize the application first
        await application.initialize()
        await application.start()
        # Start polling for updates
        await application.updater.start_polling()
        
        # Keep the bot running until stopped
        logger.info("Bot is running. Press Ctrl+C to stop.")
        # Wait for bot to run until user interrupts
        running = True
        while running:
            try:
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                running = False
                logger.info("Keyboard interrupt received, shutting down...")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in bot execution: {e}")
    finally:
        # Cleanup resources properly within the same event loop
        logger.info("Cleaning up resources...")
        try:
            await application.stop()
            await application.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down application: {e}")
        
        # Close OpenAI handler
        if openai_handler:
            await openai_handler.close()
        
        logger.info("Cleanup complete.")

if __name__ == "__main__":
    # Check for required environment variables
    required_vars = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "NOTION_API_KEY": os.getenv("NOTION_API_KEY"),
        "NOTION_DATABASE_ID": NOTION_DATABASE_ID
    }
    
    # Add TELEGRAM_BOT_TOKEN to required vars only if --bot argument is present
    if "--bot" in sys.argv:
        required_vars["TELEGRAM_BOT_TOKEN"] = TELEGRAM_BOT_TOKEN
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}. Please check your .env file.")
    else:
        asyncio.run(main_cli()) 