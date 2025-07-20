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
    
    # Navigate to fresh Grok page
    print("🔄 Starting new conversation...")
    navigate_expr = """
    (() => {
        window.location.href = 'https://grok.com/';
        return 'Navigated to fresh Grok page';
    })()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=navigate_expr, returnByValue=True)
    print(f"🆕 {result.get('result', {}).get('value', 'Unknown')}")
    
    # Wait for page to load
    time.sleep(5)
    
    # Get initial content length for response detection
    content_expr = "document.body.innerText.length"
    result = tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    initial_content_length = result['result']['value']
    print(f"📏 Initial content length: {initial_content_length}")

    # Set text and submit in one comprehensive operation
    submit_question_expr = f"""
    (() => {{
        // Step 1: Find and focus textarea
        const textarea = document.querySelector('textarea');
        if (!textarea) {{
            return {{ success: false, error: 'Textarea not found' }};
        }}
        
        // Step 2: Focus and set text
        textarea.focus();
        textarea.click();
        textarea.value = '';
        textarea.value = `{question.replace('`', '\\`')}`;
        
        // Step 3: Trigger input events
        textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
        textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
        
        // Step 4: Try multiple submission methods
        let submitted = false;
        let methods = [];
        
        // Method 1: Try Enter key with different event types
        const enterEvents = [
            new KeyboardEvent('keydown', {{ key: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }}),
            new KeyboardEvent('keypress', {{ key: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }}),
            new KeyboardEvent('keyup', {{ key: 'Enter', keyCode: 13, which: 13, bubbles: true }})
        ];
        
        for (const event of enterEvents) {{
            const result = textarea.dispatchEvent(event);
            methods.push(`Enter ${{event.type}}: ${{result}}`);
            if (result) submitted = true;
        }}
        
        // Method 2: Try to find and click any submit-related elements
        const submitElements = [
            ...document.querySelectorAll('button[type="submit"]'),
            ...document.querySelectorAll('input[type="submit"]'),
            ...document.querySelectorAll('button[aria-label*="send" i]'),
            ...document.querySelectorAll('button[title*="send" i]'),
            ...document.querySelectorAll('[role="button"][aria-label*="send" i]')
        ];
        
        for (const element of submitElements) {{
            if (element.offsetParent !== null) {{ // visible
                element.click();
                methods.push(`Clicked submit element: ${{element.tagName}} ${{element.getAttribute('aria-label') || element.textContent}}`);
                submitted = true;
                break;
            }}
        }}
        
        // Method 3: Try form submission
        const form = textarea.closest('form');
        if (form) {{
            form.submit();
            methods.push('Form submitted');
            submitted = true;
        }}
        
        // Method 4: Try to trigger React/Vue events by simulating user interaction
        textarea.focus();
        
        // Simulate typing the Enter key more realistically
        const syntheticEnter = new KeyboardEvent('keydown', {{
            key: 'Enter',
            code: 'Enter',
            keyCode: 13,
            which: 13,
            bubbles: true,
            cancelable: true,
            composed: true,
            isTrusted: false
        }});
        
        // Dispatch on the textarea and also on document
        const textareaResult = textarea.dispatchEvent(syntheticEnter);
        const documentResult = document.dispatchEvent(syntheticEnter);
        methods.push(`Synthetic Enter - textarea: ${{textareaResult}}, document: ${{documentResult}}`);
        
        // Method 5: Try to find React fiber and trigger events
        try {{
            const reactFiber = textarea._reactInternalFiber || textarea._reactInternalInstance;
            if (reactFiber) {{
                methods.push('Found React fiber');
                // Try to trigger React events
                const nativeEvent = new KeyboardEvent('keydown', {{ key: 'Enter', keyCode: 13 }});
                if (reactFiber.memoizedProps && reactFiber.memoizedProps.onKeyDown) {{
                    reactFiber.memoizedProps.onKeyDown({{ key: 'Enter', keyCode: 13, preventDefault: () => {{}}, target: textarea }});
                    methods.push('Triggered React onKeyDown');
                    submitted = true;
                }}
            }}
        }} catch (e) {{
            methods.push(`React attempt failed: ${{e.message}}`);
        }}
        
        return {{
            success: submitted,
            textSet: textarea.value,
            methods: methods,
            textareaFocused: document.activeElement === textarea
        }};
    }})()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=submit_question_expr, returnByValue=True)
    submit_result = result.get('result', {}).get('value', {})
    
    print(f"📝 Submit result: {submit_result}")
    
    # If the comprehensive method didn't work, try a simpler approach
    if not submit_result.get('success', False):
        print("🔄 Trying alternative submission method...")
        
        # Try a more direct approach - simulate actual user typing
        alternative_submit_expr = f"""
        (() => {{
            const textarea = document.querySelector('textarea');
            if (!textarea) return 'No textarea';
            
            // Clear and type character by character (more realistic)
            textarea.focus();
            textarea.value = '';
            
            const text = `{question.replace('`', '\\`')}`;
            let i = 0;
            
            const typeChar = () => {{
                if (i < text.length) {{
                    textarea.value += text[i];
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    i++;
                    setTimeout(typeChar, 50); // Type at human speed
                }} else {{
                    // After typing, press Enter
                    setTimeout(() => {{
                        const enterEvent = new KeyboardEvent('keydown', {{
                            key: 'Enter',
                            keyCode: 13,
                            bubbles: true,
                            cancelable: true
                        }});
                        textarea.dispatchEvent(enterEvent);
                    }}, 100);
                }}
            }};
            
            typeChar();
            return 'Started typing simulation';
        }})()
        """
        
        result = tab.call_method("Runtime.evaluate", expression=alternative_submit_expr, returnByValue=True)
        print(f"⌨️  Alternative method: {result.get('result', {}).get('value', 'Unknown')}")
        
        # Wait for the typing simulation to complete
        time.sleep(3)

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
            
            # If content has grown by at least 150 characters, likely a response
            if current_length > last_content_length + 150:
                print(f"📈 Content grew from {last_content_length} to {current_length}")
                response_detected = True
                break
                
            last_content_length = current_length
        
        time.sleep(2)
    
    if not response_detected:
        print("⚠️  No significant content growth detected, trying to extract response anyway...")

    # Wait additional time for streaming to complete
    time.sleep(5)

    # Extract response with the most effective method
    extract_response_expr = f"""
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
                       !trimmed.includes('Private') &&
                       !trimmed.match(/^\\d+[smh]$/);
            }});
            
            if (meaningfulLines.length > 0) {{
                return meaningfulLines.slice(0, 10).join('\\n');
            }}
        }}
        
        // Fallback: get the most recent meaningful content
        const allLines = lines.filter(line => {{
            const trimmed = line.trim();
            return trimmed.length > 20 && 
                   !trimmed.includes('SearchCtrl+K') &&
                   !trimmed.includes('Toggle Sidebar') &&
                   !trimmed.includes('Create Images');
        }});
        
        return allLines.slice(-5).join('\\n');
    }})()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=extract_response_expr, returnByValue=True)
    response = result.get('result', {}).get('value', '')
    
    if not response or len(response.strip()) < 30:
        # Final fallback: just get recent page content
        fallback_expr = "document.body.innerText.slice(-800)"
        result = tab.call_method("Runtime.evaluate", expression=fallback_expr, returnByValue=True)
        response = result.get('result', {}).get('value', 'No response detected')
    
    return response.strip()

# Main execution
print("🤖 GROK PYCHROME FINAL VERSION")
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
