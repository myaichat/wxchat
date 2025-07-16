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

async def send_message_with_streaming(message, timeout=120):  # Increased timeout
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
                    let lastTextLength = 0;
                    let stableCount = 0;
                    
                    // Enhanced function to extract text from element
                    function extractText(element) {{
                        if (!element) return '';
                        
                        let text = '';
                        
                        // Try multiple extraction methods
                        const methods = [
                            () => element.innerText,
                            () => element.textContent,
                            () => {{
                                // Get text from all text nodes recursively
                                const walker = document.createTreeWalker(
                                    element,
                                    NodeFilter.SHOW_TEXT,
                                    null,
                                    false
                                );
                                let texts = [];
                                let node;
                                while (node = walker.nextNode()) {{
                                    texts.push(node.textContent);
                                }}
                                return texts.join('');
                            }},
                            () => {{
                                // Get text from specific content elements
                                const contentElements = element.querySelectorAll('p, div, span, pre, code, li, h1, h2, h3, h4, h5, h6, blockquote');
                                return Array.from(contentElements).map(el => el.textContent || el.innerText).join('\\n');
                            }}
                        ];
                        
                        for (const method of methods) {{
                            try {{
                                const result = method();
                                if (result && result.trim().length > text.length) {{
                                    text = result;
                                }}
                            }} catch (e) {{
                                // Continue to next method
                            }}
                        }}
                        
                        return text.trim();
                    }}
                    
                    // Improved function to get actual response content
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
                        if (text.length < 5) return false;
                        
                        const systemMessages = [
                            'Could not find the language',
                            'did you forget to load/include a language module',
                            'Intercom not booted',
                            'Loading...',
                            'Thinking...'
                        ];
                        
                        for (const sysMsg of systemMessages) {{
                            if (text.includes(sysMsg)) return false;
                        }}
                        
                        return true;
                    }}
                    
                    // Enhanced function to check if this is an assistant message
                    function isAssistantMessage(element) {{
                        // Look for specific assistant indicators
                        const assistantSelectors = [
                            '[data-message-author-role="assistant"]',
                            '[data-author="assistant"]',
                            '[data-role="assistant"]',
                            '[data-testid*="assistant"]',
                            '.assistant-message',
                            '.ai-message',
                            '.bot-message'
                        ];
                        
                        for (const selector of assistantSelectors) {{
                            if (element.querySelector(selector) || element.matches(selector)) {{
                                return true;
                            }}
                        }}
                        
                        // Check parent elements too
                        let parent = element.parentElement;
                        let depth = 0;
                        while (parent && depth < 5) {{
                            for (const selector of assistantSelectors) {{
                                if (parent.matches(selector)) {{
                                    return true;
                                }}
                            }}
                            parent = parent.parentElement;
                            depth++;
                        }}
                        
                        // Check if this appears after our sent message and has meaningful content
                        const elementText = getResponseContent(element);
                        if (elementText && elementText.length > 10 && 
                            !elementText.includes("{message}") && 
                            messageSent && 
                            isValidResponse(elementText)) {{
                            return true;
                        }}
                        
                        return false;
                    }}
                    
                    // More conservative completion detection
                    function checkIfComplete(element) {{
                        const text = getResponseContent(element);
                        
                        // Don't consider complete if text is very short
                        if (text.length < 20) return false;
                        
                        // Primary completion indicators
                        const completionIndicators = [
                            'button[aria-label*="Copy"]',
                            'button[data-testid*="copy"]',
                            '[data-testid="copy-turn-action-button"]',
                            'button[title*="Copy"]',
                            'button[aria-label="Copy message"]',
                            'button[aria-label="Regenerate response"]',
                            '.response-actions',
                            '.message-actions',
                            '[data-testid="message-actions"]'
                        ];
                        
                        let hasCompletionIndicator = false;
                        for (const indicator of completionIndicators) {{
                            if (element.querySelector(indicator) || 
                                document.querySelector(indicator)) {{
                                hasCompletionIndicator = true;
                                break;
                            }}
                        }}
                        
                        // Check if text appears to end naturally
                        const endsNaturally = /[.!?]\\s*$/.test(text.trim()) || 
                                             (text.includes('```') && text.lastIndexOf('```') > text.indexOf('```'));
                        
                        // More lenient completion check
                        return hasCompletionIndicator || endsNaturally;
                    }}
                    
                    // Set up mutation observer BEFORE sending message
                    observer = new MutationObserver(function(mutations) {{
                        if (!messageSent) return;
                        
                        mutations.forEach(function(mutation) {{
                            if (mutation.type === 'childList') {{
                                mutation.addedNodes.forEach(function(node) {{
                                    if (node.nodeType === Node.ELEMENT_NODE && !responseFound) {{
                                        if (isAssistantMessage(node)) {{
                                            responseFound = true;
                                            responseElement = node;
                                            console.log("RESPONSE_STARTED");
                                            
                                            const initialContent = getResponseContent(responseElement);
                                            if (initialContent && isValidResponse(initialContent)) {{
                                                lastResponseText = initialContent;
                                                lastTextLength = initialContent.length;
                                                console.log("RESPONSE_UPDATE:" + initialContent);
                                            }}
                                            
                                            // Monitor this specific element for changes
                                            const responseObserver = new MutationObserver(function(responseMutations) {{
                                                const currentContent = getResponseContent(responseElement);
                                                
                                                if (currentContent !== lastResponseText) {{
                                                    lastResponseText = currentContent;
                                                    console.log("RESPONSE_UPDATE:" + currentContent);
                                                    lastTextLength = currentContent.length;
                                                    stableCount = 0; // Reset stability counter
                                                }}
                                            }});
                                            
                                            responseObserver.observe(responseElement, {{
                                                childList: true,
                                                subtree: true,
                                                characterData: true,
                                                attributes: true
                                            }});
                                            
                                            // Aggressive polling for streaming updates
                                            const streamingPoll = setInterval(() => {{
                                                if (responseComplete) {{
                                                    clearInterval(streamingPoll);
                                                    return;
                                                }}
                                                
                                                const currentContent = getResponseContent(responseElement);
                                                if (currentContent !== lastResponseText) {{
                                                    lastResponseText = currentContent;
                                                    console.log("RESPONSE_UPDATE:" + currentContent);
                                                    lastTextLength = currentContent.length;
                                                    stableCount = 0;
                                                }}
                                            }}, 50); // Check every 50ms
                                            
                                            // Conservative completion check with longer stability requirement
                                            const completionCheck = setInterval(() => {{
                                                if (responseComplete) {{
                                                    clearInterval(completionCheck);
                                                    return;
                                                }}
                                                
                                                const currentContent = getResponseContent(responseElement);
                                                const currentLength = currentContent.length;
                                                
                                                // Check if text is stable
                                                if (currentContent === lastResponseText && currentLength === lastTextLength) {{
                                                    stableCount++;
                                                    console.log(`COMPLETION_CHECK: stable=${{stableCount}}, length=${{currentLength}}`);
                                                    
                                                    // Require 40 stable checks (20 seconds) AND minimum length
                                                    if (stableCount >= 40 && currentLength > 50) {{
                                                        // Additional check - look for completion indicators
                                                        const hasCompletionMarkers = checkIfComplete(responseElement);
                                                        
                                                        if (hasCompletionMarkers || stableCount >= 60) {{ // 30 seconds if no markers
                                                            responseComplete = true;
                                                            console.log("RESPONSE_COMPLETE:" + currentContent);
                                                            responseObserver.disconnect();
                                                            clearInterval(completionCheck);
                                                            clearInterval(streamingPoll);
                                                            window.chatObserverActive = false;
                                                        }}
                                                    }}
                                                }} else {{
                                                    // Text is still changing
                                                    lastResponseText = currentContent;
                                                    lastTextLength = currentLength;
                                                    stableCount = 0;
                                                    
                                                    // Send update if content changed
                                                    if (currentContent.length > 0) {{
                                                        console.log("RESPONSE_UPDATE:" + currentContent);
                                                    }}
                                                }}
                                            }}, 500);
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
                        '[contenteditable="true"]'
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
                        observer.disconnect();
                        window.chatObserverActive = false;
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
                        'button[title*="Send"]'
                    ];
                    
                    let sendButton = null;
                    for (const selector of buttonSelectors) {{
                        const buttons = document.querySelectorAll(selector);
                        for (const button of buttons) {{
                            if (!button.disabled && button.offsetParent !== null) {{
                                sendButton = button;
                                console.log("Found send button with selector: " + selector);
                                break;
                            }}
                        }}
                        if (sendButton) break;
                    }}
                    
                    if (sendButton && !sendButton.disabled) {{
                        sentMessageTimestamp = Date.now();
                        messageSent = true;
                        sendButton.click();
                        console.log("Message sent, observer now monitoring for assistant response");
                        
                        // Set timeout with much longer duration
                        setTimeout(() => {{
                            if (!responseComplete) {{
                                console.log("TIMEOUT: Response incomplete after " + {timeout} + " seconds");
                                const finalContent = responseElement ? getResponseContent(responseElement) : "";
                                if (finalContent) {{
                                    console.log("RESPONSE_COMPLETE:" + finalContent);
                                }}
                                observer.disconnect();
                                window.chatObserverActive = false;
                            }}
                        }}, {timeout * 1000});
                        
                        return "Message sent, streaming observer active";
                    }} else {{
                        observer.disconnect();
                        window.chatObserverActive = false;
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
                            # Suppress debug messages - only show important ones
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
    message = "Hello! show me larger pl/sql sample"
    
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
