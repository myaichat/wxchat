import websocket
import json
import sys
import time
import re
import pychrome

# Check if question was provided as argument
if len(sys.argv) < 2:
    print("❌ Usage: python grok_cdp_pychrome_hybrid_streaming_test.py \"Your question here\"")
    print("📝 Example: python grok_cdp_pychrome_hybrid_streaming_test.py \"What is the weather like today?\"")
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

def extract_new_content(current_content, previous_content, question):
    """Extract only the new content that appeared since last check"""
    if not previous_content:
        return ""
    
    # Find the question position in both contents
    if question not in current_content:
        return ""
    
    question_pos_current = current_content.rfind(question)
    question_pos_previous = previous_content.rfind(question) if question in previous_content else -1
    
    if question_pos_previous == -1:
        # Question wasn't in previous content, extract everything after question
        text_after_question = current_content[question_pos_current + len(question):]
    else:
        # Question was in previous content, find what's new
        text_after_question_current = current_content[question_pos_current + len(question):]
        text_after_question_previous = previous_content[question_pos_previous + len(question):]
        
        # Find the new part
        if len(text_after_question_current) > len(text_after_question_previous):
            new_text = text_after_question_current[len(text_after_question_previous):]
            return new_text
        else:
            return ""
    
    # Filter and return meaningful new content
    lines = text_after_question.split('\n')
    meaningful_lines = []
    
    for line in lines[:50]:  # Check first 50 lines
        line = line.strip()
        if (len(line) > 3 and  # Very short threshold for streaming
            not line in ['How can Grok help?', 'DeepSearch', 'Think', 'Send', 'Upload', 'Grok 3', 'Upgrade to SuperGrok', 'Think Harder'] and
            not re.match(r'^\d+[smh]$', line) and
            not line.isdigit() and
            not line in ['Copy', 'Wrap', 'Collapse']):
            meaningful_lines.append(line)
    
    return '\n'.join(meaningful_lines) if meaningful_lines else ""

def stream_grok_response(timeout=180):
    """Stream Grok's response in real-time using PyChrome"""
    print(f"🔄 Starting real-time streaming (timeout: {timeout}s)...")
    print("=" * 60)
    print("🤖 GROK STREAMING RESPONSE:")
    print("=" * 60)
    
    # Wait a bit for the message to be processed
    time.sleep(2)
    
    # Debug: Let's inspect the DOM structure to find the right selectors
    debug_expr = """
    (() => {
        // Find all possible containers that might hold the response
        const allDivs = document.querySelectorAll('div');
        const candidates = [];
        
        allDivs.forEach((div, index) => {
            const text = div.innerText || div.textContent || '';
            if (text.length > 100 && text.length < 10000) {  // Reasonable response length
                candidates.push({
                    index: index,
                    className: div.className || 'no-class',
                    id: div.id || 'no-id',
                    dataTestId: div.getAttribute('data-testid') || 'no-testid',
                    role: div.getAttribute('role') || 'no-role',
                    textLength: text.length,
                    textPreview: text.substring(0, 100) + '...'
                });
            }
        });
        
        return {
            totalDivs: allDivs.length,
            candidates: candidates.slice(-5)  // Last 5 candidates
        };
    })()
    """
    
    debug_result = pychrome_tab.call_method("Runtime.evaluate", expression=debug_expr, returnByValue=True)
    debug_info = debug_result.get('result', {}).get('value', {})
    print(f"🔍 DOM Debug Info: {json.dumps(debug_info, indent=2)}")
    
    # Based on debug info, let's target the main content area more precisely
    content_expr = """
    (() => {
        // First, try to find the main conversation/chat container
        const mainSelectors = [
            'main',
            '[role="main"]',
            '.conversation',
            '.chat-container',
            '#chat',
            '.messages'
        ];
        
        for (const selector of mainSelectors) {
            const element = document.querySelector(selector);
            if (element) {
                const text = element.innerText || element.textContent || '';
                if (text.length > 1000) {  // Must be substantial content
                    console.log('Found main container with selector:', selector, 'Length:', text.length);
                    return text;
                }
            }
        }
        
        // If no main container, find the element with the most text content
        // that's likely to be the response area (not code blocks or UI elements)
        const allElements = document.querySelectorAll('div, article, section');
        let bestElement = null;
        let maxLength = 0;
        
        allElements.forEach(el => {
            // Skip elements that are clearly code blocks or UI
            const className = el.className || '';
            if (className.includes('not-prose') || className.includes('code-block')) {
                return;
            }
            
            const text = el.innerText || el.textContent || '';
            // Look for elements with substantial content (likely the main response)
            if (text.length > maxLength && text.length > 1000 && text.length < 100000) {
                maxLength = text.length;
                bestElement = el;
            }
        });
        
        if (bestElement) {
            console.log('Found best element with length:', maxLength);
            return bestElement.innerText || bestElement.textContent || '';
        }
        
        // Final fallback - but this will include UI garbage
        console.log('Falling back to body text');
        return document.body.innerText || '';
    })()
    """
    
    result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get initial page content. Result: {result}")
    
    previous_content = result['result']['value']
    previous_length = len(previous_content)
    
    start_time = time.time()
    stable_count = 0
    total_streamed = ""
    last_content_time = time.time()
    
    while time.time() - start_time < timeout:
        time.sleep(1)  # Check every 1 second for real-time streaming
        
        # Get current content using the same smart extraction
        result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
        current_content = result.get('result', {}).get('value', '')
        current_length = len(current_content)
        
        # If content has grown, print the new part
        if current_length > previous_length:
            # Get the new content that was added
            new_content = current_content[previous_length:]
            
            # Print it immediately
            print(new_content, end='', flush=True)
            total_streamed += new_content
            
            # Update tracking variables
            previous_content = current_content
            previous_length = current_length
            last_content_time = time.time()
            stable_count = 0
        else:
            stable_count += 1
        
        # Stop conditions
        if stable_count >= 15:  # 15 seconds of no new content
            print(f"\n\n⏸️  [STREAM ENDED - No new content for {stable_count} seconds]")
            break
        elif time.time() - last_content_time > 30:  # 30 seconds since last content
            print(f"\n\n⏸️  [STREAM ENDED - No new content for {time.time() - last_content_time:.1f} seconds]")
            break
    
    print("\n" + "=" * 60)
    print(f"✅ Streaming completed! Total content streamed: {len(total_streamed)} characters")
    print(f"⏱️  Total streaming time: {time.time() - start_time:.1f} seconds")
    
    return total_streamed

print("🤖 GROK CDP + PYCHROME HYBRID STREAMING TEST")
print("=" * 60)
print(f"❓ Question: {question}")
print("=" * 60)

try:
    # Enable CDP domains
    send_cdp_command("Runtime.enable", {}, 1)
    send_cdp_command("DOM.enable", {}, 2)
    
    # Send the message using CDP
    if send_message_to_grok_cdp(question):
        # Stream the response using PyChrome
        streamed_response = stream_grok_response(180)
        
        if streamed_response:
            print(f"\n🎉 SUCCESS! Hybrid streaming approach worked!")
            print(f"📊 Total response length: {len(streamed_response)} characters")
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
    
    print("\n✅ Hybrid streaming test completed!")
