import pychrome
import time

# Connect to the browser
browser = pychrome.Browser(url="http://localhost:9222")

# Find the specific tab by ID (from the provided JSON)
tab_id = "E8CF09D134FAEB497BC8E90CBB705C86"
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
    # First, let's debug what's on the page to find the right selectors
    debug_expr = """
    (() => {
        // Find all buttons and their properties
        const buttons = Array.from(document.querySelectorAll('button'));
        const buttonInfo = buttons.map((btn, idx) => ({
            index: idx,
            text: btn.textContent?.trim() || '',
            type: btn.type || '',
            className: btn.className || '',
            ariaLabel: btn.getAttribute('aria-label') || '',
            disabled: btn.disabled,
            hasSVG: btn.querySelector('svg') ? true : false
        }));
        
        // Find textarea
        const textarea = document.querySelector('textarea');
        const textareaInfo = textarea ? {
            placeholder: textarea.placeholder || '',
            value: textarea.value || '',
            className: textarea.className || ''
        } : null;
        
        return {
            buttons: buttonInfo,
            textarea: textareaInfo,
            totalButtons: buttons.length
        };
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=debug_expr, returnByValue=True)
    debug_info = result.get('result', {}).get('value', {})
    print(f"🔍 Debug info: {debug_info}")

    # Get current page content length to detect new responses
    content_expr = "document.body.innerText.length"
    result = tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get page content length. Result: {result}")
    
    initial_content_length = result['result']['value']

    # Set text in textarea using a more reliable method
    set_text_expr = f"""
    (() => {{
        const textarea = document.querySelector('textarea');
        if (textarea) {{
            // Focus and clear
            textarea.focus();
            textarea.value = '';
            
            // Set new text
            textarea.value = `{question.replace('`', '\\`')}`;
            
            // Trigger events to notify the app
            textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
            textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            return `Text set: "${{textarea.value}}"`;
        }}
        return 'Textarea not found';
    }})()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=set_text_expr, returnByValue=True)
    print(f"📝 {result.get('result', {}).get('value', 'Unknown')}")

    time.sleep(1)

    # Try Enter key first (most reliable for chat interfaces)
    print("🔄 Trying Enter key...")
    enter_expr = """
    (() => {
        const textarea = document.querySelector('textarea');
        if (textarea) {
            textarea.focus();
            
            // Try multiple Enter key approaches
            const enterKeyDown = new KeyboardEvent('keydown', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });
            
            const enterKeyUp = new KeyboardEvent('keyup', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true
            });
            
            textarea.dispatchEvent(enterKeyDown);
            textarea.dispatchEvent(enterKeyUp);
            
            return 'Enter key events dispatched';
        }
        return 'Textarea not found for Enter';
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=enter_expr, returnByValue=True)
    print(f"⌨️  {result.get('result', {}).get('value', 'Unknown')}")

    # Wait a moment to see if Enter worked
    time.sleep(2)
    
    # Check if content changed after Enter
    result = tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    current_length = result.get('result', {}).get('value', initial_content_length)
    
    if current_length > initial_content_length + 50:
        print("✅ Enter key seems to have worked - content changed!")
    else:
        print("🔄 Enter didn't work, trying button clicks...")
        
        # More targeted button selection - avoid menu/history buttons
        smart_button_expr = f"""
        (() => {{
            const textarea = document.querySelector('textarea');
            if (!textarea) return 'No textarea found';
            
            // Look for buttons near the textarea (likely send buttons)
            const textareaRect = textarea.getBoundingClientRect();
            const buttons = Array.from(document.querySelectorAll('button'));
            
            // Filter buttons that are likely send buttons
            const sendButtons = buttons.filter(btn => {{
                const rect = btn.getBoundingClientRect();
                const isNearTextarea = Math.abs(rect.top - textareaRect.top) < 100;
                const isNotDisabled = !btn.disabled;
                const hasNoMenuText = !btn.textContent?.toLowerCase().includes('menu') && 
                                     !btn.textContent?.toLowerCase().includes('history') &&
                                     !btn.textContent?.toLowerCase().includes('chat');
                const isSmallButton = rect.width < 100; // Send buttons are usually small
                
                return isNearTextarea && isNotDisabled && hasNoMenuText && isSmallButton;
            }});
            
            // Try to click the most likely send button
            if (sendButtons.length > 0) {{
                const sendButton = sendButtons[0];
                sendButton.click();
                return `Clicked send button: ${{sendButton.textContent?.trim() || 'no text'}}`;
            }}
            
            return 'No suitable send button found';
        }})()
        """
        
        result = tab.call_method("Runtime.evaluate", expression=smart_button_expr, returnByValue=True)
        print(f"🎯 {result.get('result', {}).get('value', 'Unknown')}")

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
            print("📄 Using fallback method - recent page content")
        else:
            raise ValueError(f"Failed to get any response. Last result: {result}")
    
    return response

# Example usage in a loop
print("🤖 GROK PYCHROME TEST INTERFACE")
print("=" * 50)
print(f"🔗 Connected to tab: {tab_id}")
print("=" * 50)

while True:
    question = input("\n❓ Enter your question (or 'quit' to exit): ")
    if question.lower() == 'quit':
        break
    
    try:
        print(f"\n🔄 Processing: {question}")
        answer = ask_question(question)
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
browser.close_tab(tab)
print("👋 Goodbye!")
