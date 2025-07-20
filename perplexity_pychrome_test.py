import pychrome
import time
import re
import requests
import json

def find_perplexity_tab():
    """Find an existing Perplexity tab"""
    try:
        response = requests.get("http://localhost:9222/json")
        tab_list = response.json()
        print(f"🔍 Found {len(tab_list)} tabs")
        
        # Look for a real Perplexity tab
        for tab_info in tab_list:
            url = tab_info.get('url', '')
            title = tab_info.get('title', '')
            
            if ('perplexity.ai' in url.lower() and 
                'stripe.network' not in url.lower() and
                'service_worker' not in url.lower() and
                'iframe' not in url.lower() and
                tab_info.get('type') == 'page'):
                
                print(f"📱 Found Perplexity tab: {title} - {url}")
                return tab_info
        
        print("❌ No suitable Perplexity tab found")
        print("Please open https://www.perplexity.ai in a Chrome tab and try again")
        return None
        
    except Exception as e:
        print(f"❌ Error finding tabs: {e}")
        return None

# Find existing Perplexity tab
tab_info = find_perplexity_tab()
if not tab_info:
    exit(1)

# Connect to browser and get the tab
browser = pychrome.Browser(url="http://localhost:9222")
tabs = browser.list_tab()
tab = None
for t in tabs:
    if t.id == tab_info['id']:
        tab = t
        break

if not tab:
    print("❌ Could not connect to the Perplexity tab")
    exit(1)

# Start the tab
tab.start()

# Enable necessary domains
tab.call_method("Runtime.enable")

# Test connection
try:
    result = tab.call_method("Runtime.evaluate", 
                            expression="document.title", 
                            returnByValue=True)
    title = result.get('result', {}).get('value', 'Unknown')
    print(f"✅ Connected to tab: {title}")
except Exception as e:
    print(f"❌ Connection test failed: {e}")
    exit(1)

def ask_question(question, timeout=120):
    print(f"📤 Sending message: '{question}'")
    
    # Use the correct selector for Perplexity's contenteditable div (non-async version)
    js_code = f"""
    (function() {{
        // Look for the contenteditable div with role="textbox" or ID "ask-input"
        const inputElement = document.querySelector('#ask-input') || 
                           document.querySelector('[role="textbox"]') || 
                           document.querySelector('[contenteditable="true"]');
        
        if (!inputElement) {{
            return 'No input element found';
        }}
        
        // Focus on the element
        inputElement.focus();
        
        // Clear existing content and insert new text
        inputElement.innerHTML = '';
        inputElement.textContent = '{question.replace("'", "\\'").replace('\\', '\\\\')}';
        
        // Dispatch input events
        inputElement.dispatchEvent(new Event('input', {{ bubbles: true, composed: true }}));
        inputElement.dispatchEvent(new Event('change', {{ bubbles: true, composed: true }}));
        
        return 'Text inserted successfully';
    }})();
    """
    
    # First, insert the text
    try:
        result = tab.call_method("Runtime.evaluate", 
                                expression=js_code, 
                                returnByValue=True)
        
        insert_result = result.get('result', {}).get('value', 'No return value')
        print(f"✅ Insert result: {insert_result}")
        
        if 'No input element found' in insert_result:
            return None
            
    except Exception as e:
        print(f"❌ Error inserting text: {e}")
        return None
    
    # Wait a moment for the UI to update
    time.sleep(0.5)
    
    # Now try to submit
    submit_js = """
    (function() {{
        // Look for submit button
        const buttonSelectors = [
            'button[aria-label*="Submit"]',
            'button[type="submit"]', 
            'button[class*="submit"]',
            'button.absolute.right',
            'button:has(> svg)',
            'button:has(svg)',
            'button[data-testid*="submit"]',
            'button[title*="Submit"]',
            'button[title*="Send"]'
        ];
        
        let submitButton = null;
        for (const selector of buttonSelectors) {{
            try {{
                submitButton = document.querySelector(selector);
                if (submitButton) break;
            }} catch(e) {{
                continue;
            }}
        }}
        
        if (submitButton) {{
            submitButton.click();
            return 'Clicked submit button';
        }} else {{
            // Get the input element again and simulate Enter key press
            const inputElement = document.querySelector('#ask-input') || 
                               document.querySelector('[role="textbox"]') || 
                               document.querySelector('[contenteditable="true"]');
            
            if (inputElement) {{
                const eventOpts = {{ bubbles: true, composed: true, key: 'Enter', code: 'Enter', which: 13, keyCode: 13, shiftKey: false }};
                inputElement.dispatchEvent(new KeyboardEvent('keydown', eventOpts));
                inputElement.dispatchEvent(new KeyboardEvent('keypress', eventOpts));
                inputElement.dispatchEvent(new KeyboardEvent('keyup', eventOpts));
                return 'Simulated Enter key press on contenteditable div';
            }} else {{
                return 'Could not find input element for Enter key simulation';
            }}
        }}
    }})();
    """
    
    try:
        result = tab.call_method("Runtime.evaluate", 
                                expression=submit_js, 
                                returnByValue=True)
        
        submit_result = result.get('result', {}).get('value', 'No return value')
        print(f"✅ Submit result: {submit_result}")
        
        # Wait for response
        return wait_for_new_answer(timeout)
        
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return None

def get_answer_count():
    """Get the count of answer elements"""
    js = 'document.querySelectorAll(\'[class*="prose"]\').length'
    result = tab.call_method("Runtime.evaluate", expression=js, returnByValue=True)
    return result.get('result', {}).get('value', 0) or 0

def get_latest_answer():
    """Get the latest answer text"""
    js = """
    const proses = document.querySelectorAll('[class*="prose"]');
    if (proses.length > 0) {
        const last = proses[proses.length - 1];
        return last.innerText || last.textContent;
    }
    return '';
    """
    result = tab.call_method("Runtime.evaluate", expression=js, returnByValue=True)
    return result.get('result', {}).get('value', '') or ''

def wait_for_new_answer(timeout=120, poll_interval=1, stable_checks=5):
    """Wait for new answer using the working approach from 2_perp_pych.py"""
    initial_count = get_answer_count()
    initial_text = get_latest_answer()
    start_time = time.time()
    print(f"Initial answer count: {initial_count}, initial text length: {len(initial_text)}")

    # Wait for change
    while time.time() - start_time < timeout:
        current_count = get_answer_count()
        current_text = get_latest_answer()
        if current_count > initial_count or (current_count == initial_count and current_text != initial_text and current_text):
            print(f"Detected change: count {current_count}, text length {len(current_text)}")
            break
        time.sleep(poll_interval)

    if get_answer_count() == initial_count and get_latest_answer() == initial_text:
        return "Timeout: No new answer detected."

    # Stabilize
    prev_text = ''
    stable_count = 0
    while stable_count < stable_checks and time.time() - start_time < timeout:
        current_text = get_latest_answer()
        if current_text == prev_text and current_text != '':
            stable_count += 1
        else:
            stable_count = 0
            prev_text = current_text
        time.sleep(poll_interval)
        print(f"Stabilizing: stable_count {stable_count}, text length {len(current_text)}")

    if stable_count < stable_checks:
        return "Timeout: Answer did not stabilize. Last text: " + prev_text[:200]

    return prev_text

def wait_for_response(question_text, timeout=120):
    """Wait for Perplexity's response and extract it"""
    print(f"⏳ Waiting for Perplexity's response (timeout: {timeout}s)...")
    
    # Get initial page content
    initial_result = tab.call_method("Runtime.evaluate", 
                                   expression="document.body.innerText", 
                                   returnByValue=True)
    
    if 'result' not in initial_result or 'value' not in initial_result['result']:
        print("❌ Failed to get initial page content")
        return None
        
    initial_text = initial_result['result']['value']
    initial_length = len(initial_text)
    
    start_time = time.time()
    last_length = initial_length
    stable_count = 0
    max_stable_time = 12  # Wait 12 seconds of stability
    
    while time.time() - start_time < timeout:
        time.sleep(2)  # Check every 2 seconds
        
        # Get current page content
        current_result = tab.call_method("Runtime.evaluate", 
                                       expression="document.body.innerText", 
                                       returnByValue=True)
        
        if 'result' not in current_result or 'value' not in current_result['result']:
            continue
            
        current_text = current_result['result']['value']
        current_length = len(current_text)
        
        # Check if content has grown significantly
        if current_length > initial_length + 100:
            print(f"📈 Content increased: {initial_length} → {current_length}")
            
            # If content is still growing, reset stable count
            if current_length > last_length + 10:
                stable_count = 0
                last_length = current_length
                print(f"🔄 Content still growing, resetting stability counter")
                continue
            else:
                stable_count += 1
                print(f"⏸️  Content stable for {stable_count * 2} seconds")
            
            # Wait for stability before extracting
            if stable_count >= 6:
                print(f"✅ Content has been stable for {stable_count * 2} seconds, extracting response...")
                
                # Look for new content after our question
                if question_text in current_text:
                    # Find position of our question
                    question_pos = current_text.rfind(question_text)
                    
                    # Get text after our question
                    text_after_question = current_text[question_pos + len(question_text):]
                    
                    # Split into paragraphs
                    paragraphs = text_after_question.split('\n\n')
                    if len(paragraphs) < 2:
                        paragraphs = text_after_question.split('\n')
                    
                    # Find the response content
                    response_parts = []
                    found_start = False
                    
                    # Perplexity-specific UI elements to skip
                    perplexity_ui_elements = [
                        'Ask anything...', 'Search', 'Pro', 'Sources', 'Related', 
                        'Follow-up', 'Share', 'Copy', 'Regenerate', 'Ask follow-up',
                        'View sources', 'Pro Search', 'Focus', 'All', 'Academic',
                        'Writing', 'Wolfram|Alpha', 'YouTube', 'Reddit', 'News'
                    ]
                    
                    for paragraph in paragraphs[:200]:
                        paragraph = paragraph.strip()
                        
                        # Skip empty content
                        if not paragraph:
                            continue
                            
                        # Skip known Perplexity UI elements
                        if paragraph in perplexity_ui_elements:
                            if found_start:
                                print(f"🛑 Found end marker: '{paragraph}', stopping extraction")
                                break
                            continue
                        
                        # Skip time indicators, pure numbers, and very short content
                        if (re.match(r'^\d+\.?\d*[smh]$', paragraph) or 
                            paragraph.isdigit() or 
                            len(paragraph) < 3):
                            continue
                        
                        # Skip source indicators like "[1]", "[2]", etc.
                        if re.match(r'^\[\d+\]$', paragraph):
                            continue
                        
                        # Include substantial content
                        if len(paragraph) > 5:
                            if not found_start:
                                print(f"🎯 Found response start: '{paragraph[:50]}...'")
                            found_start = True
                            response_parts.append(paragraph)
                    
                    if response_parts:
                        # Join with appropriate spacing
                        full_response = '\n\n'.join(response_parts)
                        
                        print(f"\n🎉 FOUND COMPLETE PERPLEXITY RESPONSE!")
                        print(f"📊 Extracted {len(response_parts)} paragraphs, {len(full_response)} characters")
                        return full_response
                    else:
                        print("⚠️  No valid response content found, continuing to wait...")
                        stable_count = 0  # Reset and keep waiting
            
            last_length = current_length
    
    print("⏰ Timeout reached")
    return None

# Example usage in a loop
while True:
    question = input("Enter your question (or 'quit' to exit): ")
    if question.lower() == 'quit':
        break
    try:
        answer = ask_question(question)
        print("Answer:", answer)
        print("-" * 50)
    except Exception as e:
        print("Error:", str(e))

# Stop and close the tab
tab.stop()
browser.close_tab(tab)
