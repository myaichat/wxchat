import pychrome
import time
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
    
    # Test connection with more detailed debugging
    try:
        result = tab.call_method("Runtime.evaluate", 
                                expression="document.title", 
                                returnByValue=True)
        title = result.get('result', {}).get('value', 'Unknown')
        print(f"✅ Connected to tab: {title}")
        
        # Test DOM access
        url_result = tab.call_method("Runtime.evaluate", 
                                    expression="window.location.href", 
                                    returnByValue=True)
        url = url_result.get('result', {}).get('value', 'Unknown')
        print(f"📍 Current URL: {url}")
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return
    
    def ask_question(question, timeout=120):
        print(f"📤 Sending message: '{question}'")
        
        try:
            # Try a different approach - use JavaScript to find and interact with elements
            js_code = f"""
            (function() {{
                // Find textarea or input field
                let input = document.querySelector('textarea[placeholder*="Ask"]') || 
                           document.querySelector('textarea') ||
                           document.querySelector('input[type="text"]') ||
                           document.querySelector('[contenteditable="true"]') ||
                           document.querySelector('[role="textbox"]');
                
                if (!input) {{
                    return {{ success: false, error: "No input field found" }};
                }}
                
                // Focus and clear
                input.focus();
                input.select();
                
                // Set the value
                if (input.tagName.toLowerCase() === 'textarea' || input.tagName.toLowerCase() === 'input') {{
                    input.value = '{question}';
                }} else {{
                    input.textContent = '{question}';
                }}
                
                // Trigger input event
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                
                // Try to find and click submit button or press Enter
                let submitBtn = document.querySelector('button[type="submit"]') ||
                               document.querySelector('button[aria-label*="Send"]') ||
                               document.querySelector('button[aria-label*="Submit"]');
                
                if (submitBtn) {{
                    submitBtn.click();
                }} else {{
                    // Simulate Enter key
                    input.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', bubbles: true }}));
                }}
                
                return {{ success: true, message: "Message sent" }};
            }})();
            """
            
            result = tab.call_method("Runtime.evaluate", 
                                   expression=js_code, 
                                   returnByValue=True)
            
            response = result.get('result', {}).get('value', {})
            
            if response.get('success'):
                print("✅ Message sent using JavaScript!")
                return wait_for_response(question, timeout)
            else:
                print(f"❌ JavaScript method failed: {response.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return None
    
    def wait_for_response(question_text, timeout=120):
        """Wait for Perplexity's response"""
        print(f"⏳ Waiting for response (timeout: {timeout}s)...")
        
        # Get initial content length
        try:
            initial_result = tab.call_method("Runtime.evaluate", 
                                           expression="document.body.innerText.length", 
                                           returnByValue=True)
            initial_length = initial_result.get('result', {}).get('value', 0)
            print(f"📏 Initial content length: {initial_length}")
        except:
            print("❌ Failed to get initial content length")
            return None
        
        start_time = time.time()
        last_length = initial_length
        stable_count = 0
        
        while time.time() - start_time < timeout:
            time.sleep(4)  # Check every 4 seconds
            
            try:
                # Check content length first
                length_result = tab.call_method("Runtime.evaluate", 
                                               expression="document.body.innerText.length", 
                                               returnByValue=True)
                current_length = length_result.get('result', {}).get('value', 0)
                
                # Check if content has grown significantly
                if current_length > initial_length + 100:
                    print(f"📈 Content increased: {initial_length} → {current_length}")
                    
                    # Check if content is stable
                    if current_length == last_length:
                        stable_count += 1
                        print(f"⏸️  Content stable for {stable_count * 4} seconds")
                        
                        if stable_count >= 3:  # 12 seconds of stability
                            print("✅ Content appears stable, extracting response...")
                            
                            # Get the full text and try to extract response
                            text_result = tab.call_method("Runtime.evaluate", 
                                                         expression="document.body.innerText", 
                                                         returnByValue=True)
                            current_text = text_result.get('result', {}).get('value', '')
                            
                            # Simple extraction - get text after our question
                            if question_text in current_text:
                                question_pos = current_text.rfind(question_text)
                                response_text = current_text[question_pos + len(question_text):]
                                
                                # Clean up the response - take first few meaningful lines
                                lines = [line.strip() for line in response_text.split('\n') if line.strip()]
                                response_lines = []
                                
                                for line in lines:
                                    if (len(line) > 15 and
                                        not line.isdigit() and
                                        'Ask anything' not in line and
                                        'Sources' not in line and
                                        'Related' not in line and
                                        'Follow-up' not in line):
                                        response_lines.append(line)
                                        if len(response_lines) >= 3:  # Take first 3 good lines
                                            break
                                
                                if response_lines:
                                    response = '\n\n'.join(response_lines)
                                    print(f"\n🎉 RESPONSE EXTRACTED!")
                                    return response
                            
                            print("⚠️  Could not extract meaningful response")
                            return "Response received but could not be extracted cleanly."
                    else:
                        stable_count = 0
                        last_length = current_length
                        print(f"🔄 Content still changing...")
                
            except Exception as e:
                print(f"⚠️  Error checking content: {e}")
                continue
        
        print("⏰ Timeout reached")
        return None
    
    # Main interaction loop
    print("\n🚀 Ready! Make sure you have Perplexity.ai open and loaded in Chrome.")
    print("💡 Tip: If it doesn't work, try refreshing the Perplexity page first.")
    
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
