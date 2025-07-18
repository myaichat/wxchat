"""
Simple Claude Chat Test - Minimal version to test basic functionality
"""

import asyncio
import json
import websockets
import requests
import time


class SimpleClaudeTest:
    def __init__(self, chrome_debug_port: int = 9222):
        self.chrome_debug_port = chrome_debug_port
        self.websocket = None
        self._message_id = 0
        
    async def connect_to_claude(self):
        """Connect to Claude tab"""
        try:
            response = requests.get(f"http://localhost:{self.chrome_debug_port}/json")
            tabs = response.json()
            
            claude_tab = next((tab for tab in tabs if "claude.ai" in tab["url"]), None)
            if not claude_tab:
                print("No Claude tab found")
                return False
            
            self.websocket = await websockets.connect(claude_tab["webSocketDebuggerUrl"])
            await self._send_command("Runtime.enable")
            print(f"Connected to: {claude_tab['title']}")
            return True
            
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    async def _send_command(self, method: str, params: dict = None):
        """Send command to Chrome DevTools"""
        self._message_id += 1
        command = {
            "id": self._message_id,
            "method": method,
            "params": params or {}
        }
        
        await self.websocket.send(json.dumps(command))
        
        while True:
            response_text = await self.websocket.recv()
            response = json.loads(response_text)
            
            if "id" in response and response["id"] == self._message_id:
                return response
            if "method" in response and "id" not in response:
                continue
            return response
    
    async def execute_js(self, js_code: str):
        """Execute JavaScript"""
        try:
            response = await self._send_command("Runtime.evaluate", {
                "expression": js_code,
                "returnByValue": True,
                "timeout": 5000
            })
            
            if "result" in response and "result" in response["result"]:
                result = response["result"]["result"]
                return result.get("value")
            return None
            
        except Exception as e:
            print(f"JS execution error: {e}")
            return None
    
    async def send_message(self, message: str):
        """Send message to Claude"""
        escaped_msg = message.replace('"', '\\"').replace('\n', '\\n')
        
        js_code = f'''
        (function() {{
            try {{
                // Find the main input field
                let input = document.querySelector('div[contenteditable="true"]');
                
                if (!input) {{
                    input = document.querySelector('textarea');
                }}
                
                if (!input) return "No input found";
                
                // Clear and set message
                input.focus();
                
                if (input.tagName === 'TEXTAREA') {{
                    input.value = "{escaped_msg}";
                    input.dispatchEvent(new Event('input', {{bubbles: true}}));
                }} else {{
                    input.innerText = "{escaped_msg}";
                    input.dispatchEvent(new Event('input', {{bubbles: true}}));
                }}
                
                // Find send button
                const buttons = document.querySelectorAll('button:not([disabled])');
                const inputRect = input.getBoundingClientRect();
                
                let sendButton = null;
                
                // Look for button with send attributes
                for (const btn of buttons) {{
                    const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                    if (ariaLabel.includes('send') || btn.type === 'submit') {{
                        sendButton = btn;
                        break;
                    }}
                }}
                
                // Look for button with SVG near input
                if (!sendButton) {{
                    for (const btn of buttons) {{
                        const btnRect = btn.getBoundingClientRect();
                        const svg = btn.querySelector('svg');
                        
                        if (svg && btnRect.left > inputRect.right - 150 && 
                            Math.abs(btnRect.top - inputRect.top) < 100) {{
                            sendButton = btn;
                            break;
                        }}
                    }}
                }}
                
                if (sendButton) {{
                    sendButton.click();
                    return "Message sent successfully";
                }} else {{
                    // Try Enter key
                    const enterEvent = new KeyboardEvent('keydown', {{
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        bubbles: true
                    }});
                    input.dispatchEvent(enterEvent);
                    return "Tried Enter key";
                }}
                
            }} catch (error) {{
                return "Error: " + error.message;
            }}
        }})();
        '''
        
        result = await self.execute_js(js_code)
        print(f"Send result: {result}")
        return result and ("sent" in str(result).lower() or "enter" in str(result).lower())
    
    async def get_response(self):
        """Get Claude's response"""
        js_code = '''
        (function() {
            try {
                // Try to find conversation turns
                let turns = document.querySelectorAll('[data-testid="conversation-turn"]');
                
                if (turns.length === 0) {
                    turns = document.querySelectorAll('.conversation-turn');
                }
                
                if (turns.length === 0) {
                    turns = document.querySelectorAll('div[class*="prose"]');
                }
                
                if (turns.length > 0) {
                    const lastTurn = turns[turns.length - 1];
                    
                    // Look for actual content within the turn
                    const contentSelectors = [
                        'p',
                        'div[class*="prose"] p',
                        '[data-testid="conversation-turn-content"] p',
                        '[data-testid="conversation-turn-content"] div'
                    ];
                    
                    let bestResponse = '';
                    
                    for (const selector of contentSelectors) {
                        const elements = lastTurn.querySelectorAll(selector);
                        for (const element of elements) {
                            if (element.getAttribute('contenteditable') === 'true') continue;
                            
                            const text = element.innerText || element.textContent || '';
                            const trimmed = text.trim();
                            
                            // Skip CSS, UI text, and other non-content
                            if (trimmed.length < 10 ||
                                trimmed.includes('@keyframes') ||
                                trimmed.includes('rgba(') ||
                                trimmed.includes('transform:') ||
                                trimmed.includes('opacity:') ||
                                trimmed.includes('Send message') ||
                                trimmed.includes('More options') ||
                                trimmed.includes('Sidebar') ||
                                trimmed.includes('intercom-') ||
                                trimmed.startsWith('.') ||
                                trimmed.startsWith('#') ||
                                trimmed.includes('{') ||
                                trimmed.includes('}')) continue;
                            
                            if (trimmed.length > bestResponse.length) {
                                bestResponse = trimmed;
                            }
                        }
                    }
                    
                    if (bestResponse) {
                        return bestResponse;
                    }
                }
                
                // Fallback: look for meaningful text content that's not CSS/UI
                const allElements = document.querySelectorAll('p, div, span');
                const candidates = [];
                
                for (const element of allElements) {
                    if (element.getAttribute('contenteditable') === 'true') continue;
                    if (element.querySelector('input') || element.querySelector('textarea')) continue;
                    
                    const text = element.innerText || element.textContent || '';
                    const trimmed = text.trim();
                    
                    // Filter out CSS, UI elements, and other non-content
                    if (trimmed.length > 20 &&
                        !trimmed.includes('@keyframes') &&
                        !trimmed.includes('rgba(') &&
                        !trimmed.includes('transform:') &&
                        !trimmed.includes('opacity:') &&
                        !trimmed.includes('Send message') &&
                        !trimmed.includes('More options') &&
                        !trimmed.includes('Sidebar') &&
                        !trimmed.includes('intercom-') &&
                        !trimmed.startsWith('.') &&
                        !trimmed.startsWith('#') &&
                        !trimmed.includes('{') &&
                        !trimmed.includes('}') &&
                        !trimmed.includes('px') &&
                        !trimmed.includes('rem') &&
                        !trimmed.includes('vh') &&
                        !trimmed.includes('vw')) {
                        
                        // Check if this looks like actual conversation content
                        if (trimmed.match(/[.!?]/) && // Has sentence endings
                            !trimmed.match(/^[A-Z_]+$/) && // Not all caps (likely constants)
                            trimmed.split(' ').length > 3) { // Has multiple words
                            candidates.push(trimmed);
                        }
                    }
                }
                
                if (candidates.length > 0) {
                    // Return the longest candidate that looks like a response
                    const best = candidates.reduce((a, b) => a.length > b.length ? a : b);
                    return "Found response: " + best.substring(0, 300);
                }
                
                return "No Claude response found";
                
            } catch (error) {
                return "Error getting response: " + error.message;
            }
        })();
        '''
        
        return await self.execute_js(js_code)
    
    async def test_conversation(self):
        """Test sending a message and getting response"""
        print("\\n=== Testing Claude Conversation ===")
        
        # Send message
        message = "Hello! Can you tell me a short joke?"
        print(f"Sending: {message}")
        
        if not await self.send_message(message):
            print("Failed to send message")
            return
        
        # Wait for response
        print("Waiting for response...")
        await asyncio.sleep(5)  # Give Claude time to respond
        
        # Get response
        response = await self.get_response()
        print(f"Response: {response}")
        
        # Test second message
        print("\\n--- Second message ---")
        message2 = "What's 2+2?"
        print(f"Sending: {message2}")
        
        await asyncio.sleep(2)  # Wait between messages
        
        if await self.send_message(message2):
            await asyncio.sleep(5)
            response2 = await self.get_response()
            print(f"Response: {response2}")
    
    async def close(self):
        """Close connection"""
        if self.websocket:
            await self.websocket.close()


async def main():
    test = SimpleClaudeTest()
    
    try:
        if await test.connect_to_claude():
            await test.test_conversation()
        else:
            print("Could not connect to Claude. Make sure Claude.ai is open in Chrome with debugging enabled.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await test.close()


if __name__ == "__main__":
    asyncio.run(main())
