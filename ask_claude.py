"""
Claude Chat Automation via Chrome DevTools Protocol
Automates sending messages to Claude.ai and reading responses
"""

import asyncio
import json
import websockets
import requests
import time
from typing import Optional, Dict, Any


class ClaudeChatAutomation:
    def __init__(self, chrome_debug_port: int = 9222):
        self.chrome_debug_port = chrome_debug_port
        self.websocket = None
        self.tab_id = None
        
    async def connect_to_tab(self, tab_id: Optional[str] = None, ws_url: Optional[str] = None, url_contains: str = "claude.ai") -> bool:
        """Connect to a Chrome tab containing Claude chat interface"""
        try:
            # If WebSocket URL is provided directly, use it
            if ws_url:
                self.websocket = await websockets.connect(ws_url)
                await self._send_command("Runtime.enable")
                print(f"Connected directly to Claude via WebSocket")
                return True
            
            # Otherwise, get list of tabs and find the right one
            response = requests.get(f"http://localhost:{self.chrome_debug_port}/json")
            tabs = response.json()
            
            # Find the target tab
            target_tab = None
            if tab_id:
                target_tab = next((tab for tab in tabs if tab["id"] == tab_id), None)
            else:
                # Find tab by URL content
                target_tab = next((tab for tab in tabs if url_contains in tab["url"]), None)
            
            if not target_tab:
                print(f"No Claude tab found. Available tabs:")
                for tab in tabs:
                    print(f"  {tab['id']}: {tab['url']}")
                return False
            
            self.tab_id = target_tab["id"]
            ws_url = target_tab["webSocketDebuggerUrl"]
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(ws_url)
            
            # Enable Runtime domain
            await self._send_command("Runtime.enable")
            print(f"Connected to Claude tab: {target_tab['title']}")
            return True
            
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    async def _send_command(self, method: str, params: Dict = None) -> Dict[str, Any]:
        """Send a command to Chrome DevTools"""
        # Use a simple incrementing counter for message IDs
        if not hasattr(self, '_message_id'):
            self._message_id = 1
        else:
            self._message_id += 1
            
        command = {
            "id": self._message_id,
            "method": method,
            "params": params or {}
        }
        
        await self.websocket.send(json.dumps(command))
        
        # Keep receiving messages until we get the response to our command
        while True:
            response_text = await self.websocket.recv()
            response = json.loads(response_text)
            
            # Check if this is a response to our command (has matching ID)
            if "id" in response and response["id"] == self._message_id:
                return response
            
            # If it's an event notification (has "method" but no "id"), ignore it
            if "method" in response and "id" not in response:
                continue
            
            # If it's some other response, return it anyway
            return response
    
    async def execute_js(self, javascript_code: str) -> Any:
        """Execute JavaScript in the browser tab"""
        try:
            response = await self._send_command("Runtime.evaluate", {
                "expression": javascript_code,
                "returnByValue": True,
                "awaitPromise": True,
                "timeout": 10000
            })
            
            print(f"DevTools response: {json.dumps(response, indent=2)}")
            
            if "result" in response and "result" in response["result"]:
                result = response["result"]["result"]
                if "value" in result:
                    return result["value"]
                elif "unserializableValue" in result:
                    return result["unserializableValue"]
                elif result.get("type") == "undefined":
                    return "undefined"
                else:
                    print(f"Unexpected result format: {result}")
                    return None
            elif "exceptionDetails" in response:
                error_msg = response["exceptionDetails"].get("exception", {}).get("description", "Unknown error")
                raise Exception(f"JavaScript error: {error_msg}")
            else:
                print(f"Unexpected response format: {response}")
                return None
                
        except Exception as e:
            print(f"Error executing JavaScript: {e}")
            raise
    
    async def send_message(self, message: str) -> bool:
        """Send a message to Claude chat interface"""
        # Escape the message properly for JavaScript
        escaped_message = message.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        
        js_code = f"""
        (async function() {{
            try {{
                console.log("Starting message send process...");
                
                // Multiple strategies to find the input field
                let input = null;
                
                // Strategy 1: Look for contenteditable div (most common for Claude)
                const contentEditableSelectors = [
                    'div[contenteditable="true"]',
                    '[contenteditable="true"]',
                    'div[role="textbox"]',
                    'div[data-testid*="input"]',
                    'div[data-testid*="message"]'
                ];
                
                for (const selector of contentEditableSelectors) {{
                    input = document.querySelector(selector);
                    if (input) {{
                        console.log("Found input with selector:", selector);
                        break;
                    }}
                }}
                
                // Strategy 2: Look for textarea with specific attributes
                if (!input) {{
                    const textareaSelectors = [
                        'textarea[placeholder*="How can I help"]',
                        'textarea[placeholder*="Message"]',
                        'textarea[placeholder*="Ask Claude"]',
                        'textarea[data-testid*="message"]',
                        'textarea[id*="message"]',
                        'textarea'
                    ];
                    
                    for (const selector of textareaSelectors) {{
                        input = document.querySelector(selector);
                        if (input) {{
                            console.log("Found textarea with selector:", selector);
                            break;
                        }}
                    }}
                }}
                
                if (!input) {{
                    const availableInputs = {{
                        textareas: document.querySelectorAll('textarea').length,
                        contentEditable: document.querySelectorAll('[contenteditable="true"]').length,
                        textboxes: document.querySelectorAll('[role="textbox"]').length
                    }};
                    return "Input field not found. Available: " + JSON.stringify(availableInputs);
                }}
                
                console.log("Found input element:", input.tagName, input.className);
                
                // Set focus on the input
                input.focus();
                await new Promise(resolve => setTimeout(resolve, 100));
                
                // Clear existing content and set new message
                if (input.tagName === 'TEXTAREA') {{
                    input.value = '';
                    input.value = "{escaped_message}";
                    
                    // Trigger events
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    input.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true }}));
                }} else {{
                    // For contenteditable div
                    input.innerHTML = '';
                    input.innerText = "{escaped_message}";
                    
                    // Trigger events
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    input.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true }}));
                }}
                
                console.log("Message set in input field");
                
                // Wait a moment then find and click send button
                await new Promise(resolve => setTimeout(resolve, 500));
                
                let sendButton = null;
                
                // Multiple strategies to find send button
                const buttonSelectors = [
                    'button[type="submit"]',
                    'button[aria-label*="Send" i]',
                    'button[data-testid*="send" i]',
                    'button[title*="Send" i]',
                    'button[data-testid*="submit" i]'
                ];
                
                for (const selector of buttonSelectors) {{
                    sendButton = document.querySelector(selector);
                    if (sendButton && !sendButton.disabled) {{
                        console.log("Found send button with selector:", selector);
                        break;
                    }}
                }}
                
                // Look for button with send icon (SVG)
                if (!sendButton) {{
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {{
                        if (btn.disabled) continue;
                        
                        const svg = btn.querySelector('svg');
                        const ariaLabel = btn.getAttribute('aria-label')?.toLowerCase() || '';
                        const buttonText = btn.innerText?.toLowerCase() || '';
                        
                        if (svg && (
                            svg.innerHTML.includes('M2.01') || // Common send icon path
                            svg.innerHTML.includes('send') ||
                            ariaLabel.includes('send') ||
                            buttonText.includes('send')
                        )) {{
                            sendButton = btn;
                            console.log("Found send button with SVG icon");
                            break;
                        }}
                    }}
                }}
                
                // Look for any small button near the input (likely send button)
                if (!sendButton) {{
                    const buttons = Array.from(document.querySelectorAll('button'));
                    sendButton = buttons.find(btn => {{
                        if (btn.disabled) return false;
                        const rect = btn.getBoundingClientRect();
                        return rect.width < 100 && rect.height < 100 && rect.width > 20 && rect.height > 20;
                    }});
                    if (sendButton) {{
                        console.log("Found send button by size heuristic");
                    }}
                }}
                
                if (sendButton && !sendButton.disabled) {{
                    console.log("Clicking send button...");
                    sendButton.click();
                    return "Message sent successfully";
                }} else {{
                    const buttonInfo = Array.from(document.querySelectorAll('button')).map(btn => ({{
                        text: btn.innerText?.substring(0, 20) || 'No text',
                        disabled: btn.disabled,
                        ariaLabel: btn.getAttribute('aria-label') || 'No label',
                        type: btn.type || 'No type'
                    }}));
                    return "Send button not found or disabled. Available buttons: " + JSON.stringify(buttonInfo);
                }}
                
            }} catch (error) {{
                console.error("Error in send_message:", error);
                return "Error: " + error.message;
            }}
        }})();
        """
        
        try:
            result = await self.execute_js(js_code)
            print(f"Send result: {result}")
            return "sent" in str(result).lower() if result else False
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    async def wait_for_response(self, timeout: int = 30) -> str:
        """Wait for and get the latest Claude response"""
        js_code = """
        (function() {
            // Function to get the latest Claude response
            function getLatestResponse() {
                // More comprehensive Claude-specific selectors
                const messageSelectors = [
                    // Modern Claude selectors
                    'div[data-is-streaming="false"] div[data-testid="conversation-turn-content"]',
                    '[data-testid="conversation-turn-content"]:last-child',
                    'div[data-testid="conversation-turn-content"]',
                    
                    // Prose/content selectors
                    'div[class*="prose"] p',
                    'div[class*="prose"]',
                    '.prose p',
                    '.prose',
                    
                    // General message selectors
                    '.conversation-turn:last-child [data-testid="conversation-turn-content"]',
                    '.message:last-child .text-base',
                    '.message:last-child',
                    
                    // Fallback selectors
                    'div[role="presentation"] div[class*="break-words"]',
                    'div[class*="break-words"]:not([contenteditable])',
                    'div[class*="ProseMirror"]:not([contenteditable])'
                ];
                
                console.log("Searching for Claude response...");
                
                for (const selector of messageSelectors) {
                    const elements = document.querySelectorAll(selector);
                    console.log(`Selector "${selector}" found ${elements.length} elements`);
                    
                    if (elements.length > 0) {
                        // Try to get the last element that looks like a response
                        for (let i = elements.length - 1; i >= 0; i--) {
                            const element = elements[i];
                            const text = element.innerText || element.textContent;
                            
                            if (text && text.trim().length > 10) {
                                // Skip if it looks like user input
                                if (element.getAttribute('contenteditable') === 'true') {
                                    continue;
                                }
                                
                                console.log(`Found response with selector "${selector}": ${text.substring(0, 50)}...`);
                                return text.trim();
                            }
                        }
                    }
                }
                
                // Last resort: look for any div with substantial text content
                const allDivs = document.querySelectorAll('div');
                for (let i = allDivs.length - 1; i >= 0; i--) {
                    const div = allDivs[i];
                    if (div.getAttribute('contenteditable') === 'true') continue;
                    
                    const text = div.innerText || div.textContent;
                    if (text && text.trim().length > 50 && 
                        !text.includes('Send message') && 
                        !text.includes('Sidebar') &&
                        !text.includes('More options')) {
                        
                        // Check if this div contains mostly text (not UI elements)
                        const childButtons = div.querySelectorAll('button').length;
                        const childInputs = div.querySelectorAll('input, textarea').length;
                        
                        if (childButtons < 3 && childInputs === 0) {
                            console.log(`Found response via fallback: ${text.substring(0, 50)}...`);
                            return text.trim();
                        }
                    }
                }
                
                console.log("No response found");
                return null;
            }
            
            return getLatestResponse();
        })();
        """
        
        start_time = time.time()
        last_response = ""
        
        while time.time() - start_time < timeout:
            try:
                response = await self.execute_js(js_code)
                if response and response != last_response and len(response) > 10:
                    # Check if response seems complete (not streaming)
                    await asyncio.sleep(2)  # Wait a bit more
                    final_response = await self.execute_js(js_code)
                    if final_response == response:  # Response hasn't changed
                        return final_response
                    last_response = final_response
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error checking response: {e}")
                await asyncio.sleep(1)
        
        return last_response if last_response else "No response received within timeout"
    
    async def send_and_wait(self, message: str, timeout: int = 30) -> str:
        """Send a message and wait for response"""
        print(f"Sending: {message}")
        
        success = await self.send_message(message)
        
        if not success:
            return "Failed to send message"
        
        print("Waiting for response...")
        response = await self.wait_for_response(timeout)
        print(f"Response: {response[:200]}..." if len(response) > 200 else f"Response: {response}")
        return response
    
    async def debug_page_elements(self) -> str:
        """Debug function to see what elements are available on the page"""
        js_code = """
        (function() {
            const info = {
                textareas: Array.from(document.querySelectorAll('textarea')).map(el => ({
                    tag: el.tagName,
                    placeholder: el.placeholder,
                    id: el.id,
                    className: el.className
                })),
                contentEditable: Array.from(document.querySelectorAll('[contenteditable="true"]')).map(el => ({
                    tag: el.tagName,
                    className: el.className,
                    id: el.id
                })),
                buttons: Array.from(document.querySelectorAll('button')).map(el => ({
                    text: el.innerText?.substring(0, 20),
                    ariaLabel: el.getAttribute('aria-label'),
                    type: el.type,
                    disabled: el.disabled
                })),
                url: window.location.href
            };
            return JSON.stringify(info, null, 2);
        })();
        """
        
        try:
            result = await self.execute_js(js_code)
            return result
        except Exception as e:
            return f"Debug error: {e}"
    
    async def close(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()


async def main():
    # Initialize Claude automation
    chat = ClaudeChatAutomation()
    
    try:
        # First, get current tabs to find the right Claude tab
        print("Getting current Chrome tabs...")
        response = requests.get(f"http://localhost:9222/json")
        tabs = response.json()
        
        # Print available tabs for debugging
        print("Available tabs:")
        for tab in tabs:
            if tab.get('type') == 'page':  # Only show actual pages, not workers
                print(f"  ID: {tab['id']}")
                print(f"  Title: {tab.get('title', 'No title')}")
                print(f"  URL: {tab.get('url', 'No URL')}")
                print(f"  WebSocket: {tab.get('webSocketDebuggerUrl', 'No WebSocket')}")
                print()
        
        # Try to connect to Claude tab
        if await chat.connect_to_tab(url_contains="claude.ai"):
            
            # First, let's debug what elements are available
            print("=== DEBUG INFO ===")
            debug_info = await chat.debug_page_elements()
            print(debug_info)
            print("=== END DEBUG ===\n")
            
            # Send a message and get response
            response = await chat.send_and_wait(
                "Hello! Can you tell me a short joke?"
            )
            
            print(f"\nFinal response:\n{response}")
            
            # Wait a bit between messages
            await asyncio.sleep(3)
            
            # Send another message
            response2 = await chat.send_and_wait(
                "What's 2+2?"
            )
            
            print(f"\nSecond response:\n{response2}")
            
        else:
            print("Could not find Claude tab. Make sure Claude.ai is open in Chrome with debugging enabled.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await chat.close()


if __name__ == "__main__":
    # Make sure Chrome is running with: chrome --remote-debugging-port=9222
    asyncio.run(main())
