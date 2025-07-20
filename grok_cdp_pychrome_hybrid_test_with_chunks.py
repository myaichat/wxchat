import websocket
import json
import sys
import time
import re
import pychrome

# Check if question was provided as argument
if len(sys.argv) < 2:
    print("❌ Usage: python grok_cdp_pychrome_hybrid_test_with_chunks.py \"Your question here\"")
    print("📝 Example: python grok_cdp_pychrome_hybrid_test_with_chunks.py \"What is the weather like today?\"")
    sys.exit(1)

question = sys.argv[1]

# WebSocket URL and tab ID from the provided JSON
ws_url = "ws://localhost:9222/devtools/page/E8CF09D134FAEB497BC8E90CBB705C86"
tab_id = "E8CF09D134FAEB497BC8E90CBB705C86"

def connect_websocket(ws_url):
    """Connect to CDP WebSocket for sending messages"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            ws = websocket.create_connection(ws_url)
            print("✅ CDP WebSocket connected")
            return ws
        except Exception as e:
            print(f"❌ CDP WebSocket connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2)
    raise Exception("Failed to connect to CDP WebSocket after retries")

def connect_pychrome():
    """Connect to browser using pychrome for reading responses"""
    try:
        browser = pychrome.Browser(url="http://localhost:9222")
        tabs = browser.list_tab()
        tab = None
        for t in tabs:
            if t.id == tab_id:
                tab = t
                break
        
        if tab is None:
            raise ValueError("Tab with specified ID not found.")
        
        tab.start()
        tab.call_method("Runtime.enable")
        print("✅ PyChrome connected")
        return browser, tab
    except Exception as e:
        print(f"❌ PyChrome connection failed: {e}")
        raise

# Initialize connections
ws = connect_websocket(ws_url)
browser, pychrome_tab = connect_pychrome()

def send_cdp_command(method, params, command_id):
    """Send CDP command via WebSocket"""
    command = {"id": command_id, "method": method, "params": params}
    ws.send(json.dumps(command))
    
    while True:
        response = json.loads(ws.recv())
        if 'id' in response and response['id'] == command_id:
            return response
        elif 'method' in response:
            continue

def send_message_to_grok_cdp(message):
    """Send a message to Grok via CDP (from original g_ask_grok.py)"""
    print(f"📤 Sending message via CDP: '{message}'")
    
    # Get document
    send_cdp_command("DOM.getDocument", {}, 1)
    
    # Find textarea
    textarea_response = send_cdp_command(
        "DOM.querySelector",
        {"nodeId": 1, "selector": "textarea"},
        2
    )
    
    if not textarea_response.get('result', {}).get('nodeId'):
        print("❌ Could not find textarea!")
        return False
    
    textarea_node_id = textarea_response['result']['nodeId']
    
    # Focus on textarea
    send_cdp_command("DOM.focus", {"nodeId": textarea_node_id}, 3)
    
    # Clear existing text
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Control"}, 4)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "KeyA"}, 5)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "KeyA"}, 6)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Control"}, 7)
    
    # Type the message
    command_id = 8
    for char in message:
        send_cdp_command("Input.dispatchKeyEvent", {"type": "char", "text": char}, command_id)
        command_id += 1
        time.sleep(0.02)
    
    # Press Enter to send
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter"}, command_id)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter"}, command_id + 1)
    
    print("✅ Message sent via CDP!")
    return True

def wait_for_response_pychrome(timeout=180):  # Increased timeout to 3 minutes
    """Wait for and extract Grok's response using PyChrome"""
    print(f"⏳ Waiting for Grok's response via PyChrome (timeout: {timeout}s)...")
    
    # Wait a bit for the message to be processed
    time.sleep(3)
    
    # Get initial page content to establish baseline
    content_expr = "document.body.innerText"
    result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get initial page content. Result: {result}")
    
    initial_content = result['result']['value']
    initial_content_length = len(initial_content)
    print(f"📊 Initial content length: {initial_content_length}")
    
    start_time = time.time()
    last_length = initial_content_length
    last_content = initial_content  # Track previous content for chunk extraction
    stable_count = 0
    reasoning_detected = False
    search_detected = False
    
    print("🔄 Monitoring content changes and detecting Grok's reasoning phase...")
    
    while time.time() - start_time < timeout:
        time.sleep(3)  # Check every 3 seconds for better stability
        
        # Get current content
        result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
        current_content = result.get('result', {}).get('value', '')
        current_length = len(current_content)
        
        # Check for reasoning/thinking indicators
        if any(indicator in current_content.lower() for indicator in 
               ['searching for', 'let me search', 'thinking', 'reasoning', 'quick answer']):
            if not reasoning_detected:
                print("🧠 Detected Grok reasoning/searching phase...")
                reasoning_detected = True
            if 'searching for' in current_content.lower():
                search_detected = True
                print("🔍 Grok is searching for information...")
        
        # Check if content has grown
        if current_length > last_length + 15:  # Content is still growing (increased threshold)
            stable_count = 0
            print(f"📈 Content growing: {current_length} chars (+{current_length - initial_content_length} from start)")
            
            # Show the new chunk that was added
            if len(current_content) > len(last_content):
                new_chunk = current_content[len(last_content):]
                print(f"📦 New chunk received ({len(new_chunk)} chars):")
                print("─" * 60)
                print(new_chunk[:500] + ("..." if len(new_chunk) > 500 else ""))  # Show first 500 chars
                print("─" * 60)
            
            last_length = current_length
            last_content = current_content  # Update last content for next chunk comparison
            continue
        else:
            stable_count += 1
            print(f"⏸️  Content stable for {stable_count * 3} seconds ({current_length} chars)")
        
        # If we detected reasoning/search, wait much longer for stability
        required_stable_checks = 10 if reasoning_detected else 6  # 30 seconds if reasoning, 18 seconds otherwise
        
        # Wait for longer stability to ensure streaming is complete
        if stable_count >= required_stable_checks:
            print(f"✅ Content has been stable for {stable_count * 3} seconds, streaming likely complete")
            break
        
        # Special handling for search responses - wait for substantial content
        if search_detected and current_length < initial_content_length + 1000:
            print("🔍 Search detected but response seems incomplete, continuing to wait...")
            stable_count = 0  # Reset stability counter for search responses
            continue
        
        # Also check if we have a substantial response and it's been stable for a reasonable time
        if (current_length > initial_content_length + 500 and 
            stable_count >= 5 and 
            time.time() - start_time > 20):
            print(f"✅ Substantial content detected and stable for {stable_count * 3}s, extracting...")
            break
    
    # Get final content for extraction
    result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    final_content = result.get('result', {}).get('value', '')
    print(f"📄 Final content length: {len(final_content)} chars")
    
    # If reasoning was detected, give extra time for the actual response
    if reasoning_detected:
        print("🧠 Reasoning was detected, waiting additional time for complete response...")
        time.sleep(10)  # Wait extra 10 seconds
        result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
        final_content = result.get('result', {}).get('value', '')
        print(f"📄 Final content after reasoning wait: {len(final_content)} chars")
    
    # Extract response using multiple PyChrome methods
    response_extraction_methods = [
        # Method 1: Get current page content and extract using Python
        "document.body.innerText",
        
        # Method 2: Look for conversation/message containers
        """
        (() => {
            const containers = document.querySelectorAll('div[data-testid*="conversation"], div[data-testid*="message"], .message, [role="article"]');
            if (containers.length > 0) {
                const lastContainer = containers[containers.length - 1];
                const text = lastContainer.innerText || lastContainer.textContent || '';
                return text.length > 50 ? text : null;
            }
            return null;
        })()
        """,
        
        # Method 3: Get paragraphs that look like responses
        """
        (() => {
            const allText = document.body.innerText;
            const paragraphs = allText.split('\\n\\n');
            
            // Find paragraphs that look like responses
            const responseParagraphs = paragraphs.filter(p => {
                const trimmed = p.trim();
                return trimmed.length > 50 && 
                       !trimmed.includes('How can Grok help') &&
                       !trimmed.includes('DeepSearch') &&
                       !trimmed.includes('Think') &&
                       !trimmed.includes('Send') &&
                       !trimmed.includes('Upload') &&
                       !trimmed.includes('Upgrade to SuperGrok');
            });
            
            return responseParagraphs.slice(-3).join('\\n\\n');
        })()
        """
    ]
    
    response = None
    for i, method in enumerate(response_extraction_methods, 1):
        print(f"🔍 Trying PyChrome extraction method {i}...")
        result = pychrome_tab.call_method("Runtime.evaluate", expression=method, returnByValue=True)
        
        if 'result' in result and 'value' in result['result']:
            if i == 1:  # Method 1 is just getting page content
                page_content = result['result']['value']
                extracted = extract_response_from_content(page_content)
                print(f"📄 Page content length: {len(page_content)}")
                print(f"🔍 Extracted from content: {extracted[:100] if extracted else 'None'}...")
            else:
                extracted = result['result']['value']
            
            if extracted and len(extracted.strip()) > 20:
                response = extracted.strip()
                print(f"✅ PyChrome method {i} successful!")
                break
            else:
                print(f"⚠️  PyChrome method {i} returned: {extracted}")
        else:
            print(f"❌ PyChrome method {i} failed: {result}")
    
    if not response:
        # Fallback: get full page content and try Python extraction
        print("📄 Using PyChrome fallback method...")
        fallback_expr = "document.body.innerText"
        result = pychrome_tab.call_method("Runtime.evaluate", expression=fallback_expr, returnByValue=True)
        
        if 'result' in result and 'value' in result['result']:
            full_content = result['result']['value']
            response = extract_response_from_content(full_content)
            if not response:
                # Last resort: return recent content
                response = full_content[-1000:] if len(full_content) > 1000 else full_content
            print("✅ PyChrome fallback successful")
        else:
            print(f"❌ PyChrome fallback failed: {result}")
    
    return response

def extract_response_from_content(content):
    """Extract response from page content"""
    # Look for text after our question
    if question in content:
        question_pos = content.rfind(question)
        text_after_question = content[question_pos + len(question):]
        
        # Split into lines and filter meaningful content
        lines = text_after_question.split('\n')
        meaningful_lines = []
        
        for line in lines[:200]:  # Increased from 50 to 200 lines to capture more content
            line = line.strip()
            if (len(line) > 5 and  # Reduced from 10 to 5 to capture shorter lines
                not line in ['How can Grok help?', 'DeepSearch', 'Think', 'Send', 'Upload', 'Grok 3', 'Upgrade to SuperGrok', 'Think Harder'] and
                not re.match(r'^\d+[smh]$', line) and
                not line.isdigit() and
                not line in ['Copy', 'Wrap', 'Collapse']):  # Added more UI elements to filter
                meaningful_lines.append(line)
        
        if meaningful_lines:
            return '\n\n'.join(meaningful_lines)  # Return ALL meaningful lines, not just first 10
    
    return None

print("🤖 GROK CDP + PYCHROME HYBRID TEST WITH CHUNKS")
print("=" * 50)
print(f"❓ Question: {question}")
print("=" * 50)

try:
    # Enable CDP domains
    send_cdp_command("Runtime.enable", {}, 1)
    send_cdp_command("DOM.enable", {}, 2)
    
    # Send the message using CDP
    if send_message_to_grok_cdp(question):
        # Wait for and extract response using PyChrome
        response = wait_for_response_pychrome(180)  # 3 minutes timeout for reasoning responses
        
        if response:
            print(f"\n🎉 SUCCESS! Hybrid approach worked!")
            print("=" * 50)
            print("🤖 GROK RESPONSE:")
            print("=" * 50)
            print(response)
            print("=" * 50)
        else:
            print("\n❌ No response received within timeout period")
    else:
        print("❌ Failed to send message via CDP")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Clean up connections without closing the tab
    try:
        ws.close()
        print("✅ CDP WebSocket closed")
    except:
        pass
    
    try:
        pychrome_tab.stop()
        print("✅ PyChrome connection stopped (tab remains open)")
    except:
        pass
    
    print("\n✅ Hybrid test completed!")
