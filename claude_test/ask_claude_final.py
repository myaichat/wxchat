"""
Claude Chat Automation via Chrome DevTools Protocol
FINAL VERSION - Simplified and robust response capture
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
        
    async def connect_to_tab(self, url_contains: str = "claude.ai") -> bool:
        """Connect to a Chrome tab containing Claude chat interface"""
        try:
            response = requests.get(f"http://localhost:{self.chrome_debug_port}/json")
            tabs = response.json()
            
            # Find Claude tab
            target_tab = next((tab for tab in tabs if url_contains in tab["url"]), None)
            
            if not target_tab:
                print(f"No Claude tab found. Available tabs:")
                for tab in tabs:
                    if tab.get('type') == 'page':
                        print(f"  {tab['id']}: {tab['url']}")
                return False
            
            self.tab_id = target_tab["id"]
            ws_url = target_tab["webSocketDebuggerUrl"]
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(ws_url)
            await self._send_command("Runtime.enable")
            print(f"Connected to Claude tab: {target_tab['title']}")
            return True
            
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    async def _send_command(self, method: str, params: Dict = None) -> Dict[str, Any]:
        """Send a command to Chrome DevTools"""
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
        
        # Wait for response
        while True:
            response_text = await self.websocket.recv()
            response = json.loads(response_text)
            
            if "id" in response and response["id"] == self._message_id:
                return response
            
            if "method" in response and "id" not in response:
                continue
            
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
            
            if "result" in response and "result" in response["result"]:
                result = response["result"]["result"]
                if "value" in result:
                    return result["value"]
                elif result.get("type") == "undefined":
                    return None
                else:
                    return None
            elif "exceptionDetails" in response:
                error_msg = response["exceptionDetails"].get("exception", {}).get("description", "Unknown error")
                print(f"JavaScript error: {error_msg}")
                return None
            else:
                return None
                
        except Exception as e:
            print(f"Error executing JavaScript: {e}")
            return None
    
    async def send_message(self, message: str) -> bool:
        """Send a message to Claude chat interface"""
        escaped_message = message.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        
        js_code = f'''
        (async function() {{
            try {{
                // Find input field
                let input = document.querySelector('div[contenteditable="true"]');
                if (!input) {{
                    input = document.querySelector('textarea');
                }}
                
                if (!input) {{
                    return "No input field found";
                }}
                
                // Set message
                input.focus();
                await new Promise(resolve => setTimeout(resolve, 100));
                
                if (input.tagName === 'TEXTAREA') {{
                    input.value = "{escaped_message}";
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else {{
                    input.innerText = "{escaped_message}";
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Find and click send button
                let sendButton = null;
                const buttons = document.querySelectorAll('button');
                
                for (const btn of buttons) {{
                    if (btn.disabled) continue;
                    
                    const svg = btn.querySelector('svg');
                    const rect = btn.getBoundingClientRect();
                    const inputRect = input.getBoundingClientRect();
                    
                    // Look for button near input with SVG (likely send button)
                    if (svg && rect.left > inputRect.right - 100 && 
                        Math.abs(rect.top - inputRect.top) < 50) {{
                        sendButton = btn;
                        break;
                    }}
                }}
                
                if (sendButton) {{
                    sendButton.click();
                    return "Message sent successfully";
                }} else {{
                    return "Send button not found";
                }}
                
            }} catch (error) {{
                return "Error: " + error.message;
            }}
        }})();
        '''
        
        result = await self.execute_js(js_code)
        print(f"Send result: {result}")
        return result and "sent" in str(result).lower()
    
    async def get_latest_response(self) -> str:
        """Get the latest Claude response"""
        js_code = '''
        (function() {
            try {
                // Get all conversation turns
                const turns = document.querySelectorAll('[data-testid="conversation-turn"]');
                if (turns.length === 0) return null;
                
                // Get the last turn (Claude's response)
                const lastTurn = turns[turns.length - 1];
                
                // Try to find response content
                let responseText = '';
                
                // Try different selectors
                const selectors = [
                    '[data-testid="conversation-turn-content"] p',
                    '[data-testid="conversation-turn-content"] div',
                    '.prose p',
                    'div[class*="prose"] p',
                    'p'
                ];
                
                for (const selector of selectors) {
                    const elements = lastTurn.querySelectorAll(selector);
                    for (const element of elements) {
                        if (element.getAttribute('contenteditable') === 'true') continue;
                        
                        const text = element.innerText || element.textContent || '';
                        if (text.trim().length > responseText.length) {
                            responseText = text.trim();
                        }
                    }
                    if (responseText.length > 20) break;
                }
                
                // Fallback: get all text from last turn
                if (!responseText || responseText.length < 10) {
                    const allText = lastTurn.innerText || lastTurn.textContent || '';
                    const lines = allText.split('\\n').filter(line => {
                        const trimmed = line.trim();
                        return trimmed.length > 5 && 
                               !trimmed.includes('Send message') &&
                               !trimmed.includes('More options') &&
                               !trimmed.includes('Sidebar');
                    });
                    
                    if (lines.length > 0) {
                        responseText = lines.join(' ').trim();
                    }
                }
                
                return responseText || null;
                
            } catch (error) {
                return null;
            }
        })();
        '''
        
        return await self.execute_js(js_code)
    
    async def wait_for_response(self, timeout: int = 30) -> str:
        """Wait for Claude's response with timeout"""
        print("Waiting for response...")
        
        start_time = time.time()
        last_response = ""
        stable_count = 0
        
        # Wait for streaming to complete first
        await asyncio.sleep(3)
        
        while time.time() - start_time < timeout:
            try:
                response = await self.get_latest_response()
                
                if response and len(response) > 10:
                    if response == last_response:
                        stable_count += 1
                        if stable_count >= 2:  # Response stable for 2 checks
                            return response
                    else:
                        stable_count = 0
                        last_response = response
                        print(f"Response updated: {response[:100]}...")
                
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Error checking response: {e}")
                await asyncio.sleep(2)
        
        return last_response if last_response else "No response received within timeout"
    
    async def send_and_wait(self, message: str, timeout: int = 30) -> str:
        """Send a message and wait for response"""
        print(f"Sending: {message}")
        
        success = await self.send_message(message)
        if not success:
            return "Failed to send message"
        
        response = await self.wait_for_response(timeout)
        return response
    
    async def close(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()


async def main():
    chat = ClaudeChatAutomation()
    
    try:
        if await chat.connect_to_tab():
            # Test with a simple joke request
            response1 = await chat.send_and_wait("Hello! Can you tell me a short joke?")
            print(f"\nFirst response:\n{response1}\n")
            
            # Wait between messages
            await asyncio.sleep(3)
            
            # Test with a math question
            response2 = await chat.send_and_wait("What's 2+2?")
            print(f"\nSecond response:\n{response2}\n")
            
        else:
            print("Could not connect to Claude tab. Make sure Claude.ai is open in Chrome with debugging enabled.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await chat.close()


if __name__ == "__main__":
    # Make sure Chrome is running with: chrome --remote-debugging-port=9222
    asyncio.run(main())
