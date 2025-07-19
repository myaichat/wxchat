import websocket
import json
import time
import re

# WebSocket URL from the provided JSON
ws_url = "ws://localhost:9222/devtools/page/26F411DF5B6CF6C6EA8CB688C5E84F5F"

# Initialize WebSocket connection
ws = websocket.create_connection(ws_url)

# Helper to send CDP commands
def send_cdp_command(method, params, command_id):
    command = {"id": command_id, "method": method, "params": params}
    ws.send(json.dumps(command))
    
    # Keep receiving until we get the response with matching ID
    while True:
        response = json.loads(ws.recv())
        # Check if this is the response we're looking for
        if 'id' in response and response['id'] == command_id:
            return response
        # If it's an event or other message, continue listening
        elif 'method' in response:
            # Only print important events to reduce noise
            if response['method'] in ['DOM.childNodeCountUpdated', 'DOM.subtreeModified', 'Network.webSocketFrameReceived']:
                print(f"Important event: {response['method']}")
            continue
        else:
            print(f"Received unexpected message: {response}")
            continue

# Improved text extraction using Runtime.evaluate
def get_element_text_content(node_id, command_id):
    """Get text content of an element using JavaScript evaluation"""
    try:
        response = send_cdp_command(
            "Runtime.evaluate",
            {
                "expression": f"""
                (function() {{
                    const element = document.querySelector('[data-node-id="{node_id}"]') || 
                                   Array.from(document.querySelectorAll('*')).find(el => el.__nodeId === {node_id});
                    return element ? element.textContent.trim() : '';
                }})()
                """,
                "returnByValue": True
            },
            command_id
        )
        if 'result' in response and 'result' in response['result'] and 'value' in response['result']:
            return response['result']['value']
    except Exception as e:
        print(f"Error getting text content: {e}")
    return ""

# Improved function to get text content from a node
def get_node_text(node_id, command_id):
    """Get both HTML and text content from a node"""
    try:
        # Get HTML content
        html_response = send_cdp_command(
            "DOM.getOuterHTML",
            {"nodeId": node_id},
            command_id
        )
        
        if 'result' in html_response and 'outerHTML' in html_response['result']:
            html_content = html_response['result']['outerHTML']
            # Extract text using regex
            text_only = re.sub(r'<[^>]+>', ' ', html_content)
            text_only = ' '.join(text_only.split())  # Clean whitespace
            return {
                'html': html_content,
                'text': text_only
            }
    except Exception as e:
        print(f"Error getting node content: {e}")
    
    return {'html': '', 'text': ''}

# Verify message was sent successfully
def verify_message_sent(message_text, command_id):
    """Verify that our message appears in the chat history"""
    print(f"Verifying sent message: '{message_text}'...")
    
    # Use JavaScript to search for the message
    response = send_cdp_command(
        "Runtime.evaluate",
        {
            "expression": f"""
            Array.from(document.querySelectorAll('*')).filter(el => 
                el.textContent && el.textContent.includes('{message_text}')
            ).length
            """,
            "returnByValue": True
        },
        command_id
    )
    
    if response.get('result', {}).get('result', {}).get('value', 0) > 0:
        print("✅ Sent message found in chat history!")
        return True
    else:
        print("❌ Sent message not found in chat history!")
        return False

# Enhanced monitoring with DOM events and Network monitoring
def monitor_for_response(command_id_start=500, max_wait=45):
    """Monitor for chat responses using multiple detection methods"""
    command_id = command_id_start
    start_time = time.time()
    
    print(f"Enhanced monitoring for Grok's response for {max_wait} seconds...")
    
    # Enable DOM and Network events
    send_cdp_command("DOM.enable", {}, command_id)
    command_id += 1
    
    send_cdp_command("Network.enable", {}, command_id)
    command_id += 1
    
    # Store initial state
    initial_html_response = send_cdp_command("DOM.getOuterHTML", {"nodeId": 1}, command_id)
    command_id += 1
    initial_html = initial_html_response.get('result', {}).get('outerHTML', '')
    initial_length = len(initial_html)
    
    print(f"Initial page length: {initial_length} characters")
    
    while time.time() - start_time < max_wait:
        try:
            # Set a timeout for receiving messages
            ws.settimeout(1.0)
            response = json.loads(ws.recv())
            
            if 'method' in response:
                method = response['method']
                
                # Check for DOM changes
                if method in ['DOM.childNodeCountUpdated', 'DOM.subtreeModified', 'DOM.childNodeInserted']:
                    print(f"🔄 DOM change detected: {method}")
                    
                    # Wait a moment for changes to settle
                    time.sleep(0.5)
                    
                    # Check for new content
                    current_html_response = send_cdp_command("DOM.getOuterHTML", {"nodeId": 1}, command_id)
                    command_id += 1
                    current_html = current_html_response.get('result', {}).get('outerHTML', '')
                    
                    if len(current_html) > initial_length + 100:  # Significant content added
                        print(f"📈 Significant content increase: {initial_length} → {len(current_html)}")
                        
                        # Look for new chat messages using improved selectors
                        potential_selectors = [
                            "div[class*='message']",
                            "div[class*='chat']", 
                            "div[class*='response']",
                            "div[class*='assistant']",
                            "div[class*='bot']",
                            "div[class*='ai']",
                            "article",
                            "div[role='article']",
                            "div[role='listitem']",
                            "div.prose",
                            "div[data-testid*='message']",
                            "div[data-testid*='chat']",
                            "div[data-testid*='response']"
                        ]
                        
                        for selector in potential_selectors:
                            elements_response = send_cdp_command(
                                "DOM.querySelectorAll",
                                {"nodeId": 1, "selector": selector},
                                command_id
                            )
                            command_id += 1
                            
                            node_ids = elements_response.get('result', {}).get('nodeIds', [])
                            if node_ids:
                                print(f"🎯 Found {len(node_ids)} elements with selector: {selector}")
                                
                                # Check the most recent elements
                                for node_id in node_ids[-5:]:  # Check last 5 elements
                                    content = get_node_text(node_id, command_id)
                                    command_id += 1
                                    
                                    text = content['text']
                                    if text and len(text) > 20:  # Substantial content
                                        # Filter out our own message and UI text
                                        if ("Hello, Grok!" not in text and 
                                            "How can Grok help" not in text and
                                            "DeepSearch" not in text and
                                            "Think" not in text and
                                            len(text.strip()) > 30):
                                            
                                            print(f"\n🎉 POTENTIAL RESPONSE FOUND!")
                                            print(f"Selector: {selector}")
                                            print(f"Text: {text[:300]}...")
                                            print(f"HTML: {content['html'][:200]}...")
                                            return True, command_id
                        
                        initial_length = len(current_html)  # Update baseline
                
                # Check for WebSocket frames (if Grok uses WebSocket for responses)
                elif method == 'Network.webSocketFrameReceived':
                    frame_data = response.get('params', {}).get('response', {}).get('payloadData', '')
                    if frame_data and any(keyword in frame_data.lower() for keyword in ['hello', 'hi', 'greetings', 'response']):
                        print(f"🌐 Found potential response in WebSocket frame: {frame_data[:200]}...")
                        return True, command_id
                
                # Check for network responses that might contain chat data
                elif method == 'Network.responseReceived':
                    url = response.get('params', {}).get('response', {}).get('url', '')
                    if any(keyword in url.lower() for keyword in ['chat', 'message', 'response', 'api']):
                        print(f"🌐 Potential chat API response: {url}")
            
            # Reset timeout
            ws.settimeout(None)
            
        except websocket.timeout:
            # Timeout is normal, continue monitoring
            continue
        except Exception as e:
            print(f"Error during monitoring: {e}")
            time.sleep(0.5)
    
    print("⏰ Monitoring timeout reached")
    return False, command_id

# Save page HTML for debugging
def save_page_html(command_id):
    """Save the current page HTML to a file for debugging"""
    html_response = send_cdp_command("DOM.getOuterHTML", {"nodeId": 1}, command_id)
    if 'result' in html_response:
        try:
            with open("grok_page_debug.html", "w", encoding="utf-8") as f:
                f.write(html_response['result']['outerHTML'])
            print("💾 Saved page HTML to grok_page_debug.html for debugging")
        except Exception as e:
            print(f"Error saving HTML: {e}")
    return command_id + 1

# Main execution
command_id = 1

print("🚀 Starting enhanced Grok chat interaction...")

# Enable DOM events early
print("🔧 Enabling DOM and Network monitoring...")
send_cdp_command("DOM.enable", {}, command_id)
command_id += 1

send_cdp_command("Network.enable", {}, command_id)
command_id += 1

# Get document and query the input field
print("📄 Getting document...")
send_cdp_command("DOM.getDocument", {}, command_id)
command_id += 1

print("🔍 Looking for textarea...")
textarea_response = send_cdp_command(
    "DOM.querySelector",
    {"nodeId": 1, "selector": "textarea"},
    command_id
)
command_id += 1

print(f"Textarea query result: {textarea_response}")

if textarea_response.get('result', {}).get('nodeId'):
    textarea_node_id = textarea_response['result']['nodeId']
    print(f"✅ Found textarea with node ID: {textarea_node_id}")
    
    # Focus on the textarea
    send_cdp_command("DOM.focus", {"nodeId": textarea_node_id}, command_id)
    command_id += 1
    
    # Clear any existing text
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Control"}, command_id)
    command_id += 1
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "KeyA"}, command_id)
    command_id += 1
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "KeyA"}, command_id)
    command_id += 1
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Control"}, command_id)
    command_id += 1
    
    # Type the message
    message = "Hello, Grok! Please respond with a simple greeting."
    print(f"⌨️ Typing message: {message}")
    
    for char in message:
        send_cdp_command("Input.dispatchKeyEvent", {"type": "char", "text": char}, command_id)
        command_id += 1
        time.sleep(0.03)  # Slightly faster typing
    
    # Press Enter to send
    print("📤 Pressing Enter to send message...")
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter"}, command_id)
    command_id += 1
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter"}, command_id)
    command_id += 1
    
    # Wait a moment for the message to be processed
    time.sleep(2)
    
    # Verify the message was sent
    message_sent = verify_message_sent(message, command_id)
    command_id += 1
    
    if message_sent:
        # Start enhanced monitoring
        print("🔍 Starting enhanced real-time monitoring...")
        found_response, command_id = monitor_for_response(command_id, max_wait=45)
        
        if found_response:
            print("🎉 Successfully detected Grok's response!")
        else:
            print("⏰ No response detected during monitoring period")
            
            # Save page for debugging
            print("💾 Saving page HTML for debugging...")
            command_id = save_page_html(command_id)
            
            # Try one more comprehensive search
            print("🔍 Performing final comprehensive search...")
            
            # Get all text content and look for patterns
            html_response = send_cdp_command("DOM.getOuterHTML", {"nodeId": 1}, command_id)
            command_id += 1
            
            if 'result' in html_response:
                html_content = html_response['result']['outerHTML']
                print(f"📊 Final page HTML length: {len(html_content)} characters")
                
                # Look for response patterns in the entire page
                response_patterns = [
                    r'(?i)hello[^<]{10,100}',  # Hello followed by 10-100 chars
                    r'(?i)hi[^<]{10,100}',     # Hi followed by 10-100 chars  
                    r'(?i)greetings[^<]{10,100}',  # Greetings followed by content
                    r'(?i)nice to meet[^<]{10,100}',
                    r'(?i)how are you[^<]{10,100}',
                    r'(?i)i\'?m grok[^<]{10,100}'
                ]
                
                for pattern in response_patterns:
                    matches = re.findall(pattern, html_content)
                    if matches:
                        print(f"\n🎯 Found potential response pattern:")
                        for match in matches[:3]:  # Show first 3 matches
                            clean_match = ' '.join(match.split())
                            if len(clean_match) > 15 and "Hello, Grok!" not in clean_match:
                                print(f"   Response: {clean_match[:150]}...")
    else:
        print("❌ Message was not sent successfully - skipping response monitoring")

else:
    print("❌ Could not find textarea element!")

print("\n✅ Script completed.")

# Close WebSocket connection
ws.close()
