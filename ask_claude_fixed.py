"""
Claude Chat Automation via Chrome DevTools Protocol
Automates sending messages to Claude.ai and reading responses
FIXED VERSION - Improved response capture
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
        self.last_message_count = 0
        
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
            
            # Initialize message count
            await self._update_message_count()
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
                "timeout": 15000
            })
            
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
    
    async def _update_message_count(self):
        """Update the count of messages in the conversation"""
        js_code = """
        (function() {
            // Count all message containers
            const messageSelectors = [
                '[data-testid="conversation-turn"]',
                '.conversation-turn',
                '[data-testid*="message"]',
                '.message',
                'div[class*="prose"]'
            ];
            
            let maxCount = 0;
            for (const selector of messageSelectors) {
                const count = document.querySelectorAll(selector).length;
                maxCount = Math.max(maxCount, count);
            }
            
            return maxCount;
        })();
        """
        
        try:
            count = await self.execute_js(js_code)
            self.last_message_count = count if count else 0
        except:
            self.last_message_count = 0
    
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
                    'div[data-testid*="message"]',
                    'div[data-testid*="composer"]'
                ];
                
                for (const selector of contentEditableSelectors) {{
                    const elements = document.querySelectorAll(selector);
                    for (const el of elements) {{
                        // Check if this is likely the main input (not a search box or other input)
                        const rect = el.getBoundingClientRect();
                        if (rect.height > 15 && rect.width > 200) {{
                            input = el;
                            console.log("Found input with selector:", selector);
                            break;
                        }}
                    }}
                    if (input) break;
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
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {{
                            const rect = el.getBoundingClientRect();
                            if (rect.height > 15 && rect.width > 200) {{
                                input = el;
                                console.log("Found textarea with selector:", selector);
                                break;
                            }}
                        }}
                        if (input) break;
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
                await new Promise(resolve => setTimeout(resolve, 200));
                
                // Clear existing content and set new message
                if (input.tagName === 'TEXTAREA') {{
                    input.value = '';
                    input.value = "{escaped_message}";
                    
                    // Trigger events
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }} else {{
                    // For contenteditable div
                    input.innerHTML = '';
                    input.innerText = "{escaped_message}";
                    
                    // Trigger events
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                
                console.log("Message set in input field");
                
                // Wait a moment then find and click send button
                await new Promise(resolve => setTimeout(resolve, 800));
                
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
                    const buttons = document.querySelectorAll(selector);
                    for (const btn of buttons) {{
                        if (!btn.disabled) {{
                            sendButton = btn;
                            console.log("Found send button with selector:", selector);
                            break;
                        }}
                    }}
                    if (sendButton) break;
                }}
                
                // Look for button with send icon (SVG) or near the input
                if (!sendButton) {{
                    const buttons = document.querySelectorAll('button');
                    console.log(`Checking ${{buttons.length}} buttons for send button...`);
                    
                    for (const btn of buttons) {{
                        if (btn.disabled) continue;
                        
                        const svg = btn.querySelector('svg');
                        const ariaLabel = btn.getAttribute('aria-label')?.toLowerCase() || '';
                        const buttonText = btn.innerText?.toLowerCase() || '';
                        const btnRect = btn.getBoundingClientRect();
                        
                        console.log(`Button: text="${{buttonText}}", ariaLabel="${{ariaLabel}}", hasSVG=${{!!svg}}, rect=${{JSON.stringify(btnRect)}}`);
                        
                        // Check for send-related content
                        if (svg && (
                            svg.innerHTML.includes('M2.01') || // Common send icon path
                            svg.innerHTML.includes('send') ||
                            ariaLabel.includes('send') ||
                            buttonText.includes('send') ||
                            svg.innerHTML.includes('path') // Generic SVG path
                        )) {{
                            sendButton = btn;
                            console.log("Found send button with SVG icon");
                            break;
                        }}
                        
                        // Check if button is near the input field (right side)
                        const inputRect = input.getBoundingClientRect();
                        const isNearInput = (
                            btnRect.left >= inputRect.right - 50 && // Within 50px of input right edge
                            btnRect.left <= inputRect.right + 100 && // Not too far right
                            Math.abs(btnRect.top - inputRect.top) < 50 && // Similar vertical position
                            btnRect.width > 20 && btnRect.width < 100 && // Reasonable button size
                            btnRect.height > 20 && btnRect.height < 100
                        );
                        
                        if (isNearInput) {{
                            sendButton = btn;
                            console.log("Found send button by proximity to input");
                            break;
                        }}
                        
                        // Check for small square buttons (likely icon buttons)
                        if (btnRect.width > 20 && btnRect.width < 60 && 
                            btnRect.height > 20 && btnRect.height < 60 &&
                            Math.abs(btnRect.width - btnRect.height) < 10) {{ // Nearly square
                            
                            // Check if it's positioned after the input
                            if (btnRect.left > inputRect.right - 100) {{
                                sendButton = btn;
                                console.log("Found send button by square icon heuristic");
                                break;
                            }}
                        }}
                    }}
                }}
                
                if (sendButton && !sendButton.disabled) {{
                    console.log("Clicking send button...");
                    sendButton.click();
                    return "Message sent successfully";
                }} else {{
                    const buttonInfo = Array.from(document.querySelectorAll('button')).slice(0, 10).map(btn => ({{
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
    
    async def wait_for_response(self, timeout: int = 45) -> str:
        """Wait for and get the latest Claude response using improved detection"""
        
        # First wait for streaming to complete
        await self._wait_for_streaming_complete(timeout // 2)
        
        # Then get the complete response with simplified JavaScript
        js_code = """
        (function() {
            try {
                console.log("Starting response capture...");
                
                // Get all conversation turns
                var conversationTurns = document.querySelectorAll('[data-testid="conversation-turn"]');
                console.log("Found " + conversationTurns.length + " conversation turns");
                
                if (conversationTurns.length === 0) {
                    return null;
                }
                
                // Get the last turn (should be Claude's response)
                var lastTurn = conversationTurns[conversationTurns.length - 1];
                
                // Try different selectors to find the response content
                var selectors = [
                    '[data-testid="conversation-turn-content"]',
                    '.prose',
                    'div[class*="prose"]',
                    'div[class*="break-words"]',
                    'p'
                ];
                
                var bestResponse = '';
                
                for (var i = 0; i < selectors.length; i++) {
                    var elements = lastTurn.querySelectorAll(selectors[i]);
                    console.log("Selector " + selectors[i] + " found " + elements.length + " elements");
                    
                    for (var j = 0; j < elements.length; j++) {
                        var element = elements[j];
                        
                        // Skip input elements
                        if (element.getAttribute('contenteditable') === 'true') continue;
                        
                        var text = element.innerText || element.textContent || '';
                        text = text.trim();
                        
                        // Skip very short text
                        if (text.length < 10) continue;
                        
                        // Skip UI text
                        if (text.indexOf('Send message') >= 0 || 
                            text.indexOf('More options') >= 0 ||
                            text.indexOf('Sidebar') >= 0 ||
                            text.indexOf('New chat') >= 0 ||
                            text.indexOf('I notice the user') >= 0 ||
                            text.indexOf('The user is') >= 0 ||
                            text.indexOf('thinking process') >= 0 ||
                            text.indexOf('@keyframes') >= 0 ||
                            text.indexOf('rgba(') >= 0) continue;
                        
                        // Use the longest meaningful text
                        if (text.length > bestResponse.length) {
                            bestResponse = text;
                            console.log("Found better response: " + text.substring(0, 50) + "...");
                        }
                    }
                }
                
                if (bestResponse && bestResponse.length > 10) {
                    console.log("Final response: " + bestResponse.substring(0, 100) + "...");
                    return bestResponse;
                }
                
                // Fallback: get all text from last turn and clean it
                var allText = lastTurn.innerText || lastTurn.textContent || '';
                var lines = allText.split('\\n');
                var cleanLines = [];
                
                for (var k = 0; k < lines.length; k++) {
                    var line = lines[k].trim();
                    if (line.length > 5 && 
                        line.indexOf('Send message') < 0 &&
                        line.indexOf('More options') < 0 &&
                        line.indexOf('Sidebar') < 0 &&
                        line.indexOf('New chat') < 0 &&
                        line.indexOf('thinking process') < 0 &&
                        line.indexOf('@keyframes') < 0) {
                        cleanLines.push(line);
                    }
                }
                
                if (cleanLines.length > 0) {
                    var result = cleanLines.join(' ').trim();
                    console.log("Fallback response: " + result.substring(0, 100) + "...");
                    return result;
                }
                
                console.log("No response found");
                return null;
                
            } catch (error) {
                console.error("Error in response capture: " + error.message);
                return null;
            }
        })();
        """
        
        start_time = time.time()
        last_response = ""
        stable_count = 0
        
        while time.time() - start_time < timeout:
            try:
                response = await self.execute_js(js_code)
                
                if response and len(response) > 10:
                    if response == last_response:
                        stable_count += 1
                        if stable_count >= 2:  # Response has been stable for 2 checks
                            return response
                    else:
                        stable_count = 0
                        last_response = response
                        print(f"Response updated: {response[:100]}...")
                
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"Error checking response: {e}")
                await asyncio.sleep(3)
        
        return last_response if last_response else "No response received within timeout"
    
    async def _wait_for_streaming_complete(self, timeout: int = 20):
        """Wait for Claude to finish streaming its response"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                is_streaming = await self.execute_js("""
                (function() {
                    // Check if there are any streaming indicators
                    const streamingElements = document.querySelectorAll('[data-is-streaming="true"]');
                    const loadingElements = document.querySelectorAll('[data-testid*="loading"]');
                    const thinkingElements = document.querySelectorAll('[data-testid*="thinking"]');
                    
                    return streamingElements.length > 0 || loadingElements.length > 0 || thinkingElements.length > 0;
                })();
                """)
                
                if not is_streaming:
                    print("Streaming completed")
                    await asyncio.sleep(2)  # Wait a bit more for content to settle
                    return
                
                print("Still streaming...")
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Error checking streaming status: {e}")
                await asyncio.sleep(2)
        
        print("Streaming timeout reached")
    
    async def _wait_for_new_message(self, timeout: int = 15):
        """Wait for a new message to appear in the conversation"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_count = await self.execute_js("""
                (function() {
                    const messageSelectors = [
                        '[data-testid="conversation-turn"]',
                        '.conversation-turn',
                        'div[class*="prose"]'
                    ];
                    
                    let maxCount = 0;
                    for (const selector of messageSelectors) {
                        const count = document.querySelectorAll(selector).length;
                        maxCount = Math.max(maxCount, count);
                    }
                    
                    return maxCount;
                })();
                """)
                
                if current_count and current_count > self.last_message_count:
                    print(f"New message detected! Count: {self.last_message_count} -> {current_count}")
                    self.last_message_count = current_count
                    await asyncio.sleep(2)  # Wait for message to fully load
                    return
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error waiting for new message: {e}")
                await asyncio.sleep(1)
    
    async def send_and_wait(self, message: str, timeout: int = 45) -> str:
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
                url: window.location.href,
                textareas: Array.from(document.querySelectorAll('textarea')).map(el => ({
                    tag: el.tagName,
                    placeholder: el.placeholder,
                    id: el.id,
                    className: el.className,
                    rect: el.getBoundingClientRect()
                })),
                contentEditable: Array.from(document.querySelectorAll('[contenteditable="true"]')).map(el => ({
                    tag: el.tagName,
                    className: el.className,
                    id: el.id,
                    rect: el.getBoundingClientRect()
                })),
                buttons: Array.from(document.querySelectorAll('button')).slice(0, 15).map(el => ({
                    text: el.innerText?.substring(0, 30),
                    ariaLabel: el.getAttribute('aria-label'),
                    type: el.type,
                    disabled: el.disabled,
                    className: el.className
                })),
                conversationTurns: document.querySelectorAll('[data-testid="conversation-turn"]').length,
                proseElements: document.querySelectorAll('div[class*="prose"]').length,
                messageElements: document.querySelectorAll('[data-testid*="message"]').length
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
