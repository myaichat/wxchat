#!/usr/bin/env python3
"""
Streaming Claude alternative using Chrome DevTools Protocol (no Playwright)
Shows response streaming in real-time as Claude types
Usage: python claude_simple_cdp_streaming.py "tell me more about java?"
"""

import sys
import json
import requests
import time
import re
import urllib.parse
import threading
import asyncio
from datetime import datetime

class StreamingClaude:
    def __init__(self, debug_port=9222):
        self.debug_port = debug_port
        self.base_url = f"http://localhost:{debug_port}"
        self.tab_id = None
        self.ws_url = None
        self.last_response_length = 0
        self.streaming_active = False
        
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
    
    def get_current_response(self):
        """Get current response text from Claude"""
        js_code = """
        (function() {
            try {
                // Find messages with multiple approaches
                let messages = [];
                
                // Try multiple selectors for message containers
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
                
                // Fallback: Look for any div with substantial text
                if (messages.length === 0) {
                    const allDivs = document.querySelectorAll('div');
                    const textDivs = Array.from(allDivs).filter(div => {
                        const text = div.textContent || '';
                        return text.length > 20 && 
                               !div.querySelector('input') && 
                               !div.querySelector('textarea') &&
                               !div.querySelector('button');
                    });
                    if (textDivs.length > 0) {
                        messages = textDivs;
                    }
                }
                
                if (messages.length === 0) {
                    return {
                        text: "",
                        generating: false,
                        length: 0,
                        error: "No messages found"
                    };
                }
                
                // Get the last message (most recent)
                const lastMessage = messages[messages.length - 1];
                let text = lastMessage.textContent || lastMessage.innerText || '';
                
                // Clean up the text
                text = text.trim();
                
                // Remove thinking artifacts if present
                text = text.replace(/^.*?I should[^.]*\.\s*/, '');
                text = text.replace(/^.*?\d+s[^.]*\.\s*/, '');
                text = text.replace(/^Thinking about[^.]*\.\s*/, '');
                
                // Check if Claude is still generating
                const isGenerating = !!(
                    document.querySelector('[data-testid="stop-button"]') ||
                    document.querySelector('.stop-button') ||
                    document.querySelector('[aria-label*="Stop"]') ||
                    text.includes('▌') ||
                    text.endsWith('...') ||
                    lastMessage.querySelector('.loading') ||
                    lastMessage.querySelector('.spinner')
                );
                
                return {
                    text: text,
                    generating: isGenerating,
                    length: text.length,
                    messageCount: messages.length
                };
            } catch (error) {
                return {
                    text: "",
                    generating: false,
                    length: 0,
                    error: error.message
                };
            }
        })();
        """
        
        # Try WebSocket first, then fallback
        result_str = self.execute_js_websocket(js_code)
        
        if isinstance(result_str, str) and ("error" in result_str.lower() or "timeout" in result_str.lower()):
            result_str = self.execute_js_simple(js_code)
        
        # Parse the result
        if isinstance(result_str, str) and result_str.startswith('{'):
            try:
                return json.loads(result_str)
            except:
                return {"text": result_str, "generating": False, "length": len(result_str)}
        elif isinstance(result_str, dict):
            return result_str
        else:
            return {"text": str(result_str), "generating": False, "length": len(str(result_str))}
    
    def print_streaming_response(self, new_text, is_complete=False):
        """Print new text as it streams in"""
        if not new_text:
            return
            
        # Clear the current line and print new text
        if self.streaming_active:
            # Move cursor to beginning of line and clear it
            print('\r' + ' ' * 80 + '\r', end='', flush=True)
        
        # Print the new text
        print(new_text, end='', flush=True)
        
        if is_complete:
            print()  # New line when complete
            self.streaming_active = False
        else:
            self.streaming_active = True
    
    async def send_message_with_streaming(self, question, max_wait=60, update_interval=0.5):
        """
        Async generator that yields chunks of Claude's response as they come in
        Usage: async for chunk in claude.send_message_with_streaming(question):
        """
        # Send the question first
        result = self.inject_and_ask(question)
        if "Error:" in result or "error" in result.lower():
            yield {"error": result, "complete": True}
            return
        
        # Wait a moment for the message to be processed
        await asyncio.sleep(2)
        
        start_time = time.time()
        last_text = ""
        last_length = 0
        no_change_count = 0
        
        while time.time() - start_time < max_wait:
            try:
                response_data = self.get_current_response()
                current_text = response_data.get('text', '')
                is_generating = response_data.get('generating', False)
                current_length = response_data.get('length', 0)
                
                # Check if we have new content
                if current_text != last_text and current_length > 0:
                    # Yield only the new part
                    if current_length > last_length:
                        new_part = current_text[last_length:]
                        yield {
                            "chunk": new_part,
                            "full_text": current_text,
                            "length": current_length,
                            "generating": is_generating,
                            "complete": False
                        }
                    else:
                        # Text changed but not necessarily longer (might be reformatted)
                        yield {
                            "chunk": "",
                            "full_text": current_text,
                            "length": current_length,
                            "generating": is_generating,
                            "complete": False,
                            "reformatted": True
                        }
                    
                    last_text = current_text
                    last_length = current_length
                    no_change_count = 0
                
                # Check if response is complete
                if current_length > 20 and not is_generating:
                    yield {
                        "chunk": "",
                        "full_text": current_text,
                        "length": current_length,
                        "generating": False,
                        "complete": True
                    }
                    return
                
                # Check for no changes (might indicate completion or error)
                if current_text == last_text:
                    no_change_count += 1
                    if no_change_count > 10 and current_length > 10:  # 5 seconds of no change
                        yield {
                            "chunk": "",
                            "full_text": current_text,
                            "length": current_length,
                            "generating": False,
                            "complete": True,
                            "reason": "no_new_content"
                        }
                        return
                
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                yield {
                    "error": f"Error during streaming: {e}",
                    "complete": True
                }
                return
        
        # Timeout reached
        yield {
            "chunk": "",
            "full_text": last_text,
            "length": len(last_text) if last_text else 0,
            "generating": False,
            "complete": True,
            "timeout": True,
            "error": "Streaming timeout reached"
        }

    def stream_response(self, max_wait=60, update_interval=0.5):
        """Stream Claude's response in real-time"""
        print("\n🤖 Claude is responding...")
        print("=" * 50)
        
        start_time = time.time()
        last_text = ""
        last_length = 0
        no_change_count = 0
        
        while time.time() - start_time < max_wait:
            try:
                response_data = self.get_current_response()
                current_text = response_data.get('text', '')
                is_generating = response_data.get('generating', False)
                current_length = response_data.get('length', 0)
                
                # Check if we have new content
                if current_text != last_text and current_length > 0:
                    # Print only the new part
                    if current_length > last_length:
                        new_part = current_text[last_length:]
                        print(new_part, end='', flush=True)
                    else:
                        # Text changed but not necessarily longer (might be reformatted)
                        print(f"\r{current_text}", end='', flush=True)
                    
                    last_text = current_text
                    last_length = current_length
                    no_change_count = 0
                
                # Check if response is complete
                if current_length > 20 and not is_generating:
                    print()  # New line
                    print("=" * 50)
                    print("✅ Response complete!")
                    return current_text
                
                # Show progress for long responses
                if is_generating and current_length > 0:
                    # Update status occasionally
                    if int(time.time()) % 5 == 0:
                        elapsed = int(time.time() - start_time)
                        print(f"\n[Streaming... {current_length} chars, {elapsed}s elapsed]", end='', flush=True)
                
                # Check for no changes (might indicate completion or error)
                if current_text == last_text:
                    no_change_count += 1
                    if no_change_count > 10 and current_length > 10:  # 5 seconds of no change
                        print()
                        print("=" * 50)
                        print("✅ Response appears complete (no new content)")
                        return current_text
                
                time.sleep(update_interval)
                
            except Exception as e:
                print(f"\n❌ Error during streaming: {e}")
                time.sleep(1)
        
        print()
        print("=" * 50)
        print("⏰ Streaming timeout reached")
        return last_text if last_text else "Timeout: No response received"

def main():
    if len(sys.argv) < 2:
        print("Usage: python claude_simple_cdp_streaming.py 'your question'")
        print("Example: python claude_simple_cdp_streaming.py 'tell me more about java?'")
        return
    
    question = sys.argv[1]
    
    print("🚀 Claude Streaming CDP (Real-time Response)")
    print("=" * 50)
    print(f"📝 Question: {question}")
    print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Check Chrome debug
    try:
        response = requests.get("http://localhost:9222/json", timeout=3)
        if response.status_code != 200:
            raise Exception("Chrome debug not accessible")
    except:
        print("❌ Chrome debug port not accessible")
        print()
        print("🔧 Setup required:")
        print("1. Close all Chrome instances")
        print("2. Start Chrome with:")
        print("   chrome --remote-debugging-port=9222 --user-data-dir=C:\\temp\\chrome-debug")
        print("3. Open https://claude.ai and login")
        print("4. Start a new conversation")
        print("5. Run this script again")
        print()
        print("💡 Optional: Install websocket support for better reliability:")
        print("   pip install websocket-client")
        return
    
    print("✅ Chrome debug accessible")
    
    # Initialize Claude
    claude = StreamingClaude()
    
    # Find Claude tab
    if not claude.get_claude_tab():
        print("❌ No Claude.ai tab found")
        print("Please open https://claude.ai in Chrome and login")
        return
    
    print("✅ Found Claude.ai tab")
    
    # Send question
    print("📤 Sending question...")
    result = claude.inject_and_ask(question)
    print(f"📋 Send result: {result}")
    
    if "Error:" in result or "error" in result.lower():
        print(f"❌ {result}")
        print()
        print("🔧 Troubleshooting tips:")
        print("1. Make sure you're on the Claude conversation page")
        print("2. Try refreshing the Claude.ai page")
        print("3. Make sure the input field is visible and not blocked")
        return
    
    # Wait a moment for the message to be processed
    print("⏳ Waiting for Claude to start responding...")
    time.sleep(2)
    
    # Stream the response
    response = claude.stream_response()
    
    print()
    print("📊 Final Response:")
    print("-" * 50)
    print(response)
    print("-" * 50)
    print(f"📏 Length: {len(response)} characters")
    print(f"⏰ Completed at: {datetime.now().strftime('%H:%M:%S')}")
    
    if "Error:" in response or "Timeout:" in response or "error" in response.lower():
        print("❌ Failed to get complete response")
        print()
        print("🔧 Try:")
        print("1. Make sure you're on the conversation page")
        print("2. Try asking a question manually first")
        print("3. Refresh the Claude.ai page")
        print("4. Check if Claude is responding to manual input")
    else:
        print("🎉 Streaming completed successfully!")

if __name__ == "__main__":
    main()
