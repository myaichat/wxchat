import asyncio
import json
import websockets
from playwright.async_api import async_playwright
import time
from datetime import datetime
import argparse
import sys

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
            
            # Find the Claude.ai chat page specifically
            self.log(f"Searching through {len(pages)} pages for Claude.ai...")
            claude_page = None
            all_pages_info = []
            
            for page in pages:
                url = page.url
                all_pages_info.append(f"  - {url}")
                
                # Prioritize Claude.ai pages specifically
                if "claude.ai" in url:
                    claude_page = page
                    self.log(f"Found Claude.ai page: {url}")
                    break
            
            # Log all available pages for debugging
            self.log("Available pages:")
            for page_info in all_pages_info:
                self.log(page_info)
            
            if claude_page:
                self.page = claude_page
                self.log(f"Connected to Claude.ai page: {self.page.url}")
            else:
                # Look for any chat-related page as fallback, but be more specific
                fallback_page = None
                for page in pages:
                    url = page.url
                    # Only match chat URLs that are NOT ChatGPT
                    if ("chat" in url and "chatgpt" not in url.lower() and "openai" not in url.lower()) or "claude" in url.lower():
                        fallback_page = page
                        break
                
                if fallback_page:
                    self.page = fallback_page
                    self.log(f"Connected to fallback chat page: {self.page.url}")
                else:
                    # Use the first page as last resort
                    self.page = pages[0]
                    self.log(f"No Claude.ai page found, using first available page: {self.page.url}")
                    self.log("WARNING: This may not be a Claude.ai page!")
            
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

    async def send_message_with_streaming(self, question):
        """Send a message to the chat and stream the response as it appears"""
        self.start_operation("SEND_MESSAGE")
        try:
            if not self.page:
                raise Exception("Not connected to any page")
            
            # Wait for page to load
            self.log("Waiting for page to load...")
            await self.page.wait_for_load_state('networkidle')
            
            # Get initial page content to establish baseline
            initial_content = await self.page.evaluate("document.body.innerText")
            self.log("Captured initial page content")
            
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
                    input_element = await self.page.wait_for_selector(selector, timeout=500)
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
                for i, elem in enumerate(elements[:5]):
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
                    send_button = await self.page.wait_for_selector(selector, timeout=500)
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
            
            self.end_operation("SEND_MESSAGE", "- Message sent successfully")
            self.start_operation("STREAM_RESPONSE")
            
            # Start streaming response
            previous_content = ""
            last_response_length = 0
            response_started = False
            max_iterations = 120  # Maximum 2 minutes of monitoring
            iteration = 0
            no_change_count = 0  # Track how many iterations without changes
            max_no_change = 6  # Exit after 3 seconds of no changes (6 * 0.5s)
            
            while iteration < max_iterations:
                try:
                    # Get current page content
                    current_content = await self.page.evaluate("document.body.innerText")
                    
                    # Find new content that appeared after our question
                    if not response_started:
                        # Look for the start of a response
                        if self._detect_response_start(current_content, question, initial_content):
                            response_started = True
                            self.log("Response started - beginning to stream")
                    
                    if response_started:
                        # Extract the current response content
                        current_response = self._extract_current_response(current_content, question)
                        
                        if current_response and len(current_response) > last_response_length:
                            # New content detected - yield the incremental part
                            new_content = current_response[last_response_length:]
                            if new_content.strip():
                                self.log(f"Streaming new content: {new_content[:100]}...")
                                yield new_content
                                last_response_length = len(current_response)
                                no_change_count = 0  # Reset no-change counter
                        else:
                            # No new content detected
                            no_change_count += 1
                        
                        # Check if response is complete
                        if self._is_response_complete(current_content, current_response):
                            self.log("Response appears to be complete")
                            break
                        
                        # Exit if no changes for too long and we have some content
                        # Reduced threshold for shorter responses
                        if (no_change_count >= max_no_change and 
                            current_response and 
                            len(current_response) > 10):  # Reduced from 100 to 10
                            self.log(f"No changes detected for {no_change_count * 0.5} seconds, assuming complete")
                            break
                    
                    # Wait before next check
                    await asyncio.sleep(0.5)  # Check every 500ms
                    iteration += 1
                    
                except Exception as e:
                    self.log(f"Error during streaming iteration {iteration}: {e}")
                    await asyncio.sleep(1)
                    iteration += 1
                    continue
            
            if iteration >= max_iterations:
                self.log("Reached maximum streaming iterations")
            
            self.end_operation("STREAM_RESPONSE", "- Streaming completed")
                
        except Exception as e:
            self.log(f"Error in streaming: {e}")
            yield f"Error: {e}"

    def _detect_response_start(self, current_content, question, initial_content):
        """Detect if Claude has started responding"""
        try:
            # Look for new substantial content that wasn't in initial content
            current_lines = [line.strip() for line in current_content.split('\n') if line.strip()]
            initial_lines = [line.strip() for line in initial_content.split('\n') if line.strip()]
            
            # Find lines that are new
            new_lines = []
            for line in current_lines:
                if line not in initial_lines and len(line) > 3:  # Reduced from 10 to 3
                    new_lines.append(line)
            
            # Look for response indicators
            for line in new_lines:
                # Skip UI elements and our own question
                if (question.lower() in line.lower() or
                    line.startswith('Send') or
                    line.startswith('Type') or
                    'Claude' in line or
                    'Sonnet' in line):
                    continue
                
                # Allow "Thinking" lines as they indicate response start
                if line.startswith('Thinking'):
                    return True
                
                # If we find any substantial new content, response has started
                # Reduced threshold for shorter responses
                if len(line) > 5:  # Reduced from 20 to 5
                    return True
            
            # Additional check: look for common response patterns
            content_lower = current_content.lower()
            response_indicators = [
                "i'm doing well",
                "i'm good",
                "hello! what's up",
                "hello",
                "hi there",
                "how can i help",
                "thanks for asking",
                "what's up"
            ]
            
            for indicator in response_indicators:
                if indicator in content_lower and indicator not in initial_content.lower():
                    return True
            
            return False
            
        except Exception as e:
            self.log(f"Error detecting response start: {e}")
            return False

    def _extract_current_response(self, current_content, question):
        """Extract the current response content from the page"""
        try:
            lines = [line.strip() for line in current_content.split('\n') if line.strip()]
            
            # Find the LAST occurrence of our question (most recent)
            question_index = -1
            for i in range(len(lines) - 1, -1, -1):  # Search backwards
                line = lines[i]
                if question.lower() in line.lower() and len(line) >= len(question):
                    question_index = i
                    break
            
            if question_index >= 0:
                # Collect response content after the question
                response_lines = []
                found_actual_content = False
                
                for i in range(question_index + 1, len(lines)):
                    line = lines[i].strip()
                    
                    # Skip empty lines and obvious UI elements
                    if (not line or 
                        line.startswith('Edit') or
                        line.startswith('Send') or
                        line.startswith('Type') or
                        line.startswith('Message') or
                        'Pondered' in line or
                        (line.endswith('s') and line[:-1].isdigit())):
                        continue
                    
                    # Skip Claude's internal reasoning - be more comprehensive
                    reasoning_indicators = [
                        'The user is asking',
                        'The user',  # Often starts Claude's reasoning
                        'I should',
                        'This means',
                        'I think',
                        'since they',
                        'but they specifically',
                        'This is a straightforward',
                        'doesn\'t require',
                        'Decoded user\'s',
                        'planned inline response',
                        'Strategized inline',
                        'Preparing comprehensive',
                        'Preparing to show'
                    ]
                    
                    # If this looks like reasoning, skip it
                    if any(indicator in line for indicator in reasoning_indicators):
                        continue
                    
                    # Skip "Thinking" lines but allow other content
                    if line.startswith('Thinking'):
                        continue
                    
                    # Stop if we hit obvious UI elements, navigation, or another user message
                    if (any(ui in line for ui in ['Claude', 'Sonnet', 'Set as default', 'Google Chrome', 'Retry', 'Copy', 'Edit']) or
                        line in ['AB', 'A', 'B', 'Retry', 'Copy', 'Edit'] or
                        line == question.strip() or
                        # Stop if we hit what looks like another question/conversation
                        (len(line) > 20 and line.endswith('?') and 
                         any(word in line.lower() for word in ['what', 'how', 'why', 'when', 'where', 'can', 'do', 'is']))):
                        break
                    
                    # Allow code blocks and technical content
                    if (line.startswith('public class') or 
                        line.startswith('java') or
                        line.startswith('```') or
                        'Hello World' in line or
                        'System.out.println' in line):
                        response_lines.append(line)
                        found_actual_content = True
                        continue
                    
                    # Look for actual response content (not just reasoning)
                    # Common patterns for actual responses
                    if (len(line) > 5 and  # Reduced from 10 to 5 for shorter responses
                        not line.startswith('The ') and  # Avoid "The user..." reasoning
                        not line.startswith('This ') and  # Avoid "This is..." reasoning
                        (line[0].isupper() or line.startswith('I\'m') or 'Java' in line or 'programming' in line or
                         'doing well' in line or 'good' in line or 'hello' in line)):
                        response_lines.append(line)
                        found_actual_content = True
                    elif found_actual_content:
                        # If we've found actual content, continue collecting
                        response_lines.append(line)
                
                if response_lines and found_actual_content:
                    return '\n'.join(response_lines)
            
            return ""
            
        except Exception as e:
            self.log(f"Error extracting response: {e}")
            return ""

    def _is_response_complete(self, current_content, current_response):
        """Check if the response appears to be complete"""
        try:
            # Look for completion indicators
            if not current_response:
                return False
            
            # Check if there are completion indicators in the content
            completion_indicators = [
                'Copy code',
                'Edit message',
                'Regenerate',
                'thumbs up',
                'thumbs down',
                'Retry',
                'Share & publish',
                'Continue this conversation',
                'Copy',
                'Edit'
            ]
            
            for indicator in completion_indicators:
                if indicator.lower() in current_content.lower():
                    self.log(f"Found completion indicator: {indicator}")
                    return True
            
            # Look for Claude's response completion patterns
            lines = current_content.lower().split('\n')
            for line in lines:
                line = line.strip()
                # Check for common Claude completion patterns
                if (line.startswith('retry') or 
                    'continue this conversation' in line or
                    'share & publish' in line or
                    line == 'copy' or
                    line == 'edit'):
                    self.log(f"Found completion pattern: {line}")
                    return True
            
            # Only use "Thinking about responding to a casual greeting" for very short responses
            # This prevents cutting off longer technical responses
            if (len(current_response.strip()) < 50 and 
                'thinking about responding to a casual greeting' in current_content.lower()):
                self.log("Found casual greeting completion indicator for short response")
                return True
            
            # Additional check: if response ends with a question mark and has substantial content
            if (current_response.strip().endswith('?') and 
                len(current_response.strip()) > 50 and
                ('how are you' in current_response.lower() or 
                 'what can i help' in current_response.lower() or
                 'anything else' in current_response.lower())):
                self.log("Response ends with typical Claude completion question")
                return True
            
            return False
            
        except Exception as e:
            self.log(f"Error checking completion: {e}")
            return False

    async def send_message_and_get_response(self, question):
        """Send a message and get complete response (legacy method for compatibility)"""
        full_response = ""
        async for chunk in self.send_message_with_streaming(question):
            if not chunk.startswith("Error:"):
                full_response += chunk
        
        return full_response if full_response else None

    async def close(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

async def main_async(question=None, debug_port=9222, streaming=True):
    """Main function to demonstrate streaming usage"""
    bot = ChromeDebugChatBot(debug_port=debug_port)
    
    try:
        bot.log("=== Starting Claude Chat Bot with Streaming ===")
        
        # Connect to existing Chrome tab
        if await bot.connect_to_existing_tab():
            
            # Use provided question or default
            if not question:
                question = "How are you?"
            
            bot.log(f"Sending question: {question}")
            
            if streaming:
                print("\n=== STREAMING RESPONSE ===")
                full_response = ""
                
                async for chunk in bot.send_message_with_streaming(question):
                    if not chunk.startswith("Error:"):
                        print(chunk, end='', flush=True)  # Print each chunk as it arrives
                        full_response += chunk
                    else:
                        print(f"\nError: {chunk}")
                        break
                
                print("\n=== END OF STREAMING ===")
                
                if full_response:
                    bot.log(f"Complete response received ({len(full_response)} characters)")
                    return full_response
                else:
                    bot.log("No response received")
                    return None
            else:
                # Non-streaming mode
                response = await bot.send_message_and_get_response(question)
                if response:
                    print(f"\nResponse: {response}")
                    bot.log(f"Response received: {response}")
                    return response
                else:
                    bot.log("Failed to get response")
                    return None
                
        else:
            bot.log("Failed to connect to Chrome debug session")
            return None
            
    except Exception as e:
        bot.log(f"Error in main: {e}")
        return None
        
    finally:
        bot.log("Cleaning up resources...")
        await bot.close()
        bot.log("=== Claude Chat Bot Finished ===")

async def main_sync(question=None, debug_port=9222):
    """Legacy main function for non-streaming usage"""
    return await main_async(question=question, debug_port=debug_port, streaming=False)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Claude Streaming Chat Bot - Connect to Claude.ai via Chrome debug protocol',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python claude_streaming_chat.py "What is Python?"
  python claude_streaming_chat.py "Explain machine learning" --port 9223
  python claude_streaming_chat.py "Hello" --no-streaming
  
Prerequisites:
  Make sure Chrome is running with debug enabled:
  chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
        """
    )
    
    parser.add_argument(
        'question',
        nargs='?',
        default=None,
        help='Question to ask Claude (if not provided, will use default question)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=9222,
        help='Chrome debug port (default: 9222)'
    )
    
    parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Disable streaming mode and get complete response at once'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Claude Streaming Chat Bot 1.0'
    )
    
    return parser.parse_args()


def ask_claude(question, debug_port=9222, streaming=True):
    """
    Public function to ask Claude a question programmatically.
    
    Args:
        question (str): The question to ask Claude
        debug_port (int): Chrome debug port (default: 9222)
        streaming (bool): Whether to use streaming mode (default: True)
    
    Returns:
        str: Claude's response, or None if failed
    
    Example:
        from chat_handlers.claude_streaming_chat import ask_claude
        response = ask_claude("What is Python?")
        print(response)
    """
    return asyncio.run(main_async(question=question, debug_port=debug_port, streaming=streaming))


async def ask_claude_async(question, debug_port=9222, streaming=True):
    """
    Async version of ask_claude for use in async contexts.
    
    Args:
        question (str): The question to ask Claude
        debug_port (int): Chrome debug port (default: 9222)
        streaming (bool): Whether to use streaming mode (default: True)
    
    Returns:
        str: Claude's response, or None if failed
    
    Example:
        from chat_handlers.claude_streaming_chat import ask_claude_async
        response = await ask_claude_async("What is Python?")
        print(response)
    """
    return await main_async(question=question, debug_port=debug_port, streaming=streaming)


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Run the main function with parsed arguments
    asyncio.run(main_async(
        question=args.question,
        debug_port=args.port,
        streaming=not args.no_streaming
    ))
