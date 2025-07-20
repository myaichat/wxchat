import pychrome
import time

# Connect to the browser
browser = pychrome.Browser(url="http://localhost:9222")

# Find the specific tab by ID (from the provided JSON)
tab_id = "2E53C20504E50BBFD36C0AA987A63DD3"
tabs = browser.list_tab()
tab = None
for t in tabs:
    if t.id == tab_id:
        tab = t
        break

if tab is None:
    raise ValueError("Tab with specified ID not found.")

# Start the tab
tab.start()

# Enable Runtime domain
tab.call_method("Runtime.enable")

def ask_question(question, timeout=30):
    print(f"\n🔄 Processing: {question}")
    
    # First, check if we're on the right page and navigate to chat if needed
    check_page_expr = """
    (() => {
        const currentUrl = window.location.href;
        const pageTitle = document.title;
        const hasTextarea = document.querySelector('textarea') !== null;
        const hasChatInterface = document.querySelector('[data-testid*="chat"]') !== null || 
                                document.querySelector('.chat') !== null ||
                                document.body.innerText.includes('How can Grok help');
        
        return {
            url: currentUrl,
            title: pageTitle,
            hasTextarea: hasTextarea,
            hasChatInterface: hasChatInterface,
            bodyText: document.body.innerText.substring(0, 500)
        };
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=check_page_expr, returnByValue=True)
    page_info = result.get('result', {}).get('value', {})
    print(f"🔍 Page info: {page_info}")
    
    # If we're not on the chat interface, try to navigate to it
    if not page_info.get('hasChatInterface', False):
        print("🔄 Not on chat interface, trying to navigate to chat...")
        
        # Try to click on "Chat" in the sidebar or navigate to chat
        navigate_expr = """
        (() => {
            // Look for Chat link/button in sidebar
            const chatLinks = Array.from(document.querySelectorAll('a, button')).filter(el => 
                el.textContent?.trim().toLowerCase() === 'chat' ||
                el.textContent?.trim().toLowerCase().includes('grok')
            );
            
            if (chatLinks.length > 0) {
                chatLinks[0].click();
                return 'Clicked chat link';
            }
            
            // Try to navigate directly to grok.com
            window.location.href = 'https://grok.com/';
            return 'Navigated to grok.com';
        })()
        """
        
        result = tab.call_method("Runtime.evaluate", expression=navigate_expr, returnByValue=True)
        print(f"🔄 Navigation result: {result.get('result', {}).get('value', 'Unknown')}")
        
        # Wait for navigation
        time.sleep(3)
    
    # Now try to find and use the textarea
    # Get current page content length to detect new responses
    content_expr = "document.body.innerText.length"
    result = tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get page content length. Result: {result}")
    
    initial_content_length = result['result']['value']
    print(f"📏 Initial content length: {initial_content_length}")

    # Look for textarea more comprehensively
    find_textarea_expr = """
    (() => {
        // Try multiple selectors for the input area
        const selectors = [
            'textarea',
            'input[type="text"]',
            '[contenteditable="true"]',
            '[data-testid*="input"]',
            '[data-testid*="textarea"]',
            '[placeholder*="Ask"]',
            '[placeholder*="Type"]',
            '[placeholder*="Message"]'
        ];
        
        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element) {
                return {
                    found: true,
                    selector: selector,
                    placeholder: element.placeholder || '',
                    tagName: element.tagName,
                    type: element.type || ''
                };
            }
        }
        
        return { found: false };
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=find_textarea_expr, returnByValue=True)
    textarea_info = result.get('result', {}).get('value', {})
    print(f"📝 Textarea search: {textarea_info}")
    
    if not textarea_info.get('found', False):
        raise ValueError("Could not find any input element on the page")
    
    # Set text using the found selector
    selector = textarea_info['selector']
    set_text_expr = f"""
    (() => {{
        const element = document.querySelector('{selector}');
        if (element) {{
            element.focus();
            
            // Clear existing content
            if (element.tagName === 'TEXTAREA' || element.type === 'text') {{
                element.value = '';
                element.value = `{question.replace('`', '\\`')}`;
            }} else if (element.contentEditable === 'true') {{
                element.textContent = '';
                element.textContent = `{question.replace('`', '\\`')}`;
            }}
            
            // Trigger events
            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            return `Text set in ${{element.tagName}}: "${{element.value || element.textContent}}"`;
        }}
        return 'Element not found';
    }})()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=set_text_expr, returnByValue=True)
    print(f"📝 {result.get('result', {}).get('value', 'Unknown')}")

    time.sleep(1)

    # Try multiple submission methods
    print("🔄 Trying submission methods...")
    
    # Method 1: Form submission
    form_submit_expr = f"""
    (() => {{
        const element = document.querySelector('{selector}');
        if (element) {{
            element.focus();
            
            // Find the form containing the textarea
            const form = element.closest('form');
            if (form) {{
                // Submit the form
                form.submit();
                return 'Form submitted successfully';
            }} else {{
                return 'No form found containing textarea';
            }}
        }}
        return 'Textarea element not found';
    }})()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=form_submit_expr, returnByValue=True)
    print(f"📋 Form submit: {result.get('result', {}).get('value', 'Unknown')}")
    
    time.sleep(1)
    
    # Method 2: Enter key press
    enter_key_expr = f"""
    (() => {{
        const element = document.querySelector('{selector}');
        if (element) {{
            element.focus();
            
            // Simulate Enter key press
            const enterEvent = new KeyboardEvent('keydown', {{
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true
            }});
            element.dispatchEvent(enterEvent);
            
            return 'Enter key pressed';
        }}
        return 'Element not found';
    }})()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=enter_key_expr, returnByValue=True)
    print(f"⌨️  Enter key: {result.get('result', {}).get('value', 'Unknown')}")
    
    time.sleep(1)
    
    # Method 3: Look for submit button
    submit_button_expr = """
    (() => {
        const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
        const submitButtons = buttons.filter(btn => 
            btn.textContent?.toLowerCase().includes('send') ||
            btn.textContent?.toLowerCase().includes('submit') ||
            btn.type === 'submit' ||
            btn.getAttribute('aria-label')?.toLowerCase().includes('send')
        );
        
        if (submitButtons.length > 0) {
            submitButtons[0].click();
            return `Clicked submit button: ${submitButtons[0].textContent || submitButtons[0].type}`;
        }
        
        return 'No submit button found';
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=submit_button_expr, returnByValue=True)
    print(f"🔘 Submit button: {result.get('result', {}).get('value', 'Unknown')}")

    # Wait for response to appear by monitoring content length changes
    start_time = time.time()
    last_content_length = initial_content_length
    response_detected = False
    
    print("🔄 Waiting for response...")
    
    while time.time() - start_time < timeout:
        # Check if content has grown significantly
        result = tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
        if 'result' in result and 'value' in result['result']:
            current_length = result['result']['value']
            
            print(f"📏 Content length: {current_length} (was {last_content_length})")
            
            # If content has grown by at least 100 characters, likely a response
            if current_length > last_content_length + 100:
                print(f"📈 Content grew from {last_content_length} to {current_length}")
                response_detected = True
                break
                
            last_content_length = current_length
        
        time.sleep(2)
    
    if not response_detected:
        print("⚠️  No significant content growth detected, trying to extract response anyway...")

    # Wait additional time for streaming to complete
    time.sleep(5)

    # Try multiple approaches to get the response
    response_extraction_methods = [
        # Method 1: Look for conversation/message containers
        f"""
        (() => {{
            const containers = document.querySelectorAll('div[data-testid*="conversation"], div[data-testid*="message"], .message');
            if (containers.length > 0) {{
                const lastContainer = containers[containers.length - 1];
                return lastContainer.innerText || lastContainer.textContent || 'Found container but no text';
            }}
            return null;
        }})()
        """,
        
        # Method 2: Get text after our question
        f"""
        (() => {{
            const bodyText = document.body.innerText;
            const questionIndex = bodyText.lastIndexOf(`{question.replace('`', '\\`')}`);
            if (questionIndex !== -1) {{
                const afterQuestion = bodyText.substring(questionIndex + `{question.replace('`', '\\`')}`.length);
                const lines = afterQuestion.split('\\n').filter(line => line.trim().length > 0);
                
                // Skip UI elements and get meaningful content
                const meaningfulLines = lines.filter(line => {{
                    const trimmed = line.trim();
                    return trimmed.length > 10 && 
                           !trimmed.includes('How can Grok help') &&
                           !trimmed.includes('DeepSearch') &&
                           !trimmed.includes('Think Grok') &&
                           !trimmed.includes('Upgrade to SuperGrok') &&
                           !trimmed.match(/^\\d+[smh]$/);
                }});
                
                return meaningfulLines.slice(0, 20).join('\\n');
            }}
            return null;
        }})()
        """,
        
        # Method 3: Get all text and try to find response pattern
        f"""
        (() => {{
            const allText = document.body.innerText;
            const paragraphs = allText.split('\\n\\n');
            
            // Find paragraphs that look like responses (longer than 50 chars, not UI elements)
            const responseParagraphs = paragraphs.filter(p => {{
                const trimmed = p.trim();
                return trimmed.length > 50 && 
                       !trimmed.includes('How can Grok help') &&
                       !trimmed.includes('DeepSearch') &&
                       !trimmed.includes('Think Grok') &&
                       !trimmed.includes('Upgrade to SuperGrok');
            }});
            
            // Return the last few response paragraphs
            return responseParagraphs.slice(-3).join('\\n\\n');
        }})()
        """
    ]
    
    response = None
    for i, method in enumerate(response_extraction_methods, 1):
        print(f"🔍 Trying extraction method {i}...")
        result = tab.call_method("Runtime.evaluate", expression=method, returnByValue=True)
        
        if 'result' in result and 'value' in result['result']:
            extracted = result['result']['value']
            if extracted and len(extracted.strip()) > 20:
                response = extracted.strip()
                print(f"✅ Method {i} successful!")
                break
            else:
                print(f"⚠️  Method {i} returned: {extracted}")
        else:
            print(f"❌ Method {i} failed: {result}")
    
    if not response:
        # Fallback: just get recent page content
        fallback_expr = "document.body.innerText.slice(-2000)"  # Last 2000 characters
        result = tab.call_method("Runtime.evaluate", expression=fallback_expr, returnByValue=True)
        
        if 'result' in result and 'value' in result['result']:
            response = result['result']['value']
            print("🔄 Using fallback method - recent page content")
        else:
            raise ValueError(f"Failed to get any response. Last result: {result}")
    
    return response

# Main execution
print("🤖 GROK PYCHROME TEST INTERFACE")
print("=" * 50)
print(f"🔗 Connected to tab: {tab_id}")
print("=" * 50)

# Test with a simple question automatically
test_question = "What is 2+2?"

try:
    answer = ask_question(test_question)
    print("\n" + "=" * 50)
    print("🤖 GROK RESPONSE:")
    print("=" * 50)
    print(answer)
    print("=" * 50)
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

# Stop and close the tab
print("\n✅ Closing connection...")
tab.stop()
print("🏁 Test completed!")
