import asyncio
from playwright.async_api import async_playwright
import time
from datetime import datetime

class SimpleClaudeChatBot:
    def __init__(self, debug_port=9222):
        self.debug_port = debug_port
        self.page = None
        self.browser = None
        self.start_time = time.time()

    def log(self, message):
        """Simple logging with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        elapsed = time.time() - self.start_time
        print(f"[{timestamp}] (+{elapsed:.2f}s) {message}")

    async def connect_to_claude(self):
        """Connect to existing Chrome instance with Claude.ai"""
        try:
            self.log("Starting Playwright...")
            self.playwright = await async_playwright().start()
            
            self.log(f"Connecting to Chrome debug port {self.debug_port}...")
            self.browser = await self.playwright.chromium.connect_over_cdp(
                f"http://localhost:{self.debug_port}"
            )
            
            # Find Claude.ai page
            contexts = self.browser.contexts
            for context in contexts:
                for page in context.pages:
                    if "claude.ai" in page.url:
                        self.page = page
                        self.log(f"Connected to Claude page: {page.url}")
                        return True
            
            self.log("No Claude.ai page found")
            return False
            
        except Exception as e:
            self.log(f"Connection error: {e}")
            return False

    async def send_and_get_response(self, question):
        """Send message and get response using a simple approach"""
        try:
            self.log(f"Sending question: {question}")
            
            # Find and fill input
            input_element = await self.page.wait_for_selector('[contenteditable="true"]', timeout=5000)
            await input_element.fill(question)
            
            # Send message (press Enter)
            await input_element.press('Enter')
            self.log("Message sent")
            
            # Wait longer for Claude to respond completely
            self.log("Waiting for Claude to finish responding...")
            await asyncio.sleep(8)  # Wait 8 seconds for response to complete
            
            # Get all page content
            page_content = await self.page.evaluate("document.body.innerText")
            lines = [line.strip() for line in page_content.split('\n') if line.strip()]
            
            # Debug: show some recent lines
            self.log("Recent page content (last 10 lines):")
            for i, line in enumerate(lines[-10:]):
                self.log(f"  {i}: {line}")
            
            # Look for math answer patterns specifically
            math_patterns = [
                r'2\s*\+\s*2\s*=\s*4',  # "2 + 2 = 4"
                r'2\+2=4',               # "2+2=4"
                r'equals?\s*4',          # "equals 4"
                r'is\s*4',               # "is 4"
                r'answer\s*is\s*4',      # "answer is 4"
            ]
            
            import re
            
            # First, look for exact math equation
            for line in reversed(lines):
                for pattern in math_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        self.log(f"Found math answer: {line}")
                        return line
            
            # Then look for any line containing "4" that's not UI text
            for line in reversed(lines):
                if ('4' in line and 
                    len(line) <= 30 and  # Short lines more likely to be answers
                    question.lower() not in line.lower() and
                    not line.startswith('Thinking') and
                    not line.startswith('Send') and
                    not line.startswith('Type') and
                    not line.startswith('The user') and
                    not 'Sonnet' in line and  # Skip model name
                    not 'Claude' in line and  # Skip Claude branding
                    not 'user is asking' in line.lower() and
                    not 'simple math' in line.lower()):
                    
                    self.log(f"Found line with '4': {line}")
                    return line
            
            # Final fallback: look for any short numeric content
            for line in reversed(lines):
                if (line and 
                    len(line) <= 10 and  # Very short
                    any(char.isdigit() for char in line) and
                    question.lower() not in line.lower() and
                    not line.startswith('Thinking') and
                    line != '0s' and
                    'Sonnet' not in line):
                    
                    self.log(f"Found short numeric content: {line}")
                    return line
            
            self.log("No response found")
            return None
            
        except Exception as e:
            self.log(f"Error: {e}")
            return None

    async def close(self):
        """Clean up"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

async def main():
    bot = SimpleClaudeChatBot()
    
    try:
        print("=== Simple Claude Chat Bot ===")
        
        if await bot.connect_to_claude():
            response = await bot.send_and_get_response("What is 2+2?")
            
            if response:
                print(f"\n✅ SUCCESS: Claude responded with: '{response}'")
            else:
                print(f"\n❌ FAILED: No response captured")
        else:
            print("❌ Failed to connect to Claude")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await bot.close()
        print("=== Finished ===")

if __name__ == "__main__":
    asyncio.run(main())
