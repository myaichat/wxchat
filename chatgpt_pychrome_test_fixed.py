import pychrome
import time
import json

# Connect to the browser
browser = pychrome.Browser(url="http://localhost:9222")

# Find the specific tab by ID (ChatGPT tab)
tab_id = "0451444E5EB34B50C93614897A954A8B"
tabs = browser.list_tab()
tab = None
for t in tabs:
    if t.id == tab_id:
        tab = t
        break

if tab is None:
    print("Available tabs:")
    for t in tabs:
        print(f"ID: {t.id}, Title: {t.title}, URL: {t.url}")
    raise ValueError("Tab with specified ID not found.")

# Start the tab
tab.start()

# Enable Runtime domain
tab.call_method("Runtime.enable")

def ask_question(question, timeout=30):
    """Ask a question using improved selector strategy"""
    
    # Escape the question for JavaScript
    escaped_question = json.dumps(question)
    
    # Get current number of responses before sending
    count_expr = """
    document.querySelectorAll('div[data-message-author-role="assistant"]').length
    """
    result = tab.call_method("Runtime.evaluate", expression=count_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get response count. Result: {result}")
    
    num_responses = result['result']['value']
    print(f"Current responses: {num_responses}")

    # Improved textarea finding and message sending
    send_expr = f"""
    (function() {{
        console.log("Starting message send process");
        
        // Find textarea using multiple selectors
        const selectors = [
            'textarea[placeholder*="Message"]',
            'textarea[data-id*="root"]', 
            '#prompt-textarea',
            'textarea',
            'div[contenteditable="true"]',
        ];
        
        let textarea = null;
        for (const selector of selectors) {{
            textarea = document.querySelector(selector);
            if (textarea) {{
                console.log("Found textarea with selector: " + selector);
                break;
            }}
        }}
        
        if (!textarea) {{
            return "TEXTAREA_NOT_FOUND";
        }}
        
        // Clear and populate textarea
        if (textarea.contentEditable === "true") {{
            textarea.innerHTML = "";
            textarea.focus();
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(textarea);
            selection.removeAllRanges();
            selection.addRange(range);
            document.execCommand('insertText', false, {escaped_question});
        }} else {{
            textarea.value = "";
            textarea.focus();
            textarea.value = {escaped_question};
        }}
        
        // Trigger events
        const events = ['input', 'change', 'keyup', 'keydown'];
        events.forEach(eventType => {{
            textarea.dispatchEvent(new Event(eventType, {{ bubbles: true, cancelable: true }}));
        }});
        
        // Small delay to let UI process
        setTimeout(() => {{
            // Find send button using multiple strategies
            const buttonSelectors = [
                'button[data-testid="send-button"]',
                'button[aria-label*="Send"]',
                'button[type="submit"]',
                'button:has(svg)',
                'button:not([disabled])',
            ];
            
            let sendButton = null;
            for (const selector of buttonSelectors) {{
                const buttons = document.querySelectorAll(selector);
                for (const button of buttons) {{
                    if (!button.disabled && button.offsetParent !== null) {{
                        const rect = button.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {{
                            // Check if button is in the composer area
                            const inComposer = button.closest('[class*="composer"]') || 
                                             button.closest('form') || 
                                             button.closest('[class*="input"]') ||
                                             button.parentElement?.querySelector('textarea');
                            if (inComposer) {{
                                sendButton = button;
                                console.log("Found send button with selector: " + selector);
                                break;
                            }}
                        }}
                    }}
                }}
                if (sendButton) break;
            }}
            
            if (sendButton && !sendButton.disabled) {{
                sendButton.click();
                console.log("Message sent successfully");
            }} else {{
                console.log("Send button not found or disabled");
            }}
        }}, 200);
        
        return "MESSAGE_SENDING";
    }})()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=send_expr, returnByValue=True)
    send_result = result.get('result', {}).get('value', 'UNKNOWN')
    
    if send_result == 'TEXTAREA_NOT_FOUND':
        raise ValueError("Failed to find textarea")
    
    print(f"Send result: {send_result}")
    
    # Wait for new response to appear
    start_time = time.time()
    current_num = num_responses
    
    print("Waiting for response...")
    while time.time() - start_time < timeout:
        result = tab.call_method("Runtime.evaluate", expression=count_expr, returnByValue=True)
        if 'result' in result and 'value' in result['result']:
            current_num = result['result']['value']
            if current_num > num_responses:
                print(f"New response detected! Count: {current_num}")
                break
        time.sleep(1)
    else:
        raise TimeoutError("Timeout waiting for response to appear.")

    # Wait additional time for streaming to complete
    print("Waiting for response to complete...")
    time.sleep(8)  # Increased wait time for streaming

    # Get the latest response text with improved extraction
    index = current_num - 1
    response_expr = f"""
    (function() {{
        const responses = document.querySelectorAll('div[data-message-author-role="assistant"]');
        if (responses.length > {index}) {{
            const responseElement = responses[{index}];
            let text = responseElement.innerText || responseElement.textContent || '';
            
            // Clean up common prefixes
            const prefixes = [
                'ChatGPT said:',
                'Claude said:',
                'Assistant:',
                'AI:',
                'Bot:',
            ];
            
            for (const prefix of prefixes) {{
                if (text.startsWith(prefix)) {{
                    text = text.substring(prefix.length).trim();
                }}
            }}
            
            // Clean up common UI artifacts
            const artifacts = ['markdown\\nCopy\\nEdit\\n', 'markdown\\n', 'Copy\\n', 'Edit\\n'];
            for (const artifact of artifacts) {{
                text = text.replace(artifact, '');
            }}
            
            return text.trim() || 'NO_TEXT_EXTRACTED';
        }} else {{
            return 'NO_RESPONSE_ELEMENT';
        }}
    }})()
    """
    
    result = tab.call_method("Runtime.evaluate", expression=response_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get response text. Result: {result}")
    
    response = result['result']['value']
    
    if response in ['NO_TEXT_EXTRACTED', 'NO_RESPONSE_ELEMENT']:
        raise ValueError(f"Could not extract response text: {response}")
    
    return response

# Example usage in a loop
print("ChatGPT PyChrome Test (Fixed Version)")
print("=====================================")
print("This version uses improved selectors and error handling.")
print()

while True:
    question = input("Enter your question (or 'quit' to exit): ")
    if question.lower() == 'quit':
        break
    try:
        print("Processing your question...")
        answer = ask_question(question)
        print("\n" + "="*50)
        print("Answer:")
        print("="*50)
        print(answer)
        print("="*50 + "\n")
    except Exception as e:
        print(f"Error: {str(e)}")
        print("This might be due to:")
        print("1. ChatGPT page not loaded or changed")
        print("2. Network issues")
        print("3. UI elements changed (selectors need updating)")
        print("4. Chrome debug session disconnected")
        print()

# Stop and close the tab
tab.stop()
print("Session ended.")
