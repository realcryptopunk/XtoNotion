import os
import json
import logging
import re
import asyncio
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Flag to track if playwright has been initialized
playwright_initialized = False

class OpenAIHandler:
    def __init__(self, api_key=None):
        """Initialize the OpenAI handler with an API key."""
        self.api_key = api_key or OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)
        self.playwright = None
        self.browser = None
    
    async def init_playwright(self):
        """Initialize Playwright for browser automation."""
        global playwright_initialized
        if not playwright_initialized:
            try:
                # Import here to avoid early initialization
                from playwright.async_api import async_playwright
                
                logger.info("Initializing Playwright...")
                self.playwright = await async_playwright().start()
                
                # Use a more realistic browser configuration
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-site-isolation-trials',
                        '--disable-web-security',
                        '--disable-features=BlockInsecurePrivateNetworkRequests',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                    ]
                )
                playwright_initialized = True
                logger.info("Playwright initialized successfully")
            except ImportError:
                logger.error("Playwright not installed. Run 'pip install playwright' and 'playwright install'")
                return False
            except Exception as e:
                logger.error(f"Error initializing Playwright: {e}")
                return False
        return True
    
    async def extract_with_playwright(self, url):
        """Extract tweet content using Playwright browser automation."""
        logger.info("Running new version of extract_with_playwright with improved browser configuration")
        if not await self.init_playwright():
            return None
        
        try:
            # Use a more realistic browser configuration with mobile emulation
            # Mobile often has less restrictions than desktop views
            context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
                viewport={"width": 390, "height": 844},
                device_scale_factor=2.0,
                has_touch=True,
                locale="en-US",
                timezone_id="America/New_York",
                is_mobile=True,
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True
            )
            
            # Add random cookies and headers to appear more like a real browser
            await context.add_cookies([
                {"name": "seen_ui_prompt", "value": "true", "domain": ".twitter.com", "path": "/"},
                {"name": "seen_ui_prompt", "value": "true", "domain": ".x.com", "path": "/"},
                {"name": "auth_token", "value": "", "domain": ".twitter.com", "path": "/"},
                {"name": "ct0", "value": "", "domain": ".twitter.com", "path": "/"},
                {"name": "twid", "value": "", "domain": ".twitter.com", "path": "/"}
            ])
            
            # Set extra headers to appear more like a real browser
            await context.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0"
            })
            
            page = await context.new_page()
            
            # Set longer timeout for Twitter's slow loading
            page.set_default_timeout(60000)  # Increase timeout to 60 seconds
            
            logger.info(f"Navigating to Twitter URL: {url}")
            
            # Try multiple navigation strategies
            navigation_success = False
            for _ in range(3):  # Try up to 3 times
                try:
                    response = await page.goto(url, wait_until="networkidle", timeout=60000)
                    if response and response.ok:
                        navigation_success = True
                        break
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"Navigation attempt failed: {e}")
                    await asyncio.sleep(2)
            
            if not navigation_success:
                logger.warning("Failed to navigate to the page after multiple attempts")
                return None
            
            # Wait longer for dynamic content
            await asyncio.sleep(5)  # Increased from 4 to 5 seconds
            
            # Try to handle the login modal more aggressively
            try:
                # First try to handle the login dialog if present
                login_dialog_selectors = [
                    'div[role="dialog"]',
                    'div[data-testid="loginDialog"]',
                    'div[data-testid="modal"]',
                    'div[aria-modal="true"]'
                ]
                
                for selector in login_dialog_selectors:
                    if await page.locator(selector).count() > 0:
                        logger.info(f"Login dialog detected with selector: {selector}, attempting to dismiss")
                        
                        # Try multiple approaches to dismiss the dialog
                        try:
                            # Try to find and click the "✕" close button
                            close_button_selectors = [
                                'div[role="button"][aria-label="Close"]',
                                'div[aria-label="Close"]',
                                'div[data-testid="app-bar-close"]',
                                'div[role="button"] svg[aria-label="Close"]'
                            ]
                            
                            for close_selector in close_button_selectors:
                                close_button = page.locator(close_selector)
                                if await close_button.count() > 0:
                                    await close_button.click()
                                    await asyncio.sleep(1)
                                    break
                            
                            # If close button didn't work, try clicking outside
                            await page.mouse.click(10, 10)
                            await asyncio.sleep(1)
                            
                            # Try clicking at the tweet content area
                            await page.mouse.click(195, 400)
                            await asyncio.sleep(1)
                            
                            # Try pressing Escape key
                            await page.keyboard.press('Escape')
                            await asyncio.sleep(1)
                        except Exception as e:
                            logger.warning(f"Error dismissing dialog: {e}")
                
                # Scroll down to load more content
                await page.evaluate("window.scrollBy(0, 300)")
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Error handling login dialog: {e}")
            
            # Try different selectors that might match tweet content
            tweet_content = None
            author = None
            timestamp = None
            
            # Try different selectors for the tweet content
            for content_selector in [
                'article div[data-testid="tweetText"]',
                'article div[lang]',
                '[data-testid="tweetText"]',
                '.tweet-text',
                'div[data-block="true"]',
                # Mobile selectors
                'div[dir="auto"] > span',
                'div.r-yfoy6g',
                '[data-testid="tweet"] div[lang]',
                'div[data-testid="tweet"] span[data-text="true"]',
                'div[data-testid="tweet"] div[dir="auto"]',
                'div[data-testid="tweet"] span[class*="css-"]',
                'div[data-testid="tweet"] span[class*="r-"]'
            ]:
                try:
                    element = page.locator(content_selector)
                    if await element.count() > 0:
                        tweet_content = await element.inner_text()
                        logger.info(f"Found tweet content with selector: {content_selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {content_selector} failed: {e}")
                    continue
            
            # Try to get author info
            for author_selector in [
                '[data-testid="User-Name"] > div:nth-child(2) > div > div > a > div > span',
                'a[tabindex="-1"] span',
                'article div > div > div > div > div > div > div > div > div[dir="auto"] > span',
                # Mobile selectors
                'h2[role="heading"]',
                '[data-testid="User-Name"] span.r-18u37iz',
                '[data-testid="tweetAuthor"]',
                'div[data-testid="User-Name"] span[class*="css-"]',
                'div[data-testid="User-Name"] span[class*="r-"]',
                'div[data-testid="User-Name"] a[role="link"] span'
            ]:
                try:
                    element = page.locator(author_selector)
                    if await element.count() > 0:
                        author = await element.first.inner_text()
                        logger.info(f"Found author: {author}")
                        break
                except Exception:
                    continue
            
            # Try to get timestamp
            for time_selector in [
                'time',
                '[data-testid="User-Name"] time',
                'article a time',
                # Mobile selectors
                'div[data-testid="User-Name"] span.r-18u37iz',
                'span.r-1qd0xha time',
                'div[data-testid="User-Name"] time',
                'div[data-testid="User-Name"] span[class*="css-"] time',
                'div[data-testid="User-Name"] span[class*="r-"] time'
            ]:
                try:
                    element = page.locator(time_selector)
                    if await element.count() > 0:
                        timestamp_element = page.locator(time_selector).first
                        timestamp = await timestamp_element.get_attribute('datetime')
                        if not timestamp:
                            timestamp = await timestamp_element.inner_text()
                        logger.info(f"Found timestamp: {timestamp}")
                        break
                except Exception:
                    continue
            
            # Take a screenshot for debugging
            try:
                await page.screenshot(path="tweet_screenshot.png")
                logger.info("Saved screenshot to tweet_screenshot.png")
            except Exception as e:
                logger.error(f"Error saving screenshot: {e}")
            
            # Get HTML content for debugging
            html_content = await page.content()
            with open("tweet_page.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info("Saved page HTML to tweet_page.html")
            
            await context.close()
            
            if tweet_content:
                result = {
                    "content": tweet_content,
                    "author": author or "Unknown",
                    "timestamp": timestamp or "",
                    "images": [],
                    "stats": {},
                    "url": url
                }
                logger.info(f"Successfully extracted tweet content with Playwright: {tweet_content[:100]}...")
                return result
            
            logger.warning("Playwright couldn't extract tweet content")
            return None
            
        except Exception as e:
            logger.error(f"Error using Playwright to extract tweet: {e}")
            return None
    
    async def extract_tweet_content(self, tweet_url):
        """Extract tweet content from Twitter/X URL using multiple methods."""
        # Try with Playwright first (highest success rate)
        playwright_result = await self.extract_with_playwright(tweet_url)
        if playwright_result:
            return playwright_result
        
        # Fallback to previous methods if Playwright fails
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml'
            }
            
            # Try several Nitter instances as they can be unreliable
            # Each instance might have different blocking/rate limiting
            nitter_instances = [
                "nitter.net",
                "nitter.kavin.rocks",
                "nitter.unixfox.eu",
                "nitter.42l.fr",
                "nitter.pussthecat.org",
                "nitter.nixnet.services"
            ]
            
            tweet_id = None
            tweet_id_match = re.search(r'/status/(\d+)', tweet_url)
            if tweet_id_match:
                tweet_id = tweet_id_match.group(1)
                logger.info(f"Found tweet ID: {tweet_id}")
            
            # Try each Nitter instance
            for instance in nitter_instances:
                try:
                    nitter_url = f"https://{instance}/i/status/{tweet_id}" if tweet_id else tweet_url.replace("twitter.com", instance).replace("x.com", instance)
                    
                    logger.info(f"Attempting to extract content from: {nitter_url}")
                    response = requests.get(nitter_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # For Nitter, this is the selector for tweet content
                        tweet_content_element = soup.select_one('.tweet-content')
                        if tweet_content_element:
                            tweet_content = tweet_content_element.get_text().strip()
                            
                            # Get author information
                            author_element = soup.select_one('.fullname')
                            author = author_element.get_text().strip() if author_element else "Unknown"
                            
                            # Get timestamp
                            time_element = soup.select_one('.tweet-date a')
                            timestamp = time_element.get_text().strip() if time_element else ""
                            
                            # Get tweet images if any
                            images = []
                            image_elements = soup.select('.attachment .still-image')
                            for img in image_elements:
                                if img.get('src'):
                                    images.append(img['src'])
                            
                            # Get tweet stats
                            stats = {}
                            stat_elements = soup.select('.tweet-stats .icon-container')
                            for stat in stat_elements:
                                text = stat.get_text().strip()
                                if "reply" in text.lower():
                                    stats["replies"] = text.split()[0]
                                elif "retweet" in text.lower():
                                    stats["retweets"] = text.split()[0]
                                elif "like" in text.lower():
                                    stats["likes"] = text.split()[0]
                            
                            tweet_data = {
                                "content": tweet_content,
                                "author": author,
                                "timestamp": timestamp,
                                "images": images,
                                "stats": stats,
                                "url": tweet_url
                            }
                            
                            logger.info(f"Successfully extracted tweet content from {instance}: {tweet_content[:100]}...")
                            return tweet_data
                except Exception as e:
                    logger.warning(f"Failed to extract from {instance}: {e}")
                    continue
            
            # If Nitter instances all fail, try directly with Twitter/X
            logger.info(f"All Nitter instances failed, attempting direct Twitter/X extraction from: {tweet_url}")
            try:
                response = requests.get(tweet_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Try various selectors that might work for Twitter
                    for selector in ['article div[lang]', '[data-testid="tweetText"]', '.tweet-text']:
                        content_element = soup.select_one(selector)
                        if content_element:
                            return {
                                "content": content_element.get_text().strip(),
                                "author": "Unknown",
                                "timestamp": "",
                                "images": [],
                                "stats": {},
                                "url": tweet_url
                            }
            except Exception as e:
                logger.warning(f"Direct Twitter extraction failed: {e}")
            
            # If we got here, extraction failed
            logger.warning(f"Failed to extract tweet content from {tweet_url}")
            return {
                "content": "Could not extract tweet content. Twitter may have blocked the request.",
                "author": "Unknown",
                "timestamp": "",
                "images": [],
                "stats": {},
                "url": tweet_url
            }
            
        except Exception as e:
            logger.error(f"Error extracting tweet content: {e}")
            return {
                "content": f"Error extracting tweet content: {str(e)}",
                "author": "Unknown",
                "timestamp": "",
                "images": [],
                "stats": {},
                "url": tweet_url
            }
    
    async def analyze_tweet(self, tweet_url):
        """Analyze a tweet URL with OpenAI."""
        try:
            # First extract the tweet content
            tweet_data = await self.extract_tweet_content(tweet_url)
            
            # If extraction failed completely, try to get data from tweet ID
            if tweet_data["content"] == "Could not extract tweet content. Twitter may have blocked the request.":
                logger.warning("Using fallback method to get tweet info from tweet ID")
                
                # Extract the tweet ID from the URL
                tweet_id_match = re.search(r'/status/(\d+)', tweet_url)
                if tweet_id_match:
                    tweet_id = tweet_id_match.group(1)
                    
                    # Extract the username from the URL
                    username_match = re.search(r'(?:twitter|x)\.com/([^/]+)/', tweet_url)
                    username = username_match.group(1) if username_match else "Unknown"
                    
                    # Add this basic info to help the AI make better guesses
                    tweet_data["username"] = username
                    tweet_data["tweet_id"] = tweet_id
            
            # Format the tweet information for OpenAI
            tweet_prompt = f"""Tweet URL: {tweet_url}
Author: {tweet_data.get('author', 'Unknown')}
Timestamp: {tweet_data.get('timestamp', '')}
Content: {tweet_data.get('content', 'Not available')}
Images: {"Yes, " + str(len(tweet_data.get('images', []))) + " images" if tweet_data.get('images', []) else "No images"}
Stats: {json.dumps(tweet_data.get('stats', {})) if tweet_data.get('stats', {}) else "Not available"}
"""

            # Add any extra context if we couldn't extract the content
            if tweet_data.get("content") == "Could not extract tweet content. Twitter may have blocked the request.":
                tweet_prompt += f"""
Note: The tweet content could not be directly extracted.
Username: {tweet_data.get('username', 'Unknown')}
Tweet ID: {tweet_data.get('tweet_id', 'Unknown')}

Please make your best guess about the content based on the URL, username, and any other available information.
"""
            
            logger.info(f"Sending tweet data to OpenAI: {tweet_prompt[:200]}...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """You are a helpful assistant that analyzes Twitter/X posts.
Preferred categories to choose from are:
- VibeCoding Help (for programming, coding, development related content)
- Cool AI (for AI, machine learning, LLMs, models, etc.)
- Ecommerce (for online stores, marketplaces, shopping)
- Business Ideas (for startups, entrepreneurship, business opportunities)
- Cool Tool (for productivity tools, utilities, services)
- App Idea (for mobile apps, application concepts)
- Ios Development (for iOS specific development)

If you don't have enough information about the tweet, make educated guesses based on the username, tweet ID, and URL. 
For example, if the username suggests they're a tech person or company, it's likely technology-related content.

You may suggest a new category if none of these fit well."""},
                    {"role": "user", "content": f"""Analyze this tweet:

{tweet_prompt}

Provide the following in JSON format:
1. title: A catchy title for this tweet
2. category: The most relevant category from the preferred list (or suggest a new one if needed)
3. summary: A concise summary of the tweet content
4. key_points: List 3-5 bullet points that capture the main ideas of the tweet
5. action_items: 2-3 possible follow-up actions or next steps based on the tweet's content
6. personal_reflection: How this tweet's content could be applied to business or personal life (1-2 sentences)
7. importance: Rate the importance/significance from 1-10, where 10 is extremely important
8. emoji: A single emoji that best represents this tweet's content or purpose
9. confident: Boolean indicating if you're confident in your analysis (false if working with limited information)"""}
                ],
                response_format={"type": "json_object"}
            )
            result = response.choices[0].message.content
            # Parse JSON to ensure it's valid
            data = json.loads(result)
            
            # Add original tweet data for reference
            data["extracted_tweet"] = tweet_data
            
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing OpenAI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error with OpenAI API: {e}")
            return None
            
    async def close(self):
        """Close the Playwright browser if open."""
        global playwright_initialized
        if self.browser:
            try:
                await self.browser.close()
                logger.info("Closed Playwright browser")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
                
        if self.playwright:
            try:
                await self.playwright.stop()
                logger.info("Stopped Playwright")
                playwright_initialized = False
            except Exception as e:
                logger.error(f"Error stopping Playwright: {e}")
    
    async def extract_website_content(self, url):
        """Extract content from a general website."""
        if not await self.init_playwright():
            return None
        
        try:
            context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()
            
            # Set longer timeout
            page.set_default_timeout(30000)
            
            logger.info(f"Navigating to website URL: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            
            # Wait for content to load
            await asyncio.sleep(2)
            
            # Extract title
            title = await page.title()
            
            # Extract meta description
            description = ""
            desc_element = await page.query_selector('meta[name="description"]')
            if desc_element:
                description = await desc_element.get_attribute('content') or ""
            
            # Extract main content
            # We'll try several common content selectors
            content = ""
            for selector in [
                'main', 
                'article', 
                '#content', 
                '.content', 
                'body'
            ]:
                try:
                    if await page.locator(selector).count() > 0:
                        content_element = await page.locator(selector).first
                        content = await page.locator(selector).inner_text()
                        if content:
                            logger.info(f"Found content with selector: {selector}")
                            break
                except Exception:
                    continue
            
            # Take a screenshot for debugging
            try:
                await page.screenshot(path="website_screenshot.png")
                logger.info("Saved screenshot to website_screenshot.png")
            except Exception as e:
                logger.error(f"Error saving screenshot: {e}")
            
            # If we couldn't get content from selectors, get the full body text
            if not content:
                content = await page.inner_text('body')
                
            # Limit content size to avoid token limits
            if content and len(content) > 8000:
                content = content[:8000] + "... [content truncated]"
            
            await context.close()
            
            return {
                "title": title or "Unknown Title",
                "description": description,
                "content": content,
                "url": url
            }
            
        except Exception as e:
            logger.error(f"Error extracting website content: {e}")
            return {
                "title": "Unknown Title",
                "description": "",
                "content": f"Error extracting content: {str(e)}",
                "url": url
            }
    
    async def analyze_website(self, website_url):
        """Analyze a general website with OpenAI."""
        try:
            # First extract the website content
            website_data = await self.extract_website_content(website_url)
            
            # Format the website information for OpenAI
            website_prompt = f"""Website URL: {website_url}
Title: {website_data['title']}
Description: {website_data['description']}

Content Preview:
{website_data['content'][:4000]}
"""
            
            logger.info(f"Sending website data to OpenAI: {website_prompt[:200]}...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """You are a helpful assistant that analyzes websites and tools.
Preferred categories to choose from are:
- VibeCoding Help (for programming, coding, development related content)
- Cool AI (for AI, machine learning, LLMs, models, etc.)
- Ecommerce (for online stores, marketplaces, shopping)
- Business Ideas (for startups, entrepreneurship, business opportunities)
- Cool Tool (for productivity tools, utilities, services)
- App Idea (for mobile apps, application concepts)
- Ios Development (for iOS specific development)

You may suggest a new category if none of these fit well."""},
                    {"role": "user", "content": f"""Analyze this website:

{website_prompt}

Provide the following information in JSON format:
1. title: A clear, concise title for this website or tool
2. category: The most relevant category from the preferred list (or suggest a new one if needed)
3. type: Classify this as either "Tool", "Resource", "App", "Service", or "Other"
4. description: A detailed description of what this website or tool does and what problems it solves
5. use_cases: List 2-3 primary use cases for this website/tool
6. alternatives: If you know similar tools/websites, list 1-2 alternatives
7. author: The creator, company, or individual who made this tool/website (if identifiable, otherwise "Unknown")
8. emoji: A single emoji that best represents this website or tool's purpose/category"""}
                ],
                response_format={"type": "json_object"}
            )
            result = response.choices[0].message.content
            # Parse JSON to ensure it's valid
            data = json.loads(result)
            
            # Add original website data for reference
            data["extracted_content"] = {
                "title": website_data['title'],
                "description": website_data['description']
            }
            
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing OpenAI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error with OpenAI API: {e}")
            return None 