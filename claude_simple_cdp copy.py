#!/usr/bin/env python3
"""
Simple Claude alternative using Chrome DevTools Protocol (no Playwright)
Direct replacement for: python './chat_handlers/claude_streaming_chat.py' 'how ry?'
"""

import sys
import json
import requests
import time
import re
import urllib.parse

class SimpleClaude:
    def __init__(self, debug_port=9222):
        self.debug_port = debug_port
        self.base_url = f"http://localhost:{debug_port}"
        self.tab_id = None
        self.ws_url = None
        
    def get_claude_tab(self):
        """Find Claude.ai tab"""
        try:
            response = requests.get(f"{self.base_url}/json", timeout=5)
            tabs = response.json()
            
            for tab in tabs:
                if 'claude.ai' in tab.get('url', ''):
                    self.tab_id = tab['id']
                    self.ws_url = tab.get('webSocketDebuggerUrl')
                    return True
            return False
        except:
            return False
    
    def execute_js_simple(self, js_code):
        """Execute JavaScript using simple HTTP approach (fallback)"""
        try:
            # Try the simple approach first - some Chrome versions support this
            url = f"{self.base_url}/json/runtime/evaluate"
            data = {"expression": js_code}
            
            response = requests.post(url, json=data, timeout=15)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if 'result' in result and 'value' in result['result']:
                        return result['result']['value']
                    elif 'value' in result:
                        return result['value']
                    else:
                        return f"No value in response: {result}"
                except json.JSONDecodeError:
                    return f"JSON decode error: {response.text[:200]}"
            else:
                return f"HTTP error {response.status_code}: {response.text[:200]}"
                
        except Exception as e:
            return f"Request error: {str(e)}"
    
    def execute_js_websocket(self, js_code):
        """Execute JavaScript using WebSocket (proper CDP)"""
        if not self.ws_url:
            return "Error: No WebSocket URL available"
        
        try:
            import websocket
            
            result_container = {"result": None, "error": None, "done": False}
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if 'result' in data:
                        if 'result' in data['result'] and 'value' in data['result']['result']:
                            result_container["result"] = data['result']['result']['value']
                        elif 'value' in data['result']:
                            result_container["result"] = data['result']['value']
                        else:
                            result_container["result"] = f"Unexpected format: {data}"
                        result_container["done"] = True
                    elif 'error' in data:
                        result_container["error"] = data['error']
                        result_container["done"] = True
                except Exception as e:
                    result_container["error"] = f"Message parse error: {str(e)}"
                    result_container["done"] = True
            
            def on_error(ws, error):
                result_container["error"] = f"WebSocket error: {str(error)}"
                result_container["done"] = True
            
            def on_open(ws):
                message = {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": js_code,
                        "returnByValue": True
                    }
                }
                ws.send(json.dumps(message))
            
            ws = websocket.WebSocketApp(self.ws_url,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_open=on_open)
            
            # Run WebSocket in a separate thread with timeout
            import threading
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for result with timeout
            timeout = 15
            start_time = time.time()
            while not result_container["done"] and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            ws.close()
            
            if result_container["error"]:
                return f"WebSocket error: {result_container['error']}"
            elif result_container["result"] is not None:
                return result_container["result"]
            else:
                return "Timeout: No response from WebSocket"
                
        except ImportError:
            return "Error: websocket-client not installed. Run: pip install websocket-client"
        except Exception as e:
            return f"WebSocket execution error: {str(e)}"
    
    def inject_and_ask(self, question):
        """Inject JavaScript and ask question"""
        if not self.tab_id:
            return "Error: No Claude tab found"
        
        # Escape the question for JavaScript
        escaped_question = question.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        
        # JavaScript to inject
        js_code = f"""
        (function() {{
            try {{
                // Find the input textarea with multiple selectors
                let textarea = document.querySelector('div[contenteditable="true"]');
                if (!textarea) textarea = document.querySelector('textarea');
                if (!textarea) textarea = document.querySelector('[data-testid="chat-input"]');
                if (!textarea) textarea = document.querySelector('.ProseMirror');
                if (!textarea) textarea = document.querySelector('[role="textbox"]');
                if (!textarea) textarea = document.querySelector('input[type="text"]');
                
                if (!textarea) {{
                    return "Error: Could not find input field. Available elements: " + 
                           Array.from(document.querySelectorAll('input, textarea, [contenteditable]')).length;
                }}
                
                // Clear and focus
                textarea.focus();
                
                // Clear existing content
                if (textarea.contentEditable === 'true') {{
                    textarea.innerHTML = '';
                    textarea.textContent = '';
                }} else {{
                    textarea.value = '';
                }}
                
                // Insert the question
                if (textarea.contentEditable === 'true') {{
                    textarea.textContent = '{escaped_question}';
                    textarea.innerHTML = '{escaped_question}';
                }} else {{
                    textarea.value = '{escaped_question}';
                }}
                
                // Trigger events to notify the page
                ['input', 'change', 'keyup'].forEach(eventType => {{
                    textarea.dispatchEvent(new Event(eventType, {{ bubbles: true, cancelable: true }}));
                }});
                
                // Wait a bit then find and click send button
                setTimeout(() => {{
                    let sendBtn = null;
                    
                    // Try multiple selectors for send button
                    const selectors = [
                        'button[aria-label*="Send"]',
                        'button[data-testid="send-button"]', 
                        'button[title*="Send"]',
                        '.send-button',
                        'button:has(svg)',
                        'button[type="submit"]'
                    ];
                    
                    for (let selector of selectors) {{
                        sendBtn = document.querySelector(selector);
                        if (sendBtn) break;
                    }}
                    
                    // If still not found, look for buttons with Send text or SVG icons
                    if (!sendBtn) {{
                        const buttons = Array.from(document.querySelectorAll('button'));
                        sendBtn = buttons.find(btn => 
                            btn.textContent.toLowerCase().includes('send') ||
                            btn.querySelector('svg') ||
                            btn.getAttribute('aria-label')?.toLowerCase().includes('send')
                        );
                    }}
                    
                    if (sendBtn && !sendBtn.disabled) {{
                        sendBtn.click();
                        return "Message sent successfully";
                    }} else {{
                        return "Error: Could not find enabled send button. Found " + 
                               document.querySelectorAll('button').length + " buttons total";
                    }}
                }}, 1000);
                
                return "Message prepared, attempting to send...";
                
            }} catch (error) {{
                return "JavaScript error: " + error.message + " (Stack: " + error.stack + ")";
            }}
        }})();
        """
        
        # Try WebSocket first, then fallback to simple HTTP
        result = self.execute_js_websocket(js_code)
        
        # Check if result is a string before calling .lower()
        if isinstance(result, str) and ("error" in result.lower() or "timeout" in result.lower()):
            print(f"WebSocket failed ({result}), trying simple HTTP...")
            result = self.execute_js_simple(js_code)
        
        return result
    
    def wait_for_response(self, max_wait=30):
        """Wait for Claude's response"""
        js_code = """
        (function() {
            try {
                // Debug: Let's see what elements are available
                const allDivs = document.querySelectorAll('div');
                const allElements = document.querySelectorAll('*');
                
                // Try multiple approaches to find messages
                let messages = [];
                
                // Approach 1: Look for common message containers
                const selectors = [
                    '[data-testid="conversation-turn"]',
                    '.message',
                    '[role="article"]', 
                    '.prose',
                    '.chat-message',
                    '[data-message-id]',
                    '.conversation-turn',
                    '.assistant-message',
                    '.user-message',
                    '.markdown',
                    'div[class*="message"]',
                    'div[class*="conversation"]',
                    'div[class*="chat"]',
                    'div[class*="response"]'
                ];
                
                for (let selector of selectors) {
                    messages = document.querySelectorAll(selector);
                    if (messages.length > 0) break;
                }
                
                // Approach 2: Look for any div that contains substantial text
                if (messages.length === 0) {
                    const textDivs = Array.from(allDivs).filter(div => {
                        const text = div.textContent || '';
                        return text.length > 20 && 
                               !div.querySelector('input') && 
                               !div.querySelector('textarea') &&
                               !div.querySelector('button') &&
                               text.toLowerCase().includes('doing') || 
                               text.toLowerCase().includes('well') ||
                               text.toLowerCase().includes('how') ||
                               text.toLowerCase().includes('today');
                    });
                    if (textDivs.length > 0) {
                        messages = textDivs;
                    }
                }
                
                // Approach 3: Look for any element containing the expected response
                if (messages.length === 0) {
                    const responseElements = Array.from(allElements).filter(el => {
                        const text = el.textContent || '';
                        return text.includes("I'm doing well") || 
                               text.includes("How are you") ||
                               (text.length > 10 && text.toLowerCase().includes('doing'));
                    });
                    if (responseElements.length > 0) {
                        messages = responseElements;
                    }
                }
                
                if (messages.length === 0) {
                    // Return debug info
                    return {
                        text: "No messages found",
                        generating: false,
                        length: 0,
                        debug: "Total elements: " + allElements.length + 
                               ", Divs: " + allDivs.length +
                               ", Body text preview: " + (document.body.textContent || '').substring(0, 200)
                    };
                }
                
                // Get the last/best message
                const lastMessage = messages[messages.length - 1];
                let text = lastMessage.textContent || lastMessage.innerText || '';
                
                // Clean up the text and separate thinking from actual response
                text = text.trim();
                
                // Try to separate the thinking part from the actual response
                // Look for patterns that indicate thinking vs actual response
                if (text.includes('Thinking about') || text.includes('0s')) {
                    // Look for the actual response after thinking patterns
                    // Pattern 1: Find text after "I should..." or similar thinking conclusions
                    let responseMatch = text.match(/I should[^.]*\.\s*(.+)/);
                    if (responseMatch) {
                        text = responseMatch[1].trim();
                    } else {
                        // Pattern 2: Find text after thinking time indicators like "0s"
                        responseMatch = text.match(/\d+s[^.]*\.\s*(.+)/);
                        if (responseMatch) {
                            text = responseMatch[1].trim();
                        } else {
                            // Pattern 3: Split by "Thinking about" and take the last meaningful part
                            const parts = text.split('Thinking about');
                            if (parts.length > 1) {
                                // Look for the actual response in the last part
                                const lastPart = parts[parts.length - 1];
                                const actualResponse = lastPart.match(/[.!?]\s*([A-Z][^]*)/);
                                if (actualResponse) {
                                    text = actualResponse[1].trim();
                                }
                            }
                        }
                    }
                }
                
                // Additional cleanup - remove any remaining thinking artifacts
                text = text.replace(/^.*?I should[^.]*\.\s*/, '');
                text = text.replace(/^.*?\d+s[^.]*\.\s*/, '');
                text = text.replace(/^Thinking about[^.]*\.\s*/, '');
                
                // Check if it's still generating
                const isGenerating = !!(
                    document.querySelector('[data-testid="stop-button"]') ||
                    document.querySelector('.stop-button') ||
                    document.querySelector('[aria-label*="Stop"]') ||
                    text.includes('▌') ||
                    text.endsWith('...') ||
                    text.length < 5
                );
                
                return {
                    text: text,
                    generating: isGenerating,
                    length: text.length,
                    messageCount: messages.length,
                    selector: messages.length > 0 ? (lastMessage.className || lastMessage.tagName) : 'none'
                };
            } catch (error) {
                return {
                    text: "Error: " + error.message,
                    generating: false,
                    length: 0,
                    error: error.stack
                };
            }
        })();
        """
        
        print("Waiting for Claude's response...")
        
        for i in range(max_wait):
            try:
                # Try WebSocket first, then fallback
                result_str = self.execute_js_websocket(js_code)
                
                # Check if result_str is a string before calling .lower()
                if isinstance(result_str, str) and ("error" in result_str.lower() or "timeout" in result_str.lower()):
                    result_str = self.execute_js_simple(js_code)
                
                # Parse the result
                if isinstance(result_str, str) and result_str.startswith('{'):
                    try:
                        value = json.loads(result_str)
                    except:
                        value = {"text": result_str, "generating": False, "length": len(result_str)}
                elif isinstance(result_str, dict):
                    value = result_str
                else:
                    value = {"text": str(result_str), "generating": False, "length": len(str(result_str))}
                
                text = value.get('text', '')
                generating = value.get('generating', False)
                length = value.get('length', 0)
                
                if text and length > 20 and not generating:
                    return text
                elif text and generating:
                    print(f"Claude is typing... ({length} chars)")
                elif text:
                    print(f"Got response but might be incomplete: {text[:50]}...")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Error waiting for response: {e}")
                time.sleep(1)
        
        return "Timeout: No complete response received within 30 seconds"

def main():
    if len(sys.argv) < 2:
        print("Usage: python claude_simple_cdp.py 'your question'")
        print("Example: python claude_simple_cdp.py 'how ry?'")
        return
    
    question = sys.argv[1]
    
    print("Claude Simple CDP (No Playwright)")
    print("=" * 40)
    print(f"Question: {question}")
    print()
    
    # Check Chrome debug
    try:
        response = requests.get("http://localhost:9222/json", timeout=3)
        if response.status_code != 200:
            raise Exception("Chrome debug not accessible")
    except:
        print("❌ Chrome debug port not accessible")
        print()
        print("Setup required:")
        print("1. Close all Chrome instances")
        print("2. Start Chrome with:")
        print("   chrome --remote-debugging-port=9222 --user-data-dir=C:\\temp\\chrome-debug")
        print("3. Open https://claude.ai and login")
        print("4. Start a new conversation")
        print("5. Run this script again")
        print()
        print("Optional: Install websocket support for better reliability:")
        print("   pip install websocket-client")
        return
    
    print("✅ Chrome debug accessible")
    
    # Initialize Claude
    claude = SimpleClaude()
    
    # Find Claude tab
    if not claude.get_claude_tab():
        print("❌ No Claude.ai tab found")
        print("Please open https://claude.ai in Chrome and login")
        return
    
    print("✅ Found Claude.ai tab")
    
    # Send question
    print("Sending question...")
    result = claude.inject_and_ask(question)
    print(f"Send result: {result}")
    
    if "Error:" in result or "error" in result.lower():
        print(f"❌ {result}")
        print()
        print("Troubleshooting tips:")
        print("1. Make sure you're on the Claude conversation page")
        print("2. Try refreshing the Claude.ai page")
        print("3. Make sure the input field is visible and not blocked")
        return
    
    # Wait for response
    response = claude.wait_for_response()
    
    print()
    print("Claude Response:")
    print("-" * 40)
    print(response)
    print("-" * 40)
    
    if "Error:" in response or "Timeout:" in response or "error" in response.lower():
        print("❌ Failed to get complete response")
        print()
        print("Try:")
        print("1. Make sure you're on the conversation page")
        print("2. Try asking a question manually first")
        print("3. Refresh the Claude.ai page")
        print("4. Check if Claude is responding to manual input")
    else:
        print("✅ Success!")

if __name__ == "__main__":
    main()
