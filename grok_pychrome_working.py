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
    
    # Navigate to fresh Grok page
    navigate_expr = """
    (() => {
        window.location.href = 'https://grok.com/';
        return 'Navigated to fresh Grok page';
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=navigate_expr, returnByValue=True)
    print(f"🆕 {result.get('result', {}).get('value', 'Unknown')}")
    
    # Wait for page to load
    time.sleep(4)

def ask_question(question, timeout=30):
    print(f"\n🔄 Processing: {question}")
    
    # Start with a new conversation
    start_new_conversation()
    
    # Wait for page to fully load and find textarea
    print("⏳ Waiting for page to load...")
    
    # Wait for textarea to be available
    wait_for_textarea_expr = """
    (() => {
        let attempts = 0;
        const maxAttempts = 20;
        
        const checkTextarea = () => {
            const textarea = document.querySelector('textarea');
            if (textarea && textarea.offsetParent !== null) {
                return true;
            }
            return false;
        };
        
        return new Promise((resolve) => {
            const interval = setInterval(() => {
                attempts++;
                if (checkTextarea() || attempts >= maxAttempts) {
                    clearInterval(interval);
                    resolve(checkTextarea());
                }
            }, 500);
        });
    })()
    """
    
    # This is a promise, so we need to handle it differently
    # Let's use a simpler approach - just wait and check
    time.sleep(3)
    
    # Check current page state
    check_page_expr = """
    (() => {
        const currentUrl = window.location.href;
        const pageTitle = document.title;
        const hasTextarea = document.querySelector('textarea') !== null;
        const textareaVisible = document.querySelector('textarea')?.offsetParent !== null;
        
        return {
            url: currentUrl,
            title: pageTitle,
            hasTextarea: hasTextarea,
            textareaVisible: textareaVisible,
            bodyText: document.body.innerText.substring(0, 300)
        };
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=check_page_expr, returnByValue=True)
    page_info = result.get('result', {}).get('value', {})
    print(f"🔍 Page info: {page_info}")
    
    if not page_info.get('textareaVisible', False):
        print("❌ Textarea not visible, waiting longer...")
        time.sleep(3)
    
    # Get initial content length for response detection
    content_expr = "document.body.innerText.length"
    result = tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get page content length. Result: {result}")
    
    initial_content_length = result['result']['value']
    print(f"📏 Initial content length: {initial_content_length}")

    # Find and focus textarea
    find_and_focus_textarea_expr = """
    (() => {
        const textarea = document.querySelector('textarea');
        if (textarea && textarea.offsetParent !== null) {
            textarea.focus();
            textarea.click(); // Ensure it's focused
            return {
                found: true,
                placeholder: textarea.placeholder || '',
                tagName: textarea.tagName,
                focused: document.activeElement === textarea
            };
        }
        return { found: false };
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=find_and_focus_textarea_expr, returnByValue=True)
    textarea_info = result.get('result', {}).get('value', {})
    print(f"📝 Textarea info: {textarea_info}")
    
    if not textarea_info.get('found', False):
        raise ValueError("Could not find visible textarea on the page")
    
    time.sleep(1)
    
    # Clear any existing content and set new text
    set_text_expr = f"""
    (() => {{
        const textarea = document.querySelector('textarea');
        if (textarea) {{
            // Focus and clear
            textarea.focus();
            textarea.select();
            textarea.value = '';
            
            // Set new text
            textarea.value = `{question.replace('`', '\\`')}`;
            
            // Trigger events to notify the interface
            textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
            textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
            textarea.dispatchEvent(new Event('keyup', {{ bubbles: true }}));
            
            return `Text set: "${{textarea.value}}" (Length: ${{textarea.value.length}})`;
        }}
        return 'Textarea not found';
    }})()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=set_text_expr, returnByValue=True)
    print(f"📝 {result.get('result', {}).get('value', 'Unknown')}")

    time.sleep(1)

    # Submit using Enter key (the primary method for Grok)
    print("🔄 Submitting with Enter key...")
    
    submit_with_enter_expr = """
    (() => {
        const textarea = document.querySelector('textarea');
        if (textarea) {
            textarea.focus();
            
            // Create and dispatch Enter key event
            const enterEvent = new KeyboardEvent('keydown', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });
            
            const result = textarea.dispatchEvent(enterEvent);
            
            // Also try keypress and keyup for completeness
            const keypressEvent = new KeyboardEvent('keypress', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });
            textarea.dispatchEvent(keypressEvent);
            
            const keyupEvent = new KeyboardEvent('keyup', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true
            });
            textarea.dispatchEvent(keyupEvent);
            
            return `Enter key events dispatched. KeyDown result: ${result}`;
        }
        return 'Textarea not found';
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=submit_with_enter_expr, returnByValue=True)
    print(f"⌨️  {result.get('result', {}).get('value', 'Unknown')}")

    # Wait for response with improved detection
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

    # Extract response with improved methods
    response_extraction_methods = [
        # Method 1: Look for the most recent meaningful content after our question
        f"""
        (() => {{
            const bodyText = document.body.innerText;
            const lines = bodyText.split('\\n').filter(line => line.trim().length > 0);
            
            // Find our question in the text
            let questionIndex = -1;
            for (let i = 0; i < lines.length; i++) {{
                if (lines[i].includes(`{question.replace('`', '\\`')}`)) {{
                    questionIndex = i;
                    break;
                }}
            }}
            
            if (questionIndex !== -1 && questionIndex < lines.length - 1) {{
                // Get lines after our question
                const afterQuestion = lines.slice(questionIndex + 1);
                
                // Filter out UI elements and get meaningful content
                const meaningfulLines = afterQuestion.filter(line => {{
                    const trimmed = line.trim();
                    return trimmed.length > 15 && 
                           !trimmed.includes('How can Grok help') &&
                           !trimmed.includes('DeepSearch') &&
                           !trimmed.includes('Think Grok') &&
                           !trimmed.includes('Upgrade to SuperGrok') &&
                           !trimmed.includes('SearchCtrl+K') &&
                           !trimmed.includes('Share') &&
                           !trimmed.includes('Toggle Sidebar') &&
                           !trimmed.includes('Create Images') &&
                           !trimmed.includes('Edit Image') &&
                           !trimmed.includes('Latest News') &&
                           !trimmed.includes('Personas') &&
                           !trimmed.includes('Grok 4') &&
                           !trimmed.match(/^\\d+[smh]$/);
                }});
                
                return meaningfulLines.slice(0, 15).join('\\n');
            }}
            return null;
        }})()
        """,
        
        # Method 2: Look for conversation containers or message elements
        """
        (() => {
            // Look for common chat message selectors
            const messageSelectors = [
                '[data-testid*="message"]',
                '[data-testid*="conversation"]',
                '.message',
                '[role="article"]',
                'div[class*="message"]',
                'div[class*="response"]'
            ];
            
            for (const selector of messageSelectors) {
                const containers = document.querySelectorAll(selector);
                if (containers.length > 0) {
                    const lastContainer = containers[containers.length - 1];
                    const text = lastContainer.innerText || lastContainer.textContent || '';
                    
                    if (text.length > 50) {
                        return text.trim();
                    }
                }
            }
            return null;
        })()
        """,
        
        # Method 3: Get recent meaningful paragraphs from the page
        """
        (() => {
            const allText = document.body.innerText;
            const paragraphs = allText.split('\\n\\n').filter(p => p.trim().length > 50);
            
            // Find paragraphs that look like responses (exclude UI elements)
            const responseParagraphs = paragraphs.filter(p => {
                const trimmed = p.trim();
                return trimmed.length > 50 && 
                       !trimmed.includes('How can Grok help') &&
                       !trimmed.includes('DeepSearch') &&
                       !trimmed.includes('Think Grok') &&
                       !trimmed.includes('Upgrade to SuperGrok') &&
                       !trimmed.includes('SearchCtrl+K') &&
                       !trimmed.includes('Create Images') &&
                       !trimmed.includes('Latest News');
            });
            
            // Return the last meaningful paragraph
            return responseParagraphs.slice(-1).join('\\n\\n');
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
        fallback_expr = "document.body.innerText.slice(-1000)"  # Last 1000 characters
        result = tab.call_method("Runtime.evaluate", expression=fallback_expr, returnByValue=True)
        
        if 'result' in result and 'value' in result['result']:
            response = result['result']['value']
            print("🔄 Using fallback method - recent page content")
        else:
            raise ValueError(f"Failed to get any response. Last result: {result}")
    
    return response

# Main execution
print("🤖 GROK PYCHROME WORKING VERSION")
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
