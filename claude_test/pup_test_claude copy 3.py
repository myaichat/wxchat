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
            
            # Strategy 1: Look for the complete response content
            try:
                self.log("Strategy 1: Looking for complete response content...")
                
                # Wait for response to complete
                await asyncio.sleep(10)
                
                # Get all page content
                page_content = await self.page.evaluate("document.body.innerText")
                
                # Find the question in the content to locate the response
                lines = [line.strip() for line in page_content.split('\n') if line.strip()]
                
                # Find where our question appears
                question_index = -1
                for i, line in enumerate(lines):
                    if question.lower() in line.lower() and len(line) > len(question) * 0.7:
                        question_index = i
                        self.log(f"Found question at line {i}: {line}")
                        break
                
                if question_index >= 0:
                    # Collect all response content after the question, but skip reasoning
                    response_lines = []
                    collecting = False
                    skip_reasoning = True
                    
                    for i in range(question_index + 1, len(lines)):
                        line = lines[i].strip()
                        
                        # Skip empty lines and UI elements
                        if (not line or 
                            line.startswith('Edit') or
                            line.startswith('Thinking') or
                            line.startswith('Send') or
                            line.startswith('Type') or
                            line.startswith('Message') or
                            'Pondered' in line or
                            line.endswith('s') and line[:-1].isdigit()):  # Skip timing like "2s"
                            continue
                        
                        # Skip Claude's internal reasoning
                        if skip_reasoning:
                            # Look for reasoning patterns
                            reasoning_indicators = [
                                'The user is asking',
                                'I should',
                                'This means',
                                'I think',
                                'since they',
                                'but they specifically',
                                'This is a straightforward',
                                'doesn\'t require',
                                'Decoded user\'s',
                                'planned inline response'
                            ]
                            
                            # If this line contains reasoning, skip it
                            if any(indicator in line for indicator in reasoning_indicators):
                                continue
                            
                            # If we see the actual answer starting (like "Java is a popular...")
                            # then stop skipping reasoning
                            if (line.startswith('Java is') or 
                                line.startswith('Here are') or
                                line.startswith('Key features') or
                                (len(line) > 30 and not any(indicator in line for indicator in reasoning_indicators))):
                                skip_reasoning = False
                                collecting = True
                        
                        # Start collecting when we see substantial content (non-reasoning)
                        if len(line) > 20 and not collecting and not skip_reasoning:
                            collecting = True
                        
                        if collecting:
                            # Stop if we hit another question or UI element
                            if (line.endswith('?') and len(line) > 50) or \
                               any(ui in line for ui in ['Claude', 'Sonnet', 'Set as default', 'Google Chrome']):
                                break
                            
                            # Skip if we encounter reasoning again (like "AB" markers or repeated questions)
                            if (line in ['AB', 'A', 'B'] or 
                                line == question.strip() or
                                'The user is asking again' in line):
                                break
                            
                            response_lines.append(line)
                    
                    if response_lines:
                        full_response = '\n'.join(response_lines)
                        
                        # Create preview for logging
                        preview = full_response[:300] + "..." if len(full_response) > 300 else full_response
                        self.log(f"Found complete response via Strategy 1: {preview}")
                        self.end_operation("WAIT_RESPONSE", "- Complete response found via Strategy 1")
                        return full_response
                
            except Exception as e:
                self.log(f"Strategy 1 failed: {e}")
            
            # Strategy 2: Look for response after question in lines
            try:
                self.log("Strategy 2: Looking for response after question...")
                
                # Wait a bit more for response to appear
                await asyncio.sleep(5)
                
                # Get all text content from the page
                page_text = await self.page.evaluate("document.body.innerText")
                
                # Split into lines and look for the response
                lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                
                # Find our question in the text
                question_found = False
                for i, line in enumerate(lines):
                    if question.lower() in line.lower():
                        question_found = True
                        self.log(f"Found question at line {i}: {line}")
                        
                        # Look for substantial response content in the following lines
                        response_lines = []
                        for j in range(i + 1, min(i + 50, len(lines))):  # Look further ahead
                            potential_line = lines[j].strip()
                            
                            # Skip UI elements and short lines
                            if (len(potential_line) < 20 or
                                potential_line.startswith('Thinking') or
                                potential_line.startswith('Send') or
                                potential_line.startswith('Type') or
                                potential_line.startswith('Message') or
                                'Claude' in potential_line or
                                'Sonnet' in potential_line):
                                continue
                            
                            # Collect substantial lines
                            if len(potential_line) > 30:
                                response_lines.append(potential_line)
                                
                                # If we have enough content, return it
                                if len(response_lines) >= 3 or len(' '.join(response_lines)) > 200:
                                    full_response = ' '.join(response_lines)
                                    preview = full_response[:200] + "..." if len(full_response) > 200 else full_response
                                    self.log(f"Found response via Strategy 2: {preview}")
                                    self.end_operation("WAIT_RESPONSE", "- Response found via Strategy 2")
                                    return full_response
                        break
                
                if not question_found:
                    self.log("Question not found in page content")
                        
            except Exception as e:
                self.log(f"Strategy 2 failed: {e}")
            
            # Strategy 3: Direct element inspection for substantial content
            try:
                self.log("Strategy 3: Direct element inspection...")
                
                # Wait a bit more
                await asyncio.sleep(3)
                
                # Look for elements that might contain substantial response content
                all_elements = await self.page.query_selector_all('p, div, span')
                
                for element in reversed(all_elements[-50:]):  # Check more elements
                    try:
                        text = await element.inner_text()
                        text = text.strip()
                        
                        # Look for substantial response content
                        if (text and 
                            len(text) > 100 and  # Substantial content
                            text != '0s' and
                            question.lower() not in text.lower() and
                            not text.startswith('Thinking') and
                            not text.startswith('Send') and
                            not text.startswith('Type') and
                            not text.startswith('Message') and
                            'Claude' not in text and
                            'Sonnet' not in text):
                            
                            preview = text[:200] + "..." if len(text) > 200 else text
                            self.log(f"Found response via Strategy 3: {preview}")
                            self.end_operation("WAIT_RESPONSE", "- Response found via Strategy 3")
                            return text
                    except:
                        continue
                
            except Exception as e:
                self.log(f"Strategy 3 failed: {e}")
            
            # Strategy 4: Final comprehensive search for any substantial content
            try:
                self.log("Strategy 4: Final comprehensive search...")
                await asyncio.sleep(5)
                
                # Get all text from the page
                full_page_text = await self.page.evaluate("document.body.innerText")
                all_lines = [line.strip() for line in full_page_text.split('\n') if line.strip()]
                
                # Look for any substantial content that could be a response
                for line in reversed(all_lines):  # Start from the end
                    if (line and 
                        len(line) > 50 and  # Substantial content
                        line != '0s' and
                        question.lower() not in line.lower() and
                        not line.startswith('Thinking') and
                        not line.startswith('Send') and
                        not line.startswith('Type') and
                        not line.startswith('Message') and
                        not line.startswith('What is') and
                        'Claude' not in line and
                        'Sonnet' not in line and
                        'Set as default' not in line):
                        
                        # This looks like substantial response content
                        preview = line[:200] + "..." if len(line) > 200 else line
                        self.log(f"Found response via Strategy 4: {preview}")
                        self.end_operation("WAIT_RESPONSE", "- Response found via Strategy 4")
                        return line
                
            except Exception as e:
                self.log(f"Strategy 4 failed: {e}")
            
            self.log("No response detected with any strategy")
            self.end_operation("WAIT_RESPONSE", "- No response found")
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
            question = "What is java. show sample code? anwer inline. do not open side tab"
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
