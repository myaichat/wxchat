import asyncio
import websockets
import json

async def wait_for_response(websocket, command_id):
    """Wait for a specific command response, ignoring events"""
    while True:
        message = await websocket.recv()
        try:
            data = json.loads(message)
            if data.get("id") == command_id:
                return data
            # Print events for debugging (but don't print RESPONSE_UPDATE to avoid duplication)
            if data.get("method") == "Runtime.consoleAPICalled":
                args = data.get("params", {}).get("args", [])
                if args:
                    console_msg = args[0].get('value', '')
                    if not console_msg.startswith("RESPONSE_UPDATE:") and not console_msg.startswith("CONTENT_DEBUG:") and not console_msg.startswith("VALIDATION_DEBUG:") and not console_msg.startswith("COMPLETION_DEBUG:") and not console_msg.startswith("COMPLETION_CHECK:"):
                        print(f"Console: {console_msg}")
        except json.JSONDecodeError:
            continue

async def send_message_with_streaming(message, timeout=120):
    """Generator that yields streaming responses as they arrive"""
    ws_url = "ws://localhost:9222/devtools/page/8DB73BEB74A6520C28B7C9607929F317"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("Connected to WebSocket")
            
            # Enable Runtime domain
            await websocket.send(json.dumps({
                "id": 1,
                "method": "Runtime.enable"
            }))
            await wait_for_response(websocket, 1)
            
            # Properly escape the message for JavaScript
            escaped_message = json.dumps(message)
            
            # Completely rewritten observer with simpler approach
            observer_js = f'''
                (async function() {{
                    console.log("Setting up fresh streaming observer");
                    
                    let messageSent = false;
                    let responseFound = false;
                    let responseComplete = false;
                    let lastResponseText = "";
                    let responseElement = null;
                    let sentMessageTimestamp = 0;
                    let lastUpdateTime = 0;
                    let initialPageContent = "";
                    
                    // Cleanup function
                    function cleanup() {{
                        if (window.chatStreamingPollId) {{
                            clearInterval(window.chatStreamingPollId);
                            window.chatStreamingPollId = null;
                        }}
                        if (window.chatCompletionCheckId) {{
                            clearInterval(window.chatCompletionCheckId);
                            window.chatCompletionCheckId = null;
                        }}
                        if (window.chatResponseObserver) {{
                            window.chatResponseObserver.disconnect();
                            window.chatResponseObserver = null;
                        }}
                        if (window.chatMainObserver) {{
                            window.chatMainObserver.disconnect();
                            window.chatMainObserver = null;
                        }}
                        window.chatObserverActive = false;
                    }}
                    
                    // Function to extract text from element
                    function extractText(element) {{
                        if (!element) return '';
                        return element.innerText || element.textContent || '';
                    }}
                    
                    // Simple approach: look for new text content that appears after sending message
                    function findNewResponseContent() {{
                        // Get all text content from the page
                        const currentPageContent = document.body.innerText || document.body.textContent || '';
                        
                        if (!initialPageContent) {{
                            initialPageContent = currentPageContent;
                            return '';
                        }}
                        
                        // Find new content that appeared after sending the message
                        if (currentPageContent.length > initialPageContent.length) {{
                            const newContent = currentPageContent.substring(initialPageContent.length).trim();
                            
                            // Filter out our own message and common UI elements
                            const filteredContent = newContent
                                .replace({escaped_message}, '')
                                .replace(/^\\s*hello\\s*/i, '')
                                .replace(/^\\s*Thinking about.*$/gm, '')
                                .replace(/^\\s*Claude can make mistakes.*$/gm, '')
                                .replace(/^\\s*Share\\s*$/gm, '')
                                .replace(/^\\s*Retry\\s*$/gm, '')
                                .replace(/^\\s*Copy\\s*$/gm, '')
                                .replace(/^\\s*1s\\s*$/gm, '')
                                .replace(/^\\s*Reply to Claude.*$/gm, '')
                                .replace(/^\\s*Claude Sonnet.*$/gm, '')
                                .trim();
                            
                            if (filteredContent && filteredContent.length > 5) {{
                                return filteredContent;
                            }}
                        }}
                        
                        return '';
                    }}
                    
                    // Alternative approach: look for specific response patterns
                    function findResponseByPattern() {{
                        // Look for text that appears to be a response
                        const responsePatterns = [
                            // Look for paragraphs that contain typical response content
                            'Hello! It\\'s nice to meet you',
                            'Hello!',
                            'Hi there!',
                            'How can I help',
                            'I\\'m Claude',
                            'I can help you'
                        ];
                        
                        for (const pattern of responsePatterns) {{
                            const elements = document.querySelectorAll('*');
                            for (const element of elements) {{
                                const text = extractText(element);
                                if (text.includes(pattern) && text.length > 10 && text.length < 1000) {{
                                    // Make sure this isn't our input message
                                    if (!text.includes({escaped_message}) || text.length > {escaped_message}.length * 2) {{
                                        return text.trim();
                                    }}
                                }}
                            }}
                        }}
                        
                        return '';
                    }}
                    
                    // Capture initial page state
                    initialPageContent = document.body.innerText || document.body.textContent || '';
                    
                    console.log("Observer active, now sending message");
                    
                    // Find and populate textarea
                    const selectors = [
                        'textarea[placeholder*="Reply"]',
                        'textarea[placeholder*="Message"]',
                        'textarea[placeholder*="message"]',
                        'textarea',
                        'div[contenteditable="true"]',
                        '[role="textbox"]'
                    ];
                    
                    let textarea = null;
                    for (const selector of selectors) {{
                        textarea = document.querySelector(selector);
                        if (textarea) {{
                            console.log("Found textarea with selector: " + selector);
                            break;
                        }}
                    }}
                    
                    if (!textarea) {{
                        cleanup();
                        console.log("ERROR: Textarea not found");
                        return "Textarea not found";
                    }}
                    
                    // Clear and populate textarea
                    if (textarea.contentEditable === "true") {{
                        textarea.innerHTML = "";
                        textarea.focus();
                        const selection = window.getSelection();
                        const range = document.createRange();
                        range.selectNodeContents(textarea);
                        selection.removeAllRanges();
                        selection.addRange(range);
                        document.execCommand('insertText', false, {escaped_message});
                    }} else {{
                        textarea.value = "";
                        textarea.focus();
                        textarea.value = {escaped_message};
                    }}
                    
                    // Trigger events
                    const events = ['input', 'change', 'keyup', 'keydown'];
                    events.forEach(eventType => {{
                        textarea.dispatchEvent(new Event(eventType, {{ bubbles: true, cancelable: true }}));
                    }});
                    
                    // Wait for interface to process
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    // Find send button
                    const buttonSelectors = [
                        'button[data-testid="send-button"]',
                        'button[aria-label*="Send"]',
                        'button[aria-label*="send"]',
                        'button[type="submit"]',
                        'button:has(svg)',
                        'button[class*="send"]',
                        'button:not([disabled])',
                    ];
                    
                    let sendButton = null;
                    for (const selector of buttonSelectors) {{
                        const buttons = document.querySelectorAll(selector);
                        for (const button of buttons) {{
                            if (!button.disabled && button.offsetParent !== null) {{
                                const rect = button.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {{
                                    sendButton = button;
                                    console.log("Found send button with selector: " + selector);
                                    break;
                                }}
                            }}
                        }}
                        if (sendButton) break;
                    }}
                    
                    if (sendButton && !sendButton.disabled) {{
                        sentMessageTimestamp = Date.now();
                        lastUpdateTime = Date.now();
                        messageSent = true;
                        
                        // Update initial content right before sending
                        initialPageContent = document.body.innerText || document.body.textContent || '';
                        
                        sendButton.click();
                        console.log("Message sent, observer monitoring for response");
                        
                        // Wait a moment for the message to be processed
                        await new Promise(resolve => setTimeout(resolve, 2000));
                        
                        // Start monitoring for response
                        let checkCount = 0;
                        let stableCount = 0;
                        let hasStarted = false;
                        
                        const responseCheckInterval = setInterval(() => {{
                            checkCount++;
                            
                            if (checkCount > 240) {{ // 2 minutes max
                                console.log("TIMEOUT: Response incomplete after {timeout} seconds");
                                cleanup();
                                if (lastResponseText) {{
                                    console.log("RESPONSE_COMPLETE:" + lastResponseText);
                                }}
                                return;
                            }}
                            
                            // Try both approaches to find response
                            let currentResponse = findNewResponseContent();
                            if (!currentResponse) {{
                                currentResponse = findResponseByPattern();
                            }}
                            
                            if (currentResponse && currentResponse !== lastResponseText) {{
                                if (!hasStarted) {{
                                    hasStarted = true;
                                    console.log("RESPONSE_STARTED");
                                }}
                                
                                lastResponseText = currentResponse;
                                lastUpdateTime = Date.now();
                                stableCount = 0;
                                console.log("RESPONSE_UPDATE:" + currentResponse);
                            }} else if (currentResponse && currentResponse === lastResponseText) {{
                                const timeSinceUpdate = Date.now() - lastUpdateTime;
                                if (timeSinceUpdate > 3000) {{ // 3 seconds of stability
                                    stableCount++;
                                    if (stableCount >= 3) {{ // 1.5 seconds of stability checks
                                        console.log("RESPONSE_COMPLETE:" + currentResponse);
                                        clearInterval(responseCheckInterval);
                                        cleanup();
                                    }}
                                }}
                            }}
                        }}, 500);
                        
                        // Set overall timeout
                        setTimeout(() => {{
                            if (!responseComplete) {{
                                console.log("TIMEOUT: Response incomplete after {timeout} seconds");
                                clearInterval(responseCheckInterval);
                                cleanup();
                                if (lastResponseText) {{
                                    console.log("RESPONSE_COMPLETE:" + lastResponseText);
                                }}
                            }}
                        }}, {timeout * 1000});
                        
                        return "Message sent, streaming observer active";
                    }} else {{
                        cleanup();
                        console.log("ERROR: Send button not found or disabled");
                        return "Send button not found or disabled";
                    }}
                }})();
            '''
            
            await websocket.send(json.dumps({
                "id": 3,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": observer_js,
                    "returnByValue": True
                }
            }))
            
            eval_response = await wait_for_response(websocket, 3)
            print(f"Observer setup result: {eval_response}")
            
            # Wait for streaming responses
            print(f"Waiting up to {timeout} seconds for streaming response...")
            
            start_time = asyncio.get_event_loop().time()
            response_started = False
            response_complete = False
            
            while (asyncio.get_event_loop().time() - start_time) < timeout and not response_complete:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if data.get("method") == "Runtime.consoleAPICalled":
                        args = data.get("params", {}).get("args", [])
                        if args:
                            console_message = args[0].get("value", "")
                            
                            if console_message == "RESPONSE_STARTED":
                                response_started = True
                                print("\\n=== RESPONSE STARTED (streaming) ===")
                                yield {"status": "started", "content": ""}
                                
                            elif console_message.startswith("RESPONSE_UPDATE:"):
                                content = console_message.replace("RESPONSE_UPDATE:", "")
                                if content.strip():  # Only yield if there's actual content
                                    yield {"status": "streaming", "content": content}
                                    
                            elif console_message.startswith("RESPONSE_COMPLETE:"):
                                content = console_message.replace("RESPONSE_COMPLETE:", "")
                                print(f"\\n=== RESPONSE COMPLETE ===")
                                print(f"Final response length: {len(content)} characters")
                                response_complete = True
                                yield {"status": "complete", "content": content}
                                break
                                
                            elif console_message.startswith("TIMEOUT:"):
                                print("Observer timed out")
                                yield {"status": "timeout", "content": ""}
                                break
                            elif console_message.startswith("ERROR:"):
                                print(f"Error: {console_message}")
                                
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
            
            if not response_started:
                yield {"status": "error", "content": "No response received within timeout period"}
                
    except Exception as e:
        print(f"Error: {e}")
        yield {"status": "error", "content": f"Error: {e}"}

async def send_message_with_observer(message, timeout=120):
    """Original function that waits for complete response"""
    final_response = None
    async for response in send_message_with_streaming(message, timeout):
        if response["status"] in ["complete", "timeout", "error"]:
            final_response = response["content"]
            break
    
    return final_response if final_response else "No response received"

# Usage examples
async def main():
    message = "Hello! show large sample pl/sql program"
    
    print("=== STREAMING EXAMPLE ===")
    previous_content = ""
    
    async for response in send_message_with_streaming(message, timeout=120):
        status = response['status']
        content = response['content']
        
        if status == "started":
            print("\n🚀 Response started streaming...")
            print("📝 Streaming chunks:")
            print("-" * 50)
        elif status == "streaming":
            # Show only the new chunk (difference from previous content)
            if len(content) > len(previous_content):
                new_chunk = content[len(previous_content):]
                try:
                    print(new_chunk, end='', flush=True)
                except UnicodeEncodeError:
                    # Handle emoji and special characters
                    print(new_chunk.encode('utf-8', errors='replace').decode('utf-8'), end='', flush=True)
                previous_content = content
        elif status == "complete":
            # Show any final chunk
            if len(content) > len(previous_content):
                new_chunk = content[len(previous_content):]
                try:
                    print(new_chunk, end='', flush=True)
                except UnicodeEncodeError:
                    # Handle emoji and special characters
                    print(new_chunk.encode('utf-8', errors='replace').decode('utf-8'), end='', flush=True)
            
            print(f"\n{'-' * 50}")
            print(f"✅ Response complete ({len(content)} chars)")
            print("=" * 50)
            print("FULL RESPONSE:")
            print(content)
            print("=" * 50)
            break
        elif status in ["timeout", "error"]:
            print(f"\n❌ {status}: {content}")
            break

if __name__ == "__main__":
    asyncio.run(main())
