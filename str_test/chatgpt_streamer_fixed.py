import asyncio
import websockets
import json
from typing import AsyncGenerator

class ChatGPTStreamer:
    """Standalone module for ChatGPT streaming functionality via WebSocket"""
    
    def __init__(self, ws_url: str = "ws://localhost:9222/devtools/page/88E0A660C0870B92DD1E7248EDABA645"):
        self.ws_url = ws_url
    
    async def _wait_for_response(self, websocket, command_id):
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

    def _generate_observer_js(self, message: str, timeout: int) -> str:
        """Generate JavaScript code for DOM observation and message sending"""
        return f'''
            (async function() {{
                // Prevent multiple executions
                if (window.chatObserverActive) {{
                    console.log("Observer already active, skipping");
                    return "Observer already running";
                }}
                window.chatObserverActive = true;
                
                console.log("Setting up streaming observer with improved completion detection");
                
                let messageSent = false;
                let responseFound = false;
                let responseComplete = false;
                let observer;
                let lastResponseText = "";
                let responseElement = null;
                let sentMessageTimestamp = 0;
                let lastUpdateTime = Date.now();
                
                // Function to extract text from element
                function extractText(element) {{
                    if (!element) return '';
                    
                    // Try different methods to get text content
                    let text = element.innerText || element.textContent || '';
                    
                    // If still empty, try to get text from child elements
                    if (!text.trim()) {{
                        const textElements = element.querySelectorAll('p, div, span, pre, code');
                        text = Array.from(textElements).map(el => el.textContent).join(' ');
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
                    if (text.length < 5) return false;  // Reduced from 10 to 5
                    
                    // Filter out common system messages
                    const systemMessages = [
                        'Could not find the language',
                        'did you forget to load/include a language module',
                        'Intercom not booted'
                    ];
                    
                    for (const sysMsg of systemMessages) {{
                        if (text.includes(sysMsg)) return false;
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
                        '[data-testid*="assistant"]'
                    ];
                    
                    for (const indicator of assistantIndicators) {{
                        if (element.querySelector(indicator) || element.matches(indicator)) {{
                            return true;
                        }}
                    }}
                    
                    // Check if this appears after our sent message and doesn't contain our sent text
                    const elementText = getResponseContent(element);
                    if (elementText && elementText.length > 5 && !elementText.includes("{message}") && messageSent) {{
                        return true;
                    }}
                    
                    return false;
                }}
                
                // Improved completion detection with multiple strategies
                function checkIfComplete(element) {{
                    const text = getResponseContent(element);
                    
                    // Strategy 1: Look for UI completion indicators
                    const primaryIndicators = [
                        'button[aria-label*="Copy"]',
                        'button[data-testid*="copy"]',
                        '[data-testid="copy-turn-action-button"]',
                        'button[title*="Copy"]',
                        'button[aria-label="Copy message"]',
                        'button[aria-label="Regenerate response"]'
                    ];
                    
                    let hasPrimaryIndicator = false;
                    for (const indicator of primaryIndicators) {{
                        if (element.querySelector(indicator)) {{
                            hasPrimaryIndicator = true;
                            break;
                        }}
                    }}
                    
                    // Strategy 2: Check if text ends naturally
                    const endsNaturally = /[.!?]\\s*$/.test(text.trim()) || 
                                         (text.includes('```') && text.lastIndexOf('```') > text.indexOf('```')) ||
                                         text.endsWith('💻🤒') ||  // Specific to the joke response
                                         /[.!?]\\s*$/.test(text.trim()); // Ends with punctuation
                    
                    // Strategy 3: Check for content stability (no changes for a while)
                    const now = Date.now();
                    const stableForTime = now - lastUpdateTime > 5000; // Increased to 5 seconds of stability
                    
                    // Strategy 4: Minimum content length check
                    const hasMinimumContent = text.length > 50; // Increased minimum length
                    
                    console.log(`COMPLETION_CHECK: hasPrimary=${{hasPrimaryIndicator}}, endsNaturally=${{endsNaturally}}, stable=${{stableForTime}}, minContent=${{hasMinimumContent}}, textLength=${{text.length}}`);
                    
                    // Disable automatic completion - only rely on fallback timeout
                    return false;
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
                                        console.log("RESPONSE_STARTED");
                                        
                                        // Send initial update if valid
                                        const initialContent = getResponseContent(responseElement);
                                        if (initialContent && isValidResponse(initialContent)) {{
                                            lastResponseText = initialContent;
                                            lastUpdateTime = Date.now();
                                            console.log("RESPONSE_UPDATE:" + initialContent);
                                        }}
                                        
                                        // Start monitoring this specific element for changes
                                        const responseObserver = new MutationObserver(function(responseMutations) {{
                                            const currentContent = getResponseContent(responseElement);
                                            
                                            // Always send update if content changed
                                            if (currentContent !== lastResponseText && currentContent.length > 0) {{
                                                lastResponseText = currentContent;
                                                lastUpdateTime = Date.now();
                                                console.log("RESPONSE_UPDATE:" + currentContent);
                                            }}
                                            
                                            // Check if response is complete
                                            if (!responseComplete && currentContent.length > 10 && checkIfComplete(responseElement)) {{
                                                responseComplete = true;
                                                console.log("RESPONSE_COMPLETE:" + currentContent);
                                                responseObserver.disconnect();
                                                window.chatObserverActive = false;
                                            }}
                                        }});
                                        
                                        responseObserver.observe(responseElement, {{
                                            childList: true,
                                            subtree: true,
                                            characterData: true
                                        }});
                                        
                                        // Frequent polling for streaming updates
                                        const streamingPoll = setInterval(() => {{
                                            if (responseComplete) {{
                                                clearInterval(streamingPoll);
                                                return;
                                            }}
                                            
                                            const currentContent = getResponseContent(responseElement);
                                            if (currentContent !== lastResponseText && currentContent.length > 0) {{
                                                lastResponseText = currentContent;
                                                lastUpdateTime = Date.now();
                                                console.log("RESPONSE_UPDATE:" + currentContent);
                                            }}
                                        }}, 100); // Check every 100ms
                                        
                                        // Completion check with multiple strategies
                                        const completionCheck = setInterval(() => {{
                                            if (responseComplete) {{
                                                clearInterval(completionCheck);
                                                return;
                                            }}
                                            
                                            const currentContent = getResponseContent(responseElement);
                                            
                                            // Update lastUpdateTime if content changed
                                            if (currentContent !== lastResponseText) {{
                                                lastUpdateTime = Date.now();
                                                lastResponseText = currentContent;
                                                console.log("RESPONSE_UPDATE:" + currentContent);
                                            }}
                                            
                                            // Check for completion using multiple strategies
                                            if (currentContent.length > 10 && checkIfComplete(responseElement)) {{
                                                responseComplete = true;
                                                console.log("RESPONSE_COMPLETE:" + currentContent);
                                                responseObserver.disconnect();
                                                clearInterval(completionCheck);
                                                clearInterval(streamingPoll);
                                                window.chatObserverActive = false;
                                            }}
                                        }}, 1000); // Check every second
                                        
                                        // Fallback timeout - force completion after extended period
                                        setTimeout(() => {{
                                            if (!responseComplete && lastResponseText.length > 10) {{
                                                console.log("FALLBACK_TIMEOUT: Forcing completion due to timeout");
                                                responseComplete = true;
                                                console.log("RESPONSE_COMPLETE:" + lastResponseText);
                                                responseObserver.disconnect();
                                                clearInterval(streamingPoll);
                                                clearInterval(completionCheck);
                                                window.chatObserverActive = false;
                                            }}
                                        }}, {timeout * 1000 - 2000}); // 2 seconds before main timeout
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
                    'div[contenteditable="true"]'
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
                const events = ['input', 'change', 'keyup'];
                events.forEach(eventType => {{
                    textarea.dispatchEvent(new Event(eventType, {{ bubbles: true, cancelable: true }}));
                }});
                
                // Wait for interface to process
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Find send button
                const buttonSelectors = [
                    'button[data-testid="send-button"]',
                    'button[aria-label*="Send"]',
                    'button[type="submit"]',
                    'button:has(svg)',
                    'button[data-testid*="send"]'
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
                    
                    // Main timeout
                    setTimeout(() => {{
                        if (!responseComplete) {{
                            console.log("TIMEOUT: Response incomplete");
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

    async def send_message_with_streaming(self, message: str, timeout: int = 60) -> AsyncGenerator[dict, None]:
        """Generator that yields streaming responses as they arrive"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print("Connected to WebSocket")
                
                # Enable Runtime domain
                await websocket.send(json.dumps({
                    "id": 1,
                    "method": "Runtime.enable"
                }))
                await self._wait_for_response(websocket, 1)
                
                # Set up mutation observer for streaming responses
                observer_js = self._generate_observer_js(message, timeout)
                
                await websocket.send(json.dumps({
                    "id": 3,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": observer_js,
                        "returnByValue": True
                    }
                }))
                
                eval_response = await self._wait_for_response(websocket, 3)
                print(f"Observer setup result: {eval_response}")
                
                # Wait for streaming responses
                print(f"Waiting up to {timeout} seconds for streaming response...")
                
                start_time = asyncio.get_event_loop().time()
                response_started = False
                response_complete = False
                last_activity_time = start_time
                
                while (asyncio.get_event_loop().time() - start_time) < timeout and not response_complete:
                    try:
                        message_data = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message_data)
                        
                        if data.get("method") == "Runtime.consoleAPICalled":
                            args = data.get("params", {}).get("args", [])
                            if args:
                                console_message = args[0].get("value", "")
                                
                                if console_message == "RESPONSE_STARTED":
                                    response_started = True
                                    last_activity_time = asyncio.get_event_loop().time()
                                    print("\n=== RESPONSE STARTED (streaming) ===")
                                    yield {"status": "started", "content": ""}
                                    
                                elif console_message.startswith("RESPONSE_UPDATE:"):
                                    if response_started:
                                        content = console_message.replace("RESPONSE_UPDATE:", "")
                                        last_activity_time = asyncio.get_event_loop().time()
                                        yield {"status": "streaming", "content": content}
                                        
                                elif console_message.startswith("RESPONSE_COMPLETE:") or console_message.startswith("FALLBACK_TIMEOUT:"):
                                    if console_message.startswith("RESPONSE_COMPLETE:"):
                                        content = console_message.replace("RESPONSE_COMPLETE:", "")
                                    else:
                                        # For fallback timeout, get the last content
                                        content = ""  # Will be handled by the last streaming update
                                    print(f"\n=== RESPONSE COMPLETE ===")
                                    print(f"Final response length: {len(content)} characters")
                                    response_complete = True
                                    yield {"status": "complete", "content": content}
                                    break
                                    
                                elif console_message == "TIMEOUT: Response incomplete":
                                    print("Observer timed out")
                                    yield {"status": "timeout", "content": ""}
                                    break
                                # Suppress debug messages - only show important ones
                                elif console_message.startswith("ERROR:") or console_message.startswith("TIMEOUT:"):
                                    print(f"Debug: {console_message}")
                                    
                    except asyncio.TimeoutError:
                        # Check for inactivity timeout (no messages for 15 seconds)
                        current_time = asyncio.get_event_loop().time()
                        if response_started and (current_time - last_activity_time) > 15:
                            print("No activity for 15 seconds, assuming response is complete")
                            response_complete = True
                            yield {"status": "complete", "content": ""} 
                            break
                        continue
                    except json.JSONDecodeError:
                        continue
                
                if not response_started:
                    yield {"status": "error", "content": "No response received within timeout period"}
                    
        except Exception as e:
            print(f"Error: {e}")
            yield {"status": "error", "content": f"Error: {e}"}

    async def send_message_complete(self, message: str, timeout: int = 60) -> str:
        """Send message and wait for complete response (non-streaming)"""
        final_response = None
        async for response in self.send_message_with_streaming(message, timeout):
            if response["status"] in ["complete", "timeout", "error"]:
                final_response = response["content"]
                break
        
        return final_response if final_response else "No response received"
