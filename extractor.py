import logging
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import json
from typing import Dict, List, Optional, Tuple, Any
import html
from datetime import datetime
import time
from selenium.common.exceptions import TimeoutException, WebDriverException
from urllib.parse import urlparse
import os

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Keep INFO level for now

def clean_url(url: str) -> str:
    """Clean and validate the ChatGPT URL.
    
    Args:
        url (str): The raw URL
        
    Returns:
        str: Cleaned URL
        
    Raises:
        ValueError: If URL is invalid or not a ChatGPT share URL
    """
    # Remove any whitespace and normalize
    url = url.strip()
    
    # Check if it's a valid URL
    if not url:
        raise ValueError("URL cannot be empty")
    
    # Ensure URL uses HTTPS
    if not url.startswith('https://'):
        url = 'https://' + url.split('://')[-1]
    
    # Validate ChatGPT URL format
    valid_domains = [
        'chat.openai.com',
        'chatgpt.com'
    ]
    
    # Extract domain from URL
    domain_match = re.search(r'https?://([^/]+)', url)
    if not domain_match:
        raise ValueError("Invalid URL format")
    
    domain = domain_match.group(1)
    if domain not in valid_domains:
        raise ValueError(f"URL must be from one of: {', '.join(valid_domains)}")
    
    # Convert to proper share URL format
    if 'chat.openai.com' in url:
        if '/share/' in url:
            # Already a share URL
            pass
        elif '/c/' in url:
            # Convert to share URL
            url = url.replace('/c/', '/share/')
        else:
            # Add share path if missing
            url = url.rstrip('/') + '/share/'
    elif 'chatgpt.com' in url:
        # Keep chatgpt.com domain
        if '/share/' not in url:
            url = url.rstrip('/') + '/share/'
    
    # Basic cleaning and validation
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Ensure it's a chatgpt.com URL
    if "chatgpt.com/share/" not in url and "chat.openai.com/share/" not in url:
        # Allow chat.openai.com/g/ URLs as well
        if "chat.openai.com/g/" not in url:
             raise ValueError("URL must be a valid ChatGPT shared link (chatgpt.com/share/...) or a GPT link (chat.openai.com/g/...)")

    # Keep original domain for direct access
    logger.info(f"Processing cleaned URL: {url}")
    return url

def clean_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace and normalizing newlines.
    
    Args:
        text (str): Raw text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text).strip()
    # Preserve paragraphs by replacing multiple newlines with two, then single newlines appropriately
    text = re.sub(r'\n\s*\n', '\n\n', text) 
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines).strip()

def is_meaningful_text(text: str, is_code: bool = False) -> bool:
    """Check if text is meaningful and not UI elements.
    
    Args:
        text: Text to check
        is_code: Whether the text is a code block
        
    Returns:
        bool: True if text is meaningful
    """
    # Skip common UI text
    ui_patterns = [
        'log in', 'sign up', 'skip to content',
        'what can i help', 'search', 'loading',
        '^copy$', '^menu$', '^help$'  # Only match exact words
    ]
    
    text = text.lower().strip()
    
    # Skip if empty
    if not text:
        return False
        
    # Skip if contains UI patterns (unless it's code)
    if not is_code and any(re.search(rf'\b{pattern}\b', text) for pattern in ui_patterns):
        return False
        
    # Skip if too short (unless it's code)
    if not is_code and len(text.strip()) < 5:  # Lowered from 10
        return False
        
    # Skip if mostly special characters (unless it's code)
    if not is_code:
        alpha_ratio = sum(c.isalpha() or c.isspace() or c.isdigit() or c in '.,!?-_()[]{}' for c in text) / (len(text) or 1)
        if alpha_ratio < 0.1:  # Lowered from 0.2
            return False
        
    return True

def extract_chat_content(url: str) -> List[Dict[str, str]]:
    """
    Extracts structured conversation content (user/assistant turns) from a ChatGPT shared URL.
    
    Args:
        url (str): The ChatGPT shared URL.
        
    Returns:
        List[Dict[str, str]]: A list of message dictionaries, e.g., 
                                [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
    Raises:
        ValueError: If the URL is invalid or content cannot be extracted.
    """
    logger.info(f"Starting extraction for URL: {url}")
    driver = None
    try:
        cleaned_url = clean_url(url)
        driver = get_headless_driver()
        logger.info("Headless browser created.")
        
        driver.get(cleaned_url)
        logger.info(f"Navigated to URL: {cleaned_url}")

        # Wait for page elements to indicate loading is likely complete
        try:
            # Wait for common elements that signify content area
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='prose'], div[class*='markdown'], main, article"))
            )
            logger.info("Content indicators found. Waiting for potential dynamic loading...")
            time.sleep(5) # Extra wait for JS rendering
            
        except TimeoutException:
            logger.warning("Timeout waiting for initial content indicators. Page might be structured differently or failed to load fully.")
            # Check if we landed on an error page or simple text page
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "error" in body_text.lower() or len(body_text) < 100:
                 raise ValueError(f"Failed to load chat content. Page may be inaccessible or an error page. Body: {body_text[:200]}...")

        # Get page source and parse
        page_source = driver.page_source
        logger.debug(f"Page source length: {len(page_source)}")
        if not page_source or len(page_source) < 100:
             raise ValueError("Failed to retrieve meaningful page source.")
             
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Extract metadata
        metadata = extract_metadata(soup)
        logger.info(f"Extracted metadata: {metadata}")
        
        conversation_data = []
        processed_content_hashes = set() # Set to track content already processed
        
        # --- Add Metadata as System Message ---
        meta_content_parts = []
        if metadata.get('title'):
            meta_content_parts.append(f"Title: {metadata['title']}")
        if metadata.get('model'):
            meta_content_parts.append(f"Model Used: {metadata['model']}")
        if metadata.get('timestamp'):
             meta_content_parts.append(f"Conversation Time: {metadata['timestamp']}")
             
        if meta_content_parts:
            conversation_data.append({
                "role": "system",
                "content": "\n".join(meta_content_parts)
            })
            
        # --- Extract Conversation Turns ---
        # Refined selector attempt: Look for blocks likely representing direct turns.
        # Prioritize selectors that might indicate a single message group.
        possible_message_blocks = soup.select(
            'div.w-full.text-token-text-primary[class*="group"], div[class*="text-base"], div[class*="message"]' 
        )

        # Fallback if primary selectors fail
        if not possible_message_blocks:
             possible_message_blocks = soup.select('div[class*="prose"], div[class*="markdown"]')
             if not possible_message_blocks:
                 raise ValueError("Could not find any potential message blocks on the page.")
             logger.warning("Using fallback message block selectors (prose/markdown). Role detection might be inaccurate.")

        logger.info(f"Found {len(possible_message_blocks)} potential message blocks. Processing...")

        for block in possible_message_blocks:
            # Extract content first to check if it was already processed
            content = ""
            content_element = block.select_one('div[class*="prose"], div[class*="markdown"], .text-message') 
            if not content_element:
                 content_element = block 

            if content_element:
                texts = []
                for elem in content_element.find_all(string=True, recursive=True):
                    parent = elem.find_parent(['button', 'nav', 'aside', 'footer', 'header', 'script', 'style'])
                    if not parent:
                         text_piece = str(elem).strip()
                         if text_piece and text_piece.lower() not in ["copy code", "regenerate", "edit", "share", "like", "dislike"]:
                             texts.append(text_piece)
                if texts:
                    content = clean_text("\n".join(texts))
            
            # Skip if content is empty or already processed
            content_hash = hash(content) # Use hash for faster checking
            if not content or content_hash in processed_content_hashes:
                if content: # Log only if content exists but is duplicate
                     logger.debug(f"Skipping already processed content block: {content[:50]}...")
                continue # Move to the next block

            # If new content, mark as processed
            processed_content_hashes.add(content_hash)
            
            # Now determine role for the new content block
            role = "unknown"
            block_classes = block.get('class', [])
            if any("user" in c for c in block_classes):
                role = "user"
            elif any("agent" in c or "assistant" in c for c in block_classes):
                 role = "assistant"
            if role == "unknown":
                 if block.select_one('svg path[d*="M9.01"]'): # Needs verification
                     role = "assistant"
                 elif block.select_one('div[class*="human"]'): # Needs verification
                     role = "user"

            # Add to data if meaningful content found
            if is_meaningful_text(content):
                if role == "unknown":
                    role = "assistant" 
                    logger.warning(f"Could not determine role for a block, defaulting to '{role}'. Content starts: {content[:50]}...")
                
                conversation_data.append({"role": role, "content": content})
                logger.debug(f"Added message: Role={role}, Content Length={len(content)}")
            elif content: # Log skipped non-meaningful only if content exists
                 logger.debug(f"Skipping non-meaningful content block: {content[:50]}...")

        if len(conversation_data) <= 1: # Check if only system message or less was added
            raise ValueError("Failed to extract meaningful conversation turns from the page.")
            
        logger.info(f"Successfully extracted {len(conversation_data)} structured messages.")
        return conversation_data
        
    except ValueError as ve:
         logger.error(f"Validation Error during extraction: {str(ve)}")
         raise # Re-raise specific validation errors
    except Exception as e:
        logger.error(f"General extraction error: {str(e)}", exc_info=True)
        # Try to get more context if possible
        page_text_snippet = ""
        if driver:
            try:
                 page_text_snippet = driver.find_element(By.TAG_NAME, "body").text[:500]
            except:
                 pass # Ignore errors getting snippet
        raise ValueError(f"Error extracting chat content: {str(e)}. Page snippet: {page_text_snippet}...")
    
    finally:
        # Clean up browser
        if driver:
            try:
                driver.quit()
                logger.info("Closed browser")
            except Exception as e:
                logger.warning(f"Error closing browser: {str(e)}")

def get_headless_driver():
    """Create and configure a headless Chrome browser instance.
    
    Returns:
        webdriver.Chrome: Configured headless browser
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")  # Required for headless mode
    chrome_options.add_argument("--no-sandbox")  # Required for running as root
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--window-size=1920,1080")  # Set window size
    chrome_options.add_argument("--disable-notifications")  # Disable notifications
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-infobars")  # Disable infobars
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # Avoid detection
    chrome_options.add_argument('--lang=en-US')  # Set language
    
    # Add user agent
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    # Suppress log messages
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    try:
        # Try specifying the service to suppress console messages further
        service = Service(log_output=os.devnull) 
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except NameError:
        # Fallback if 'os' is not imported or service fails
        try:
             driver = webdriver.Chrome(options=chrome_options)
             return driver
        except Exception as e:
             logger.error(f"Failed to create Chrome driver: {str(e)}")
             raise
    except Exception as e:
        logger.error(f"Failed to create Chrome driver: {str(e)}")
        raise

def extract_metadata(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract metadata from the chat page.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        Dict[str, Any]: Metadata dictionary
    """
    metadata = {
        'title': None,
        'timestamp': None,
        'model': None
    }
    
    # Try to find title
    title_elem = soup.find('title')
    if title_elem:
        metadata['title'] = title_elem.get_text(strip=True)
    
    # Try to find timestamp (more specific selectors)
    time_elem = soup.select_one('time[datetime], span[class*="time"], div[class*="timestamp"]')
    if time_elem:
         # Prioritize datetime attribute if available
         dt_attr = time_elem.get('datetime')
         if dt_attr:
             try:
                 # Attempt to parse ISO format
                 metadata['timestamp'] = datetime.fromisoformat(dt_attr.replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S UTC")
             except ValueError:
                 metadata['timestamp'] = time_elem.get_text(strip=True) # Fallback to text
         else:
            metadata['timestamp'] = time_elem.get_text(strip=True)
    
    # If no timestamp found, use current time as fallback
    if not metadata['timestamp']:
        metadata['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S Local")
        logger.warning("Could not find timestamp on page, using current time as fallback.")
    
    # Try to find model info (more specific selectors)
    model_elem = soup.select_one('div[class*="model-name"], span[class*="model-info"], div:contains("Model:")')
    if model_elem:
        model_text = model_elem.get_text(strip=True)
        # Clean up potential prefixes like "Model: GPT-4"
        model_text = re.sub(r'^(Model|Using|Running):\s*', '', model_text, flags=re.IGNORECASE).strip()
        metadata['model'] = model_text
    else:
        # Check title for model info as fallback
        if metadata['title'] and any(m in metadata['title'] for m in ['GPT-3', 'GPT-4', 'Claude']):
            metadata['model'] = metadata['title'] # Use title if it likely contains model name
            logger.info("Using title as fallback for model information.")

    return metadata 