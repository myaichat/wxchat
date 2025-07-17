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
            
            # Set up new observer with proper cleanup
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
                    
                    // Function to get response content (excluding headers/prefixes)
                    function getResponseContent(element) {{
                        let text = extractText(element);
                        
                        const prefixes = [
                            'ChatGPT said:',
                            'Claude said:',
                            'Assistant:',
                            'AI:',
                            'Bot:',
                        ];
                        
                        for (const prefix of prefixes) {{
                            if (text.startsWith(prefix)) {{
                                text = text.substring(prefix.length).trim();
                            }}
                        }}
                        
                        return text;
                    }}
                    
                    // Function to check if this is an assistant message
                    function isAssistantMessage(element) {{
                        // Look for specific assistant indicators
                        if (element.querySelector('[data-message-author-role="assistant"]') ||
                            element.matches('[data-message-author-role="assistant"]')) {{
                            return true;
                        }}
                        
                        // Check if this appears after our sent message and doesn't contain our sent text
                        const elementText = getResponseContent(element);
                        if (elementText && elementText.length > 10 && !elementText.includes({escaped_message}) && messageSent) {{
                            const timeSinceMessage = Date.now() - sentMessageTimestamp;
                            if (timeSinceMessage > 0 && timeSinceMessage < 120000) {{
                                return true;
                            }}
                        }}
                        
                        return false;
                    }}
                    
                    // Simplified completion detection
                    function checkIfComplete(element, text) {{
                        if (text.length < 20) return false;
                        
                        // Check for copy button or other completion indicators
                        const completionIndicators = [
                            'button[aria-label*="Copy"]',
                            'button[data-testid*="copy"]',
                            'button[title*="Copy"]',
                        ];
                        
                        for (const indicator of completionIndicators) {{
                            if (element.querySelector(indicator) || document.querySelector(indicator)) {{
                                return true;
                            }}
                        }}
                        
                        // Check if text appears to end naturally
                        const trimmedText = text.trim();
                        const endsNaturally = /[.!?]\\s*$/.test(trimmedText) || 
                                             trimmedText.endsWith('```') ||
                                             /\\n\\s*$/.test(trimmedText);
                        
                        return endsNaturally && text.length > 100;
                    }}
                    
                    // Set up mutation observer
                    window.chatMainObserver = new MutationObserver(function(mutations) {{
                        if (!messageSent || responseComplete) return;
                        
                        mutations.forEach(function(mutation) {{
                            if (mutation.type === 'childList') {{
                                mutation.addedNodes.forEach(function(node) {{
                                    if (node.nodeType === Node.ELEMENT_NODE && !responseFound) {{
                                        if (isAssistantMessage(node)) {{
                                            responseFound = true;
                                            responseElement = node;
                                            lastUpdateTime = Date.now();
                                            console.log("RESPONSE_STARTED");
                                            
                                            const initialContent = getResponseContent(responseElement);
                                            if (initialContent && initialContent.length > 0) {{
                                                lastResponseText = initialContent;
                                                console.log("RESPONSE_UPDATE:" + initialContent);
                                            }}
                                            
                                            // Monitor this element for changes
                                            window.chatResponseObserver = new MutationObserver(function(responseMutations) {{
                                                if (responseComplete) return;
                                                
                                                const currentContent = getResponseContent(responseElement);
                                                if (currentContent !== lastResponseText && currentContent.length > 0) {{
                                                    lastResponseText = currentContent;
                                                    lastUpdateTime = Date.now();
                                                    console.log("RESPONSE_UPDATE:" + currentContent);
                                                }}
                                            }});
                                            
                                            window.chatResponseObserver.observe(responseElement, {{
                                                childList: true,
                                                subtree: true,
                                                characterData: true,
                                                attributes: true
                                            }});
                                            
                                            // Polling for streaming updates
                                            window.chatStreamingPollId = setInterval(() => {{
                                                if (responseComplete) return;
                                                
                                                const currentContent = getResponseContent(responseElement);
                                                if (currentContent !== lastResponseText && currentContent.length > 0) {{
                                                    lastResponseText = currentContent;
                                                    lastUpdateTime = Date.now();
                                                    console.log("RESPONSE_UPDATE:" + currentContent);
                                                }}
                                            }}, 50);
                                            
                                            // Completion check with timeout
                                            let stableCount = 0;
                                            let maxChecks = 0;
                                            
                                            window.chatCompletionCheckId = setInterval(() => {{
                                                if (responseComplete) return;
                                                
                                                maxChecks++;
                                                if (maxChecks > 240) {{ // 2 minutes max
                                                    responseComplete = true;
                                                    console.log("RESPONSE_COMPLETE:" + lastResponseText);
                                                    cleanup();
                                                    return;
                                                }}
                                                
                                                const currentContent = getResponseContent(responseElement);
                                                const timeSinceUpdate = Date.now() - lastUpdateTime;
                                                
                                                if (currentContent === lastResponseText && timeSinceUpdate > 3000) {{
                                                    stableCount++;
                                                    if (stableCount >= 5) {{ // 2.5 seconds of stability
                                                        if (checkIfComplete(responseElement, currentContent)) {{
                                                            responseComplete = true;
                                                            console.log("RESPONSE_COMPLETE:" + currentContent);
                                                            cleanup();
                                                        }} else if (stableCount >= 20) {{ // 10 seconds max stability wait
                                                            responseComplete = true;
                                                            console.log("RESPONSE_COMPLETE:" + currentContent);
                                                            cleanup();
                                                        }}
                                                    }}
                                                }} else {{
                                                    stableCount = 0;
                                                }}
                                            }}, 500);
                                        }}
                                    }}
                                }});
                            }}
                        }});
                    }});
                    
                    // Start observing
                    window.chatMainObserver.observe(document.body, {{
                        childList: true,
                        subtree: true
                    }});
                    
                    console.log("Observer active, now sending message");
                    
                    // Find and populate textarea
                    const selectors = [
                        'textarea[placeholder*="Message"]',
                        'textarea[data-id*="root"]', 
                        '#prompt-textarea',
                        'textarea',
                        'div[contenteditable="true"]',
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
                    
                    // Wait for interface to process (reduced delay)
                    await new Promise(resolve => setTimeout(resolve, 200));
                    
                    // Find send button
                    const buttonSelectors = [
                        'button[data-testid="send-button"]',
                        'button[aria-label*="Send"]',
                        'button[type="submit"]',
                        'button:has(svg)',
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
                        sendButton.click();
                        console.log("Message sent, observer monitoring for response");
                        
                        // Set timeout with cleanup
                        setTimeout(() => {{
                            if (!responseComplete) {{
                                console.log("TIMEOUT: Response incomplete after {timeout} seconds");
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
                                if response_started:
                                    content = console_message.replace("RESPONSE_UPDATE:", "")
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
