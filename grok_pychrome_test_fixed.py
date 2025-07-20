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

def start_new_conversation():
    """Start a new conversation to avoid old responses"""
    print("🔄 Starting new conversation...")
    
    # Try to click "New Chat" or similar button
    new_chat_expr = """
    (() => {
        // Look for new chat buttons
        const buttons = Array.from(document.querySelectorAll('button, a'));
        const newChatButtons = buttons.filter(btn => {
            const text = btn.textContent?.toLowerCase() || '';
            const ariaLabel = btn.getAttribute('aria-label')?.toLowerCase() || '';
            return text.includes('new') || text.includes('chat') || 
                   ariaLabel.includes('new') || ariaLabel.includes('chat');
        });
        
        if (newChatButtons.length > 0) {
            newChatButtons[0].click();
            return `Clicked new chat button: ${newChatButtons[0].textContent || newChatButtons[0].getAttribute('aria-label')}`;
        }
        
        // Alternative: navigate to new chat URL
        if (window.location.href.includes('grok.com')) {
            window.location.href = 'https://grok.com/';
            return 'Navigated to new chat';
        }
        
        return 'No new chat button found';
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=new_chat_expr, returnByValue=True)
    print(f"🆕 {result.get('result', {}).get('value', 'Unknown')}")
    
    # Wait for new chat to load
    time.sleep(3)

def ask_question(question, timeout=30):
    print(f"\n🔄 Processing: {question}")
    
    # Start with a new conversation
    start_new_conversation()
    
    # Check current page state
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
    
    # Get initial content length for response detection
    content_expr = "document.body.innerText.length"
    result = tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get page content length. Result: {result}")
    
    initial_content_length = result['result']['value']
    print(f"📏 Initial content length: {initial_content_length}")

    # Find textarea with better detection
    find_textarea_expr = """
    (() => {
        // Try multiple selectors for the input area
        const selectors = [
            'textarea[placeholder*="Ask"]',
            'textarea[placeholder*="Type"]',
            'textarea[placeholder*="Message"]',
            'textarea',
            'input[type="text"]',
            '[contenteditable="true"]',
            '[data-testid*="input"]',
            '[data-testid*="textarea"]'
        ];
        
        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element && element.offsetParent !== null) { // Check if visible
                return {
                    found: true,
                    selector: selector,
                    placeholder: element.placeholder || '',
                    tagName: element.tagName,
                    type: element.type || '',
                    visible: true
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
        raise ValueError("Could not find any visible input element on the page")
    
    # Clear any existing content and set new text
    selector = textarea_info['selector']
    set_text_expr = f"""
    (() => {{
        const element = document.querySelector('{selector}');
        if (element) {{
            element.focus();
            
            // Clear existing content thoroughly
            if (element.tagName === 'TEXTAREA' || element.type === 'text') {{
                element.value = '';
                element.value = `{question.replace('`', '\\`')}`;
            }} else if (element.contentEditable === 'true') {{
                element.innerHTML = '';
                element.textContent = `{question.replace('`', '\\`')}`;
            }}
            
            // Trigger comprehensive events
            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
            element.dispatchEvent(new Event('keyup', {{ bubbles: true }}));
            
            return `Text set in ${{element.tagName}}: "${{element.value || element.textContent}}"`;
        }}
        return 'Element not found';
    }})()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=set_text_expr, returnByValue=True)
    print(f"📝 {result.get('result', {}).get('value', 'Unknown')}")

    time.sleep(1)

    # Try multiple submission methods with better button detection
    print("🔄 Trying submission methods...")
    
    # Method 1: Look for proper send/submit button (not search)
    send_button_expr = """
    (() => {
        const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
        const sendButtons = buttons.filter(btn => {
            const text = (btn.textContent || '').toLowerCase();
            const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
            const title = (btn.title || '').toLowerCase();
            
            // Look for send/submit indicators, but exclude search
            return (text.includes('send') || text.includes('submit') || 
                   ariaLabel.includes('send') || ariaLabel.includes('submit') ||
                   title.includes('send') || title.includes('submit') ||
                   btn.type === 'submit') &&
                   !text.includes('search') && !ariaLabel.includes('search') &&
                   !text.includes('ctrl+k') && !ariaLabel.includes('ctrl+k');
        });
        
        if (sendButtons.length > 0) {
            sendButtons[0].click();
            return `Clicked send button: ${sendButtons[0].textContent || sendButtons[0].getAttribute('aria-label') || sendButtons[0].type}`;
        }
        
        return 'No send button found';
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=send_button_expr, returnByValue=True)
    print(f"🔘 Send button: {result.get('result', {}).get('value', 'Unknown')}")
    
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
    
    # Method 3: Form submission as fallback
    form_submit_expr = f"""
    (() => {{
        const element = document.querySelector('{selector}');
        if (element) {{
            const form = element.closest('form');
            if (form) {{
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

    # Wait for response with better detection
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
            
            # If content has grown by at least 200 characters, likely a response
            if current_length > last_content_length + 200:
                print(f"📈 Content grew from {last_content_length} to {current_length}")
                response_detected = True
                break
                
            last_content_length = current_length
        
        time.sleep(2)
    
    if not response_detected:
        print("⚠️  No significant content growth detected, trying to extract response anyway...")

    # Wait additional time for streaming to complete
    time.sleep(5)

    # Improved response extraction methods
    response_extraction_methods = [
        # Method 1: Look for the most recent message that's not our question
        f"""
        (() => {{
            const bodyText = document.body.innerText;
            const lines = bodyText.split('\\n').filter(line => line.trim().length > 0);
            
            // Find our question in the text
            const questionIndex = lines.findIndex(line => 
                line.includes(`{question.replace('`', '\\`')}`)
            );
            
            if (questionIndex !== -1 && questionIndex < lines.length - 1) {{
                // Get lines after our question
                const afterQuestion = lines.slice(questionIndex + 1);
                
                // Filter out UI elements and get meaningful content
                const meaningfulLines = afterQuestion.filter(line => {{
                    const trimmed = line.trim();
                    return trimmed.length > 10 && 
                           !trimmed.includes('How can Grok help') &&
                           !trimmed.includes('DeepSearch') &&
                           !trimmed.includes('Think Grok') &&
                           !trimmed.includes('Upgrade to SuperGrok') &&
                           !trimmed.includes('SearchCtrl+K') &&
                           !trimmed.includes('Share') &&
                           !trimmed.includes('Toggle Sidebar') &&
                           !trimmed.match(/^\\d+[smh]$/);
                }});
                
                return meaningfulLines.slice(0, 10).join('\\n');
            }}
            return null;
        }})()
        """,
        
        # Method 2: Look for conversation containers
        """
        (() => {
            const containers = document.querySelectorAll('div[data-testid*="conversation"], div[data-testid*="message"], .message, [role="article"]');
            if (containers.length > 0) {
                const lastContainer = containers[containers.length - 1];
                const text = lastContainer.innerText || lastContainer.textContent || '';
                
                // Filter out our question and UI elements
                const lines = text.split('\\n').filter(line => {
                    const trimmed = line.trim();
                    return trimmed.length > 20 && 
                           !trimmed.includes('How can Grok help') &&
                           !trimmed.includes('SearchCtrl+K');
                });
                
                return lines.join('\\n');
            }
            return null;
        })()
        """,
        
        # Method 3: Get recent meaningful paragraphs
        """
        (() => {
            const allText = document.body.innerText;
            const paragraphs = allText.split('\\n\\n').filter(p => p.trim().length > 50);
            
            // Find paragraphs that look like responses
            const responseParagraphs = paragraphs.filter(p => {
                const trimmed = p.trim();
                return trimmed.length > 50 && 
                       !trimmed.includes('How can Grok help') &&
                       !trimmed.includes('DeepSearch') &&
                       !trimmed.includes('Think Grok') &&
                       !trimmed.includes('Upgrade to SuperGrok') &&
                       !trimmed.includes('SearchCtrl+K');
            });
            
            // Return the last few response paragraphs
            return responseParagraphs.slice(-2).join('\\n\\n');
        })()
        """
    ]
    
    response = None
    for i, method in enumerate(response_extraction_methods, 1):
        print(f"🔍 Trying extraction method {i}...")
        result = tab.call_method("Runtime.evaluate", expression=method, returnByValue=True)
        
        if 'result' in result and 'value' in result['result']:
            extracted = result['result']['value']
            if extracted and len(extracted.strip()) > 30:
                response = extracted.strip()
                print(f"✅ Method {i} successful!")
                break
            else:
                print(f"⚠️  Method {i} returned: {extracted}")
        else:
            print(f"❌ Method {i} failed: {result}")
    
    if not response:
        # Fallback: just get recent page content
        fallback_expr = "document.body.innerText.slice(-1500)"  # Last 1500 characters
        result = tab.call_method("Runtime.evaluate", expression=fallback_expr, returnByValue=True)
        
        if 'result' in result and 'value' in result['result']:
            response = result['result']['value']
            print("🔄 Using fallback method - recent page content")
        else:
            raise ValueError(f"Failed to get any response. Last result: {result}")
    
    return response

# Main execution
print("🤖 GROK PYCHROME TEST INTERFACE (FIXED)")
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
