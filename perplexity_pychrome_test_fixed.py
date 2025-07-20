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
        
        # Look for a real Perplexity tab (not iframe or service worker)
        for tab_info in tab_list:
            url = tab_info.get('url', '')
            title = tab_info.get('title', '')
            
            # Skip service workers, iframes, and other non-main tabs
            if ('perplexity.ai' in url.lower() and 
                'stripe.network' not in url.lower() and
                'service_worker' not in url.lower() and
                'iframe' not in url.lower() and
                tab_info.get('type') == 'page'):
                
                print(f"📱 Found Perplexity tab: {title} - {url}")
                return tab_info['id']
        
        print("❌ No suitable Perplexity tab found")
        print("Please open https://www.perplexity.ai in a Chrome tab and try again")
        return None
        
    except Exception as e:
        print(f"❌ Error finding tabs: {e}")
        return None

def main():
    # Find existing Perplexity tab
    tab_id = find_perplexity_tab()
    if not tab_id:
        return
    
    # Connect to browser
    browser = pychrome.Browser(url="http://localhost:9222")
    
    # Get the specific tab
    tabs = browser.list_tab()
    tab = None
    for t in tabs:
        if t.id == tab_id:
            tab = t
            break
    
    if not tab:
        print("❌ Could not connect to the Perplexity tab")
        return
    
    # Start the tab
    tab.start()
    
    # Enable domains
    tab.call_method("Runtime.enable")
    tab.call_method("DOM.enable")
    tab.call_method("Page.enable")
    
    # Wait a moment
    time.sleep(2)
    
    # Test connection
    try:
        result = tab.call_method("Runtime.evaluate", 
                                expression="document.title", 
                                returnByValue=True)
        title = result.get('result', {}).get('value', 'Unknown')
        print(f"✅ Connected to tab: {title}")
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return
    
    def ask_question(question, timeout=120):
        print(f"📤 Sending message: '{question}'")
        
        try:
            # Get document
            doc_result = tab.call_method("DOM.getDocument")
            if not doc_result or 'result' not in doc_result:
                print("❌ Failed to get document")
                return None
            
            root_node_id = doc_result['result']['root']['nodeId']
            
            # Find input field - try multiple selectors
            selectors = [
                "textarea[placeholder*='Ask']",
                "textarea",
                "input[type='text']",
                "[contenteditable='true']",
                "[role='textbox']"
            ]
            
            input_node_id = None
            for selector in selectors:
                result = tab.call_method("DOM.querySelector", 
                                       nodeId=root_node_id, 
                                       selector=selector)
                if result.get('result', {}).get('nodeId'):
                    input_node_id = result['result']['nodeId']
                    print(f"📝 Found input with selector: {selector}")
                    break
            
            if not input_node_id:
                print("❌ Could not find input field!")
                return None
            
            # Focus and clear
            tab.call_method("DOM.focus", nodeId=input_node_id)
            time.sleep(0.5)
            
            # Clear existing text
            tab.call_method("Input.dispatchKeyEvent", type="keyDown", key="Control")
            tab.call_method("Input.dispatchKeyEvent", type="keyDown", key="KeyA")
            tab.call_method("Input.dispatchKeyEvent", type="keyUp", key="KeyA")
            tab.call_method("Input.dispatchKeyEvent", type="keyUp", key="Control")
            time.sleep(0.2)
            
            # Type the question
            for char in question:
                tab.call_method("Input.dispatchKeyEvent", type="char", text=char)
                time.sleep(0.01)
            
            # Press Enter
            tab.call_method("Input.dispatchKeyEvent", type="keyDown", key="Enter")
            tab.call_method("Input.dispatchKeyEvent", type="keyUp", key="Enter")
            
            print("✅ Message sent!")
            
            # Wait for response
            return wait_for_response(question, timeout)
            
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return None
    
    def wait_for_response(question_text, timeout=120):
        """Wait for Perplexity's response"""
        print(f"⏳ Waiting for response (timeout: {timeout}s)...")
        
        # Get initial content
        try:
            initial_result = tab.call_method("Runtime.evaluate", 
                                           expression="document.body.innerText", 
                                           returnByValue=True)
            initial_text = initial_result.get('result', {}).get('value', '')
            initial_length = len(initial_text)
        except:
            print("❌ Failed to get initial content")
            return None
        
        start_time = time.time()
        last_length = initial_length
        stable_count = 0
        
        while time.time() - start_time < timeout:
            time.sleep(3)  # Check every 3 seconds
            
            try:
                current_result = tab.call_method("Runtime.evaluate", 
                                               expression="document.body.innerText", 
                                               returnByValue=True)
                current_text = current_result.get('result', {}).get('value', '')
                current_length = len(current_text)
                
                # Check if content has grown
                if current_length > initial_length + 50:
                    print(f"📈 Content increased: {initial_length} → {current_length}")
                    
                    # Check if content is stable
                    if current_length == last_length:
                        stable_count += 1
                        print(f"⏸️  Content stable for {stable_count * 3} seconds")
                        
                        if stable_count >= 4:  # 12 seconds of stability
                            print("✅ Content appears stable, extracting response...")
                            
                            # Find our question in the text
                            if question_text in current_text:
                                question_pos = current_text.rfind(question_text)
                                response_text = current_text[question_pos + len(question_text):]
                                
                                # Clean up the response
                                lines = response_text.split('\n')
                                response_lines = []
                                
                                for line in lines:
                                    line = line.strip()
                                    if (line and 
                                        len(line) > 10 and
                                        not line.isdigit() and
                                        'Ask anything' not in line and
                                        'Sources' not in line and
                                        'Related' not in line):
                                        response_lines.append(line)
                                        if len(response_lines) >= 10:  # Limit response length
                                            break
                                
                                if response_lines:
                                    response = '\n\n'.join(response_lines[:5])  # Take first 5 meaningful lines
                                    print(f"\n🎉 RESPONSE FOUND!")
                                    return response
                            
                            print("⚠️  Could not extract response")
                            return None
                    else:
                        stable_count = 0
                        last_length = current_length
                
            except Exception as e:
                print(f"⚠️  Error checking content: {e}")
                continue
        
        print("⏰ Timeout reached")
        return None
    
    # Main interaction loop
    print("\n🚀 Ready! Make sure you have Perplexity.ai open in Chrome.")
    while True:
        question = input("\nEnter your question (or 'quit' to exit): ")
        if question.lower() == 'quit':
            break
        
        if question.strip():
            try:
                answer = ask_question(question.strip())
                if answer:
                    print(f"\n📝 Answer:\n{answer}")
                else:
                    print("❌ No response received")
                print("-" * 50)
            except Exception as e:
                print(f"❌ Error: {e}")
    
    # Cleanup
    try:
        tab.stop()
    except:
        pass

if __name__ == "__main__":
    main()
