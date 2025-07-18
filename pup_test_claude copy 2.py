import asyncio
import json
import websockets
from playwright.async_api import async_playwright
import time
from datetime import datetime

class ChromeDebugChatBot:
    def __init__(self, debug_port=9222):
        self.debug_port = debug_port
        self.page = None
        self.context = None
        self.browser = None
        self.start_time = time.time()
        self.operation_start = None

    def log(self, message, operation_name=None):
        """Log message with timestamp and elapsed time"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        total_elapsed = time.time() - self.start_time
        
        if operation_name and self.operation_start:
            operation_elapsed = time.time() - self.operation_start
            print(f"[{timestamp}] (+{total_elapsed:.2f}s) [{operation_name}: {operation_elapsed:.2f}s] {message}")
        elif operation_name:
            self.operation_start = time.time()
            print(f"[{timestamp}] (+{total_elapsed:.2f}s) [START {operation_name}] {message}")
        else:
            print(f"[{timestamp}] (+{total_elapsed:.2f}s) {message}")

    def start_operation(self, operation_name):
        """Start timing an operation"""
        self.operation_start = time.time()
        self.log(f"Starting {operation_name}", operation_name)

    def end_operation(self, operation_name, message=""):
        """End timing an operation"""
        if self.operation_start:
            elapsed = time.time() - self.operation_start
            self.log(f"Completed {operation_name} {message}", f"{operation_name}_END")
            self.operation_start = None
        else:
            self.log(f"Completed {operation_name} {message}")

    async def connect_to_existing_tab(self, tab_id=None):
        """Connect to existing Chrome instance via debug protocol"""
        self.start_operation("CONNECT")
        try:
            # Start Playwright
            self.log("Starting Playwright...")
            self.playwright = await async_playwright().start()
            
            # Connect to existing Chrome instance
            self.log(f"Connecting to Chrome debug port {self.debug_port}...")
            self.browser = await self.playwright.chromium.connect_over_cdp(
                f"http://localhost:{self.debug_port}"
            )
            
            # Get all contexts (browser tabs)
            self.log("Getting browser contexts...")
            contexts = self.browser.contexts
            
            if not contexts:
                raise Exception("No browser contexts found")
            
            # Use the first context or find specific one
            self.context = contexts[0]
            pages = self.context.pages
            
            if not pages:
                raise Exception("No pages found in context")
            
            # Find the chat page (Claude.ai in your case)
            self.log(f"Searching through {len(pages)} pages for Claude.ai...")
            chat_page = None
            for page in pages:
                url = page.url
                if "claude.ai" in url or "chat" in url:
                    chat_page = page
                    break
            
            if chat_page:
                self.page = chat_page
                self.log(f"Connected to chat page: {self.page.url}")
            else:
                # Use the first page if no chat page found
                self.page = pages[0]
                self.log(f"Using first available page: {self.page.url}")
            
            self.end_operation("CONNECT", "- Successfully connected")
            return True
            
        except Exception as e:
            self.log(f"Error connecting to Chrome: {e}")
            self.end_operation("CONNECT", "- Failed")
            return False

    async def get_existing_weather_info(self):
        """Check if there's already weather information on the page"""
        try:
            # Get all text content from the page
            page_text = await self.page.evaluate("document.body.innerText")
            
            # Look for weather-related paragraphs
            paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
            
            # Find the best weather-related paragraph
            best_response = None
            best_score = 0
            
            for paragraph in paragraphs:
                if len(paragraph) > 100:  # Substantial content
                    # Score based on weather-related content
                    score = 0
                    weather_terms = ['weather', 'temperature', 'cloudy', 'sunny', 'forecast', 
                                   'burien', '°F', '°C', 'high', 'low', 'today', 'currently',
                                   'pleasant', 'mild', 'comfortable']
                    
                    for term in weather_terms:
                        if term.lower() in paragraph.lower():
                            score += 1
                    
                    # Prefer longer, more complete responses
                    if len(paragraph) > 200:
                        score += 2
                    
                    # Bonus for specific weather patterns
                    if ('today' in paragraph.lower() and 
                        ('°F' in paragraph or '°C' in paragraph) and
                        ('high' in paragraph.lower() or 'low' in paragraph.lower())):
                        score += 3
                    
                    if score > best_score:
                        best_score = score
                        best_response = paragraph
            
            if best_response and best_score >= 5:  # Must have substantial weather content
                return best_response
                
            return None
            
        except Exception as e:
            print(f"Error checking existing weather info: {e}")
            return None

    async def send_message_and_get_response(self, question):
        """Send a message to the chat and wait for response"""
        self.start_operation("SEND_MESSAGE")
        try:
            if not self.page:
                raise Exception("Not connected to any page")
            
            # Wait for page to load
            self.log("Waiting for page to load...")
            await self.page.wait_for_load_state('networkidle')
            
            # Get initial message count to track new messages
            initial_messages = await self.page.query_selector_all('[data-testid="conversation-turn"], .message, .chat-message')
            initial_count = len(initial_messages)
            self.log(f"Initial message count: {initial_count}")
            
            # Common selectors for chat input fields (reordered by likelihood)
            input_selectors = [
                '[contenteditable="true"]',  # Most likely for Claude.ai
                'textarea[placeholder*="message"]',
                'textarea[placeholder*="Message"]',
                'textarea',
                'input[placeholder*="message"]',
                'textarea[data-testid*="message"]',
                'textarea[aria-label*="message"]',
                '.message-input textarea',
                'input[type="text"]'
            ]
            
            # Try to find the input field
            self.log("Searching for input field...")
            input_element = None
            for i, selector in enumerate(input_selectors):
                try:
                    self.log(f"Trying selector {i+1}/{len(input_selectors)}: {selector}")
                    input_element = await self.page.wait_for_selector(selector, timeout=500)  # Reduced timeout
                    if input_element:
                        self.log(f"Found input with selector: {selector}")
                        break
                except:
                    self.log(f"Selector failed: {selector}")
                    continue
            
            if not input_element:
                # Print page content for debugging
                self.log("Available elements:")
                elements = await self.page.query_selector_all('input, textarea, [contenteditable]')
                for i, elem in enumerate(elements[:5]):  # Show first 5 elements
                    tag = await elem.evaluate('el => el.tagName')
                    attrs = await elem.evaluate('el => ({placeholder: el.placeholder, type: el.type, class: el.className})')
                    self.log(f"  {i}: {tag} - {attrs}")
                
                raise Exception("Could not find message input field")
            
            # Clear and type the message
            self.log(f"Typing message: {question}")
            await input_element.fill(question)
            
            # Try to find and click send button
            self.log("Searching for send button...")
            send_selectors = [
                'button[aria-label*="send"]',
                'button[title*="send"]',
                'button[data-testid*="send"]',
                '.send-button',
                'button:has-text("Send")',
                'button[type="submit"]',
                'form button:last-child'
            ]
            
            send_button = None
            for i, selector in enumerate(send_selectors):
                try:
                    self.log(f"Trying send button selector {i+1}/{len(send_selectors)}: {selector}")
                    send_button = await self.page.wait_for_selector(selector, timeout=500)  # Reduced timeout
                    if send_button:
                        self.log(f"Found send button with selector: {selector}")
                        break
                except:
                    self.log(f"Send button selector failed: {selector}")
                    continue
            
            if send_button:
                await send_button.click()
                self.log("Clicked send button")
            else:
                # Try pressing Enter as fallback
                await input_element.press('Enter')
                self.log("Pressed Enter to send")
            
            # Wait for response
            self.end_operation("SEND_MESSAGE", "- Message sent successfully")
            self.start_operation("WAIT_RESPONSE")
            
            # Strategy 1: Wait for Claude's response to appear and stabilize
            try:
                self.log("Strategy 1: Waiting for Claude response to appear...")
                max_attempts = 30  # 30 seconds max wait
                attempt = 0
                
                while attempt < max_attempts:
                    await asyncio.sleep(2)  # Wait 2 seconds between checks
                    
                    # Look for Claude's response container - updated selectors for current Claude UI
                    response_selectors = [
                        'div[data-testid="conversation-turn"]:last-child div[class*="font-claude"]',
                        'div[data-testid="conversation-turn"]:last-child .prose',
                        'div[data-testid="conversation-turn"]:last-child p',
                        'div[data-testid="conversation-turn"]:last-child div:not([class*="user"])',
                        '[data-testid="conversation-turn"]:last-child',
                        '.font-claude-message:last-child',
                        'div:has(> p):last-of-type'
                    ]
                    
                    for selector in response_selectors:
                        try:
                            elements = await self.page.query_selector_all(selector)
                            if elements:
                                # Check the last few elements for a substantial response
                                for element in reversed(elements[-3:]):  # Check last 3 elements
                                    text = await element.inner_text()
                                    text = text.strip()
                                    
                                    # Check if this looks like a Claude response (skip thinking process and meta-commentary)
                                    if (text and 
                                        len(text) > 50 and  # Substantial content
                                        question.lower() not in text.lower() and  # Not echoing question
                                        not text.startswith('What is') and  # Not the question
                                        not text.startswith('Send') and
                                        not text.startswith('Type') and
                                        not text.startswith('Thinking') and  # Skip thinking process
                                        not text.startswith('The user has') and  # Skip meta commentary
                                        not text.startswith('The user keeps') and  # Skip meta commentary
                                        not 'thinking about' in text.lower() and  # Skip thinking process
                                        not 'user is asking' in text.lower() and  # Skip meta commentary
                                        not 'user has asked' in text.lower() and  # Skip meta commentary
                                        not 'user keeps asking' in text.lower() and  # Skip meta commentary
                                        not 'multiple times' in text.lower() and  # Skip repetition commentary
                                        not 'recent searches' in text.lower() and  # Skip search commentary
                                        not 'provided the current weather' in text.lower() and  # Skip meta commentary
                                        not 'same question' in text.lower() and  # Skip repetition commentary
                                        not "i've given them" in text.lower() and  # Skip meta commentary
                                        ('weather' in text.lower() or 
                                         'temperature' in text.lower() or 
                                         'cloudy' in text.lower() or 
                                         'sunny' in text.lower() or
                                         'forecast' in text.lower() or
                                         'burien' in text.lower() or
                                         '°F' in text or '°C' in text or
                                         len(text) > 100)):  # Weather responses are usually longer
                                        
                                        self.log(f"Found Claude response with selector '{selector}': {text[:100]}...")
                                        self.end_operation("WAIT_RESPONSE", "- Response found via Strategy 1")
                                        return text
                        except Exception as selector_error:
                            continue
                    
                    attempt += 1
                    if attempt % 5 == 0:
                        self.log(f"Still waiting... ({attempt * 2}s)", "WAIT_RESPONSE")
                
            except Exception as e:
                self.log(f"Strategy 1 failed: {e}")
            
            # Strategy 2: Wait for complete response and look for final weather summary
            try:
                print("Waiting for complete weather response...")
                
                # Wait longer for Claude to finish processing and provide final answer
                await asyncio.sleep(15)  # Give more time for complete response
                
                # Get all text content from the page
                page_text = await self.page.evaluate("document.body.innerText")
                
                # Look for the final weather summary paragraph
                paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
                
                # Find the most substantial weather-related paragraph (likely the final summary)
                best_response = None
                best_score = 0
                
                for paragraph in reversed(paragraphs):  # Start from most recent
                    if (len(paragraph) > 80 and  # Substantial content
                        question.lower() not in paragraph.lower() and  # Not our question
                        not paragraph.startswith('Thinking') and
                        not 'search results' in paragraph.lower() and
                        not 'getting search' in paragraph.lower() and
                        not 'let me try' in paragraph.lower()):
                        
                        # Score based on weather-related content
                        score = 0
                        weather_terms = ['weather', 'temperature', 'cloudy', 'sunny', 'forecast', 
                                       'burien', '°F', '°C', 'high', 'low', 'today', 'currently']
                        
                        for term in weather_terms:
                            if term.lower() in paragraph.lower():
                                score += 1
                        
                        # Prefer longer, more complete responses
                        if len(paragraph) > 200:
                            score += 2
                        
                        if score > best_score:
                            best_score = score
                            best_response = paragraph
                
                if best_response and best_score >= 3:  # Must have at least 3 weather-related terms
                    print(f"Found complete weather response (score: {best_score}): {best_response[:100]}...")
                    return best_response
                        
            except Exception as e:
                print(f"Strategy 2 failed: {e}")
            
            # Strategy 3: Manual polling with text analysis
            try:
                print("Using text analysis approach...")
                
                # Wait a bit for response to appear
                await asyncio.sleep(5)
                
                # Get all visible text from conversation area
                conversation_selectors = [
                    '[data-testid="conversation"]',
                    '.conversation',
                    'main',
                    '[role="main"]'
                ]
                
                conversation_text = ""
                for selector in conversation_selectors:
                    try:
                        conv_element = await self.page.query_selector(selector)
                        if conv_element:
                            conversation_text = await conv_element.inner_text()
                            break
                    except:
                        continue
                
                if not conversation_text:
                    # Fallback to full page text
                    conversation_text = await self.page.evaluate("document.body.innerText")
                
                # Split into lines and analyze
                lines = [line.strip() for line in conversation_text.split('\n') if line.strip()]
                
                # Find our question and get the response after it
                for i, line in enumerate(lines):
                    if question.lower() in line.lower():
                        # Look for substantial text after our question
                        for j in range(i + 1, min(i + 20, len(lines))):
                            potential_response = lines[j]
                            
                            # Check if this looks like a real response
                            if (len(potential_response) > 30 and  # Substantial length
                                not potential_response.startswith('Send') and
                                not potential_response.startswith('Type') and
                                not potential_response.startswith('Message') and
                                'today' in potential_response.lower() or 
                                'weather' in potential_response.lower() or
                                len(potential_response) > 100):  # Weather responses tend to be longer
                                
                                print(f"Found response via text analysis: {potential_response[:100]}...")
                                return potential_response
                
            except Exception as e:
                print(f"Strategy 3 failed: {e}")
            
            # Strategy 4: Simple wait and get last substantial content
            try:
                print("Using final fallback strategy...")
                await asyncio.sleep(10)  # Give more time
                
                # Get all paragraphs and divs that might contain responses
                content_elements = await self.page.query_selector_all('p, div[class*="message"], div[class*="response"], div[class*="text"]')
                
                # Look for the most recent substantial content
                for element in reversed(content_elements):
                    try:
                        text = await element.inner_text()
                        if (text.strip() and 
                            len(text.strip()) > 50 and
                            question.lower() not in text.lower() and
                            not text.strip().startswith('Send') and
                            not text.strip().startswith('Type')):
                            print(f"Found content in fallback: {text[:100]}...")
                            return text.strip()
                    except:
                        continue
                
            except Exception as e:
                print(f"Final strategy failed: {e}")
            
            print("No response detected with any strategy")
            return None
                
        except Exception as e:
            print(f"Error sending message: {e}")
            return None

    async def close(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

async def main():
    """Main function to demonstrate usage"""
    bot = ChromeDebugChatBot()
    
    try:
        bot.log("=== Starting Claude Chat Bot ===")
        
        # Connect to existing Chrome tab
        if await bot.connect_to_existing_tab():
            
            # Send a question and get response
            question = "What is the weather like today?"
            bot.log(f"Sending question: {question}")
            
            response = await bot.send_message_and_get_response(question)
            
            if response:
                bot.log(f"Response received: {response}")
            else:
                bot.log("Failed to get response")
                
        else:
            bot.log("Failed to connect to Chrome debug session")
            
    except Exception as e:
        bot.log(f"Error in main: {e}")
        
    finally:
        bot.log("Cleaning up resources...")
        await bot.close()
        bot.log("=== Claude Chat Bot Finished ===")

if __name__ == "__main__":
    # Make sure Chrome is running with debug enabled:
    # chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
    
    asyncio.run(main())
