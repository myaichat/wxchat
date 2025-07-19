#!/usr/bin/env python3
"""
Test script to communicate with Gemini chat via Chrome DevTools Protocol (CDP)
Uses WebSocket to connect to Chrome debug tab and interact with Gemini interface
"""

import asyncio
import json
import websockets
import requests
import time
from typing import Optional, Dict, Any

class GeminiChromeDebugger:
    def __init__(self, debug_port: int = 9222):
        self.debug_port = debug_port
        self.websocket = None
        self.page_id = None
        self.websocket_url = None
        self.message_id = 0
        
    def get_message_id(self) -> int:
        """Get next message ID for CDP commands"""
        self.message_id += 1
        return self.message_id
    
    def get_chrome_tabs(self) -> list:
        """Get list of Chrome tabs from debug endpoint"""
        try:
            response = requests.get(f"http://localhost:{self.debug_port}/json")
            return response.json()
        except Exception as e:
            print(f"Error getting Chrome tabs: {e}")
            return []
    
    def find_gemini_tab(self) -> Optional[Dict[str, Any]]:
        """Find Gemini tab in Chrome debug tabs"""
        tabs = self.get_chrome_tabs()
        for tab in tabs:
            if "gemini.google.com" in tab.get("url", ""):
                return tab
        return None
    
    async def connect(self, websocket_url: str = None):
        """Connect to Chrome DevTools WebSocket"""
        if websocket_url:
            self.websocket_url = websocket_url
        else:
            # Auto-detect Gemini tab
            gemini_tab = self.find_gemini_tab()
            if not gemini_tab:
                raise Exception("Gemini tab not found. Make sure Gemini is open in Chrome with debug mode enabled.")
            
            self.websocket_url = gemini_tab["webSocketDebuggerUrl"]
            self.page_id = gemini_tab["id"]
        
        print(f"Connecting to: {self.websocket_url}")
        self.websocket = await websockets.connect(self.websocket_url)
        
        # Enable Runtime and DOM domains
        await self.send_command("Runtime.enable")
        await self.send_command("DOM.enable")
        await self.send_command("Page.enable")
        
        print("Connected to Chrome DevTools")
    
    async def send_command(self, method: str, params: dict = None) -> dict:
        """Send CDP command and wait for response"""
        if not self.websocket:
            raise Exception("Not connected to Chrome DevTools")
        
        message_id = self.get_message_id()
        command = {
            "id": message_id,
            "method": method,
            "params": params or {}
        }
        
        await self.websocket.send(json.dumps(command))
        
        # Wait for response
        while True:
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("id") == message_id:
                return data
            # Ignore other messages (events, etc.)
    
    async def execute_js(self, javascript_code: str) -> Any:
        """Execute JavaScript code in the page"""
        try:
            response = await self.send_command("Runtime.evaluate", {
                "expression": javascript_code,
                "returnByValue": True,
                "awaitPromise": True
            })
            
            if "result" in response:
                result = response["result"]
                
                if "exceptionDetails" in result:
                    error_msg = result["exceptionDetails"].get("text", "Unknown JavaScript error")
                    raise Exception(f"JavaScript error: {error_msg}")
                
                if "result" in result:
                    if "value" in result["result"]:
                        return result["result"]["value"]
                    elif "unserializableValue" in result["result"]:
                        return result["result"]["unserializableValue"]
                    else:
                        return None
                
                return result
            else:
                raise Exception(f"Unexpected response format: {response}")
                
        except Exception as e:
            print(f"JavaScript execution error: {e}")
            raise
    
    async def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """Wait for element to appear on page"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = await self.execute_js(f"document.querySelector('{selector}') !== null")
                if result:
                    return True
            except:
                pass
            await asyncio.sleep(0.5)
        return False
    
    async def debug_page_elements(self):
        """Debug function to see what elements are available on the page"""
        try:
            print("Debugging page elements...")
            
            # Get all input-like elements
            elements_info = await self.execute_js("""
                const inputs = document.querySelectorAll('input, textarea, div[contenteditable], div[role="textbox"]');
                const buttons = document.querySelectorAll('button, div[role="button"]');
                
                const inputInfo = Array.from(inputs).map(el => ({
                    tag: el.tagName,
                    type: el.type || 'none',
                    contenteditable: el.contentEditable,
                    role: el.getAttribute('role'),
                    placeholder: el.placeholder || el.getAttribute('data-placeholder'),
                    classes: el.className,
                    id: el.id
                }));
                
                const buttonInfo = Array.from(buttons).map(el => ({
                    tag: el.tagName,
                    text: el.textContent.trim().substring(0, 50),
                    ariaLabel: el.getAttribute('aria-label'),
                    classes: el.className,
                    id: el.id
                }));
                
                return { inputs: inputInfo, buttons: buttonInfo };
            """)
            
            print(f"Found {len(elements_info.get('inputs', []))} input elements:")
            for i, inp in enumerate(elements_info.get('inputs', [])):
                print(f"  {i+1}. {inp}")
            
            print(f"Found {len(elements_info.get('buttons', []))} button elements:")
            for i, btn in enumerate(elements_info.get('buttons', [])):
                print(f"  {i+1}. {btn}")
                
        except Exception as e:
            print(f"Debug failed: {e}")
    
    async def set_input_text(self, selector: str, text: str) -> bool:
        """Try different methods to set text in input field"""
        methods = [
            # Method 1: Direct content setting
            f"""
                const el = document.querySelector('{selector}');
                if (el) {{
                    el.focus();
                    el.textContent = '{text}';
                    el.innerHTML = '{text}';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            """,
            
            # Method 2: Using execCommand
            f"""
                const el = document.querySelector('{selector}');
                if (el) {{
                    el.focus();
                    document.execCommand('selectAll');
                    document.execCommand('insertText', false, '{text}');
                    return true;
                }}
                return false;
            """,
            
            # Method 3: Character by character typing simulation
            f"""
                const el = document.querySelector('{selector}');
                if (el) {{
                    el.focus();
                    el.textContent = '';
                    const text = '{text}';
                    for (let i = 0; i < text.length; i++) {{
                        const char = text[i];
                        el.textContent += char;
                        el.dispatchEvent(new KeyboardEvent('keydown', {{ key: char, bubbles: true }}));
                        el.dispatchEvent(new KeyboardEvent('keyup', {{ key: char, bubbles: true }}));
                    }}
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            """,
            
            # Method 4: For textarea elements
            f"""
                const el = document.querySelector('{selector}');
                if (el && el.tagName === 'TEXTAREA') {{
                    el.focus();
                    el.value = '{text}';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            """
        ]
        
        for i, method in enumerate(methods):
            try:
                result = await self.execute_js(method)
                if result:
                    print(f"Successfully set text using method {i+1}")
                    return True
            except Exception as e:
                print(f"Method {i+1} failed: {e}")
                continue
        
        return False
    
    async def try_generic_input(self, text: str) -> bool:
        """Try to find and interact with any input field generically"""
        try:
            result = await self.execute_js(f"""
                // Try to find any focusable input element
                const candidates = document.querySelectorAll('input, textarea, div[contenteditable="true"], div[role="textbox"]');
                
                for (let el of candidates) {{
                    // Skip hidden elements
                    if (el.offsetParent === null) continue;
                    
                    try {{
                        el.focus();
                        
                        // Clear existing content
                        if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {{
                            el.value = '{text}';
                        }} else {{
                            el.textContent = '{text}';
                            el.innerHTML = '{text}';
                        }}
                        
                        // Trigger events
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        
                        return true;
                    }} catch (e) {{
                        continue;
                    }}
                }}
                return false;
            """)
            
            return result
        except Exception as e:
            print(f"Generic input attempt failed: {e}")
            return False
    
    async def click_send_button(self, selectors: list) -> bool:
        """Try to click send button using various selectors"""
        for selector in selectors:
            try:
                exists = await self.execute_js(f"document.querySelector('{selector}') !== null")
                if exists:
                    print(f"Found send button with selector: {selector}")
                    clicked = await self.execute_js(f"""
                        const btn = document.querySelector('{selector}');
                        if (btn && btn.offsetParent !== null) {{
                            btn.click();
                            return true;
                        }}
                        return false;
                    """)
                    if clicked:
                        return True
            except Exception as e:
                print(f"Send button selector {selector} failed: {e}")
                continue
        
        # Try generic button finding
        try:
            result = await self.execute_js("""
                const buttons = document.querySelectorAll('button, div[role="button"]');
                for (let btn of buttons) {
                    const text = btn.textContent.toLowerCase();
                    const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                    
                    if (text.includes('send') || ariaLabel.includes('send') || 
                        btn.querySelector('svg') || btn.querySelector('[data-testid*="send"]')) {
                        if (btn.offsetParent !== null) {
                            btn.click();
                            return true;
                        }
                    }
                }
                return false;
            """)
            return result
        except Exception as e:
            print(f"Generic send button click failed: {e}")
            return False
    
    async def try_enter_key(self, selector: str):
        """Try pressing Enter key on the input field"""
        try:
            await self.execute_js(f"""
                const input = document.querySelector('{selector}');
                if (input) {{
                    input.focus();
                    input.dispatchEvent(new KeyboardEvent('keydown', {{
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true
                    }}));
                    input.dispatchEvent(new KeyboardEvent('keyup', {{
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true
                    }}));
                }}
            """)
            print("Sent Enter key event")
        except Exception as e:
            print(f"Enter key failed: {e}")
    
    async def send_message_to_gemini(self, message: str) -> str:
        """Send message to Gemini chat and get response"""
        print(f"Sending message: {message}")
        
        # First, let's debug what elements are available
        await self.debug_page_elements()
        
        # Common selectors for Gemini chat interface
        input_selectors = [
            'div[contenteditable="true"]',
            'textarea[placeholder*="Enter a prompt"]',
            'div[data-testid="chat-input"]',
            'div[role="textbox"]',
            '.ql-editor',
            'div[contenteditable="true"][data-placeholder]',
            'textarea',
            'input[type="text"]'
        ]
        
        send_button_selectors = [
            'button[data-testid="send-button"]',
            'button[aria-label*="Send"]',
            'button[type="submit"]',
            'div[role="button"][aria-label*="Send"]',
            'button:has(svg)',
            'button[data-testid="send"]',
            'button[aria-label*="send"]',
            'svg[data-testid="send-icon"]'
        ]
        
        # Try to find input field
        input_found = False
        working_selector = None
        
        for selector in input_selectors:
            try:
                exists = await self.execute_js(f"document.querySelector('{selector}') !== null")
                if exists:
                    print(f"Found input field with selector: {selector}")
                    
                    # Try different methods to set the text
                    success = await self.set_input_text(selector, message)
                    if success:
                        input_found = True
                        working_selector = selector
                        break
                    else:
                        print(f"Failed to set text for selector: {selector}")
            except Exception as e:
                print(f"Selector {selector} failed: {e}")
                continue
        
        if not input_found:
            # Try a more generic approach
            print("Trying generic input detection...")
            success = await self.try_generic_input(message)
            if not success:
                raise Exception("Could not find or interact with Gemini input field")
        
        # Wait a moment for the input to register
        await asyncio.sleep(1)
        
        # Try to find and click send button
        send_clicked = await self.click_send_button(send_button_selectors)
        
        if not send_clicked:
            # Try pressing Enter as fallback
            print("Trying Enter key as fallback")
            await self.try_enter_key(working_selector or 'div[contenteditable="true"]')
        
        # Wait for response
        print("Waiting for Gemini response...")
        await asyncio.sleep(3)  # Give time for response to start
        
        # Try to get the latest response
        response_selectors = [
            'div[data-testid="conversation-turn-3"] div[data-testid="response-text"]',
            'div[data-testid="response"] div[data-testid="response-text"]',
            '.model-response-text',
            'div[data-testid*="response"] p',
            'div[role="presentation"] p:last-child',
            'div:has(> p):last-of-type p'
        ]
        
        response_text = ""
        for selector in response_selectors:
            try:
                response_text = await self.execute_js(f"""
                    const elements = document.querySelectorAll('{selector}');
                    if (elements.length > 0) {{
                        return elements[elements.length - 1].textContent.trim();
                    }}
                    return '';
                """)
                if response_text and len(response_text) > 10:  # Reasonable response length
                    print(f"Got response with selector: {selector}")
                    break
            except Exception as e:
                print(f"Response selector {selector} failed: {e}")
                continue
        
        if not response_text:
            # Fallback: get all text content and try to extract response
            try:
                all_text = await self.execute_js("""
                    const responses = document.querySelectorAll('div[data-testid*="response"], .model-response, div:has(p)');
                    let lastResponse = '';
                    responses.forEach(el => {
                        const text = el.textContent.trim();
                        if (text.length > lastResponse.length) {
                            lastResponse = text;
                        }
                    });
                    return lastResponse;
                """)
                response_text = all_text if all_text else "No response found"
            except:
                response_text = "Error getting response"
        
        return response_text
    
    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            print("Disconnected from Chrome DevTools")

async def test_gemini_chat():
    """Test function to demonstrate Gemini chat interaction"""
    debugger = GeminiChromeDebugger()
    
    try:
        # You can either auto-detect or use the specific WebSocket URL from your JSON
        websocket_url = "ws://localhost:9222/devtools/page/8D25B8EDED124ED7635252EF0F0E4217"
        
        # Connect to Chrome DevTools
        await debugger.connect(websocket_url)
        
        # Test questions
        test_questions = [
            "Hello, can you help me with Python programming?",
            "What is the capital of France?",
            "Explain quantum computing in simple terms"
        ]
        
        for question in test_questions:
            print(f"\n{'='*50}")
            print(f"Question: {question}")
            print(f"{'='*50}")
            
            try:
                response = await debugger.send_message_to_gemini(question)
                print(f"Gemini Response: {response}")
            except Exception as e:
                print(f"Error sending question: {e}")
            
            # Wait between questions
            await asyncio.sleep(2)
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await debugger.close()

def main():
    """Main function to run the test"""
    print("Gemini Chrome Debug Test")
    print("Make sure Chrome is running with debug mode enabled:")
    print("chrome.exe --remote-debugging-port=9222")
    print("And Gemini chat is open in a tab")
    print()
    
    # Run the async test
    asyncio.run(test_gemini_chat())

if __name__ == "__main__":
    main()
