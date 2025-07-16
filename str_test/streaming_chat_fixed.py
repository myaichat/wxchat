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

async def send_message_with_streaming(message, timeout=120):  # Increased default timeout
    """Generator that yields streaming responses as they arrive"""
    ws_url = "ws://localhost:9222/devtools/page/88E0A660C0870B92DD1E7248EDABA645"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("Connected to WebSocket")
            
            # Enable Runtime domain
            await websocket.send(json.dumps({
                "id": 1,
                "method": "Runtime.enable"
            }))
            await wait_for_response(websocket, 1)
            
            # Set up mutation observer for streaming responses
            observer_js = f'''
                (async function() {{
                    // Prevent multiple executions
                    if (window.chatObserverActive) {{
                        console.log("Observer already active, skipping");
                        return "Observer already running";
                    }}
                    window.chatObserverActive = true;
                    
                    console.log("Setting up streaming observer");
                    
                    let messageSent = false;
                    let responseFound = false;
                    let responseComplete = false;
                    let observer;
                    let lastResponseText = "";
                    let responseElement = null;
                    let sentMessageTimestamp = 0;
                    let lastUpdateTime = 0;
                    
                    // Store interval IDs for proper cleanup
                    let streamingPollId = null;
                    let completionCheckId = null;
                    let responseObserver = null;
                    
                    // Cleanup function
                    function cleanup() {{
                        if (streamingPollId) {{
                            clearInterval(streamingPollId);
                            streamingPollId = null;
                        }}
                        if (completionCheckId) {{
                            clearInterval(completionCheckId);
                            completionCheckId = null;
                        }}
                        if (responseObserver) {{
                            responseObserver.disconnect();
                            responseObserver = null;
                        }}
                        if (observer) {{
                            observer.disconnect();
                            observer = null;
                        }}
                        window.chatObserverActive = false;
                    }}
                    
                    // Function to extract text from element - improved version
                    function extractText(element) {{
                        if (!element) return '';
                        
                        // Try multiple approaches to get all text content
                        let text = '';
                        
                        // Method 1: innerText (respects styling)
                        if (element.innerText) {{
                            text = element.innerText;
                        }}
                        // Method 2: textContent (gets all text)
                        else if (element.textContent) {{
                            text = element.textContent;
                        }}
                        // Method 3: Manual traversal for complex structures
                        else {{
                            const walker = document.createTreeWalker(
                                element,
                                NodeFilter.SHOW_TEXT,
                                null,
                                false
                            );
                            
                            let node;
                            const textParts = [];
                            while (node = walker.nextNode()) {{
                                if (node.textContent.trim()) {{
                                    textParts.push(node.textContent);
                                }}
                            }}
                            text = textParts.join(' ');
                        }}
                        
                        return text.trim();
                    }}
                    
                    // Improved function to get actual response content (excluding headers/prefixes)
                    function getResponseContent(element) {{
                        let text = extractText(element);
                        
                        // More comprehensive prefix removal
                        const prefixes = [
                            'ChatGPT said:',
                            'Claude said:',
                            'Assistant:',
                            'AI:',
                            'Bot:',
                            /^[A-Za-z]+\\s+said:\\s*/,  // Regex for any name + "said:"
                        ];
                        
                        for (const prefix of prefixes) {{
                            if (typeof prefix === 'string' && text.startsWith(prefix)) {{
                                text = text.substring(prefix.length).trim();
                            }} else if (prefix instanceof RegExp) {{
                                text = text.replace(prefix, '').trim();
                            }}
                        }}
                        
                        return text;
                    }}
                    
                    // Response validation function
                    function isValidResponse(text) {{
                        // Filter out responses that are too short or appear to be system messages
                        if (text.length < 5) return false;
                        
                        // Filter out common system messages
                        const systemMessages = [
                            'Could not find the language',
                            'did you forget to load/include a language module',
                            'Intercom not booted',
                            'Loading',
                            'Thinking',
                            'Please wait'
                        ];
                        
                        for (const sysMsg of systemMessages) {{
                            if (text.toLowerCase().includes(sysMsg.toLowerCase())) return false;
                        }}
                        
                        return true;
                    }}
                    
                    // Function to check if this is an assistant message (not user message)
                    function isAssistantMessage(element) {{
                        // Look for specific assistant indicators
                        if (element.querySelector('[data-message-author-role="assistant"]') ||
                            element.matches('[data-message-author-role="assistant"]')) {{
                            return true;
                        }}
                        
                        // Look for common assistant message patterns
                        const assistantIndicators = [
                            '.assistant-message',
                            '[data-author="assistant"]',
                            '[data-role="assistant"]',
                            '[data-testid*="assistant"]',
                            '[data-testid*="response"]',
                            '.response-container',
                            '.ai-response'
                        ];
                        
                        for (const indicator of assistantIndicators) {{
                            if (element.querySelector(indicator) || element.matches(indicator)) {{
                                return true;
                            }}
                        }}
                        
                        // Check if this appears after our sent message and doesn't contain our sent text
                        const elementText = getResponseContent(element);
                        if (elementText && elementText.length > 10 && !elementText.includes("{message}") && messageSent) {{
                            const timeSinceMessage = Date.now() - sentMessageTimestamp;
                            // Only consider as response if it appeared after we sent the message
                            if (timeSinceMessage > 0 && timeSinceMessage < 120000) {{ // Within 2 minutes
                                return true;
                            }}
                        }}
                        
                        return false;
                    }}
                    
                    // Improved completion detection - less conservative, more reliable
                    function checkIfComplete(element, text) {{
                        // Don't complete if text is very short
                        if (text.length < 20) return false;
                        
                        // Check for definitive completion indicators
                        const definiteCompletionIndicators = [
                            'button[aria-label*="Copy"]',
                            'button[data-testid*="copy"]',
                            '[data-testid="copy-turn-action-button"]',
                            'button[title*="Copy"]',
                            'button[aria-label="Copy message"]',
                            'button[aria-label="Regenerate response"]',
                            'button[data-testid="regenerate"]'
                        ];
                        
                        let hasDefinitiveIndicator = false;
                        for (const indicator of definiteCompletionIndicators) {{
                            if (element.querySelector(indicator) || document.querySelector(indicator)) {{
                                hasDefinitiveIndicator = true;
                                break;
                            }}
                        }}
                        
                        // Look for streaming indicators that suggest it's still generating
                        const streamingIndicators = [
                            '.streaming',
                            '.generating',
                            '.typing',
                            '.loading',
                            '[data-testid*="streaming"]',
                            '.cursor-blink'
                        ];
                        
                        let hasStreamingIndicator = false;
                        for (const indicator of streamingIndicators) {{
                            if (element.querySelector(indicator) || document.querySelector(indicator)) {{
                                hasStreamingIndicator = true;
                                break;
                            }}
                        }}
                        
                        // If still streaming, definitely not complete
                        if (hasStreamingIndicator) return false;
                        
                        // Check if text appears to end naturally
                        const trimmedText = text.trim();
                        const endsNaturally = /[.!?]\\s*$/.test(trimmedText) || 
                                             trimmedText.endsWith('```') ||
                                             trimmedText.endsWith('</code>') ||
                                             /\\n\\s*$/.test(trimmedText);
                        
                        // Less conservative: completion indicator OR natural ending (not both)
                        return hasDefinitiveIndicator || (endsNaturally && text.length > 100);
                    }}
                    
                    // Set up mutation observer BEFORE sending message
                    observer = new MutationObserver(function(mutations) {{
                        if (!messageSent) return; // Don't process until message is sent
                        
                        mutations.forEach(function(mutation) {{
                            if (mutation.type === 'childList') {{
                                mutation.addedNodes.forEach(function(node) {{
                                    if (node.nodeType === Node.ELEMENT_NODE && !responseFound) {{
                                        // Check if this is an assistant message
                                        if (isAssistantMessage(node)) {{
                                            responseFound = true;
                                            responseElement = node;
                                            lastUpdateTime = Date.now();
                                            console.log("RESPONSE_STARTED");
                                            
                                            // Send initial update if content exists
                                            const initialContent = getResponseContent(responseElement);
                                            if (initialContent && initialContent.length > 0) {{
                                                lastResponseText = initialContent;
                                                console.log("RESPONSE_UPDATE:" + initialContent);
                                            }}
                                            
                                            // Start monitoring this specific element for changes
                                            responseObserver = new MutationObserver(function(responseMutations) {{
                                                const currentContent = getResponseContent(responseElement);
                                                
                                                // Send update if content changed
                                                if (currentContent !== lastResponseText && currentContent.length > 0) {{
                                                    lastResponseText = currentContent;
                                                    lastUpdateTime = Date.now();
                                                    console.log("RESPONSE_UPDATE:" + currentContent);
                                                }}
                                            }});
                                            
                                            responseObserver.observe(responseElement, {{
                                                childList: true,
                                                subtree: true,
                                                characterData: true,
                                                attributes: true  // Also watch for attribute changes
                                            }});
                                            
                                            // More frequent polling for streaming updates
                                            streamingPollId = setInterval(() => {{
                                                if (responseComplete) {{
                                                    return;
                                                }}
                                                
                                                const currentContent = getResponseContent(responseElement);
                                                if (currentContent !== lastResponseText && currentContent.length > 0) {{
                                                    lastResponseText = currentContent;
                                                    lastUpdateTime = Date.now();
                                                    console.log("RESPONSE_UPDATE:" + currentContent);
                                                }}
                                            }}, 50); // Check every 50ms for faster streaming detection
                                            
                                            // Improved completion check with better cleanup
                                            let stableTextCount = 0;
                                            let lastSeenLength = 0;
                                            let maxCompletionChecks = 0;
                                            
                                            completionCheckId = setInterval(() => {{
                                                if (responseComplete) {{
                                                    return;
                                                }}
                                                
                                                maxCompletionChecks++;
                                                
                                                // Force completion after 60 seconds (120 checks) to prevent infinite loops
                                                if (maxCompletionChecks > 120) {{
                                                    console.log("COMPLETION_DEBUG: Force completing after max checks");
                                                    responseComplete = true;
                                                    console.log("RESPONSE_COMPLETE:" + lastResponseText);
                                                    cleanup();
                                                    return;
                                                }}
                                                
                                                const currentContent = getResponseContent(responseElement);
                                                const currentTime = Date.now();
                                                const timeSinceLastUpdate = currentTime - lastUpdateTime;
                                                
                                                console.log(`COMPLETION_DEBUG: length=${{currentContent.length}}, stable=${{stableTextCount}}, timeSinceUpdate=${{timeSinceLastUpdate}}ms, checks=${{maxCompletionChecks}}`);
                                                
                                                // More reasonable stability check
                                                if (currentContent.length === lastSeenLength && currentContent.length > 50) {{
                                                    // Text length hasn't changed and we have some content
                                                    if (timeSinceLastUpdate > 2000) {{ // 2 seconds since last update
                                                        stableTextCount++;
                                                        console.log(`COMPLETION_CHECK: stable=${{stableTextCount}}, checking completion indicators`);
                                                        
                                                        // Much lower threshold: 10 checks (5 seconds) of stability
                                                        if (stableTextCount >= 10) {{
                                                            // Check if it looks complete
                                                            if (checkIfComplete(responseElement, currentContent)) {{
                                                                responseComplete = true;
                                                                console.log("RESPONSE_COMPLETE:" + currentContent);
                                                                cleanup();
                                                            }} else {{
                                                                // If it doesn't look complete but has been stable for 20 checks (10 seconds), force complete
                                                                if (stableTextCount >= 20) {{
                                                                    console.log("COMPLETION_DEBUG: Force completing - stable too long");
                                                                    responseComplete = true;
                                                                    console.log("RESPONSE_COMPLETE:" + currentContent);
                                                                    cleanup();
                                                                }}
                                                            }}
                                                        }}
                                                    }} else {{
                                                        stableTextCount = 0; // Reset if update was recent
                                                    }}
                                                }} else {{
                                                    // Text is still changing
                                                    stableTextCount = 0;
                                                    lastSeenLength = currentContent.length;
                                                }}
                                            }}, 500); // Check every 500ms
                                        }}
                                    }}
                                }});
                            }}
                        }});
                    }});
                    
                    // Start observing
                    observer.observe(document.body, {{
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
                        '[data-testid*="textbox"]',
                        '[data-testid*="input"]'
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
                        document.execCommand('insertText', false, "{message}");
                    }} else {{
                        textarea.value = "";
                        textarea.focus();
                        textarea.value = "{message}";
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
                        'button[type="submit"]',
                        'button:has(svg)',
                        'button[data-testid*="send"]',
                        'button:not([disabled])',
                        '[data-testid*="submit"]'
                    ];
                    
                    let sendButton = null;
                    for (const selector of buttonSelectors) {{
                        const buttons = document.querySelectorAll(selector);
                        for (const button of buttons) {{
                            if (!button.disabled && button.offsetParent !== null) {{
                                // Additional check: button should be visible and clickable
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
                        console.log("Message sent, observer now monitoring for assistant response");
                        
                        // Set timeout with proper cleanup
                        setTimeout(() => {{
                            if (!responseComplete) {{
                                console.log("TIMEOUT: Response incomplete after {timeout} seconds");
                                cleanup();
                                
                                // Send whatever we have as the final response
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
                            # Show debug messages for troubleshooting
                            elif console_message.startswith("ERROR:") or console_message.startswith("COMPLETION_DEBUG:"):
                                print(f"Debug: {console_message}")
                                
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
            
            if not response_started:
                yield {"status": "error", "content": "No response received within timeout period"}
                
    except Exception as e:
        print(f"Error: {e}")
        yield {"status": "error", "content": f"Error: {e}"}

async def send_message_with_observer(message, timeout=120):  # Increased timeout
    """Original function that waits for complete response"""
    final_response = None
    async for response in send_message_with_streaming(message, timeout):
        if response["status"] in ["complete", "timeout", "error"]:
            final_response = response["content"]
            break
    
    return final_response if final_response else "No response received"

# Usage examples
async def main():
    message = "Hello! show me larger wxpython sample"
    
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
