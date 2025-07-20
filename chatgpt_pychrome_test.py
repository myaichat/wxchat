import pychrome
import time

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
    raise ValueError("Tab with specified ID not found.")

# Start the tab
tab.start()

# Enable Runtime domain
tab.call_method("Runtime.enable")

def ask_question(question, timeout=30):
    # ChatGPT selectors based on debugging
    input_selector = '#prompt-textarea'
    response_selector = 'div[data-message-author-role="assistant"]'

    # Get current number of responses
    count_expr = f"document.querySelectorAll('{response_selector}').length"
    result = tab.call_method("Runtime.evaluate", expression=count_expr, returnByValue=True)
    
    # Check if the result has the expected structure
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get response count. Result: {result}")
    
    num_responses = result['result']['value']

    # Clear and set the input text
    input_expr = f"""
    const textarea = document.querySelector('{input_selector}');
    if (textarea) {{
        textarea.value = '';
        textarea.focus();
        textarea.value = `{question.replace('`', '\\`')}`;
        textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
        textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
        'SUCCESS';
    }} else {{
        'TEXTAREA_NOT_FOUND';
    }}
    """
    result = tab.call_method("Runtime.evaluate", expression=input_expr, returnByValue=True)
    if result.get('result', {}).get('value') != 'SUCCESS':
        raise ValueError("Failed to set textarea value")

    # Small delay to simulate typing
    time.sleep(1)

    # Try to send using Enter key first
    send_expr = f"""
    const textarea = document.querySelector('{input_selector}');
    if (textarea) {{
        textarea.focus();
        const enterEvent = new KeyboardEvent('keydown', {{
            key: 'Enter',
            code: 'Enter',
            keyCode: 13,
            which: 13,
            bubbles: true
        }});
        textarea.dispatchEvent(enterEvent);
        'ENTER_SENT';
    }} else {{
        'TEXTAREA_NOT_FOUND';
    }}
    """
    tab.call_method("Runtime.evaluate", expression=send_expr)

    # Wait a moment and try button click as backup
    time.sleep(0.5)
    
    # Try to find and click send button as backup
    button_click_expr = """
    // Look for enabled buttons near the textarea
    const buttons = Array.from(document.querySelectorAll('button')).filter(btn => {
        const rect = btn.getBoundingClientRect();
        const isVisible = rect.width > 0 && rect.height > 0;
        const isEnabled = !btn.disabled;
        const nearTextarea = btn.closest('form') || 
                           btn.closest('[class*="composer"]') || 
                           btn.closest('[class*="input"]') ||
                           btn.parentElement?.querySelector('#prompt-textarea');
        return isVisible && isEnabled && nearTextarea;
    });
    
    if (buttons.length > 0) {
        // Try to find the most likely send button (usually the last enabled button in composer area)
        const sendButton = buttons[buttons.length - 1];
        sendButton.click();
        'BUTTON_CLICKED';
    } else {
        'NO_BUTTON_FOUND';
    }
    """
    tab.call_method("Runtime.evaluate", expression=button_click_expr)

    # Wait for new response to appear
    start_time = time.time()
    current_num = num_responses
    while time.time() - start_time < timeout:
        result = tab.call_method("Runtime.evaluate", expression=count_expr, returnByValue=True)
        if 'result' in result and 'value' in result['result']:
            current_num = result['result']['value']
            if current_num > num_responses:
                break
        time.sleep(1)
    else:
        raise TimeoutError("Timeout waiting for response to appear.")

    # Wait additional time for streaming to complete
    time.sleep(5)

    # Get the latest response text
    index = current_num - 1
    response_expr = f"""
    const responses = document.querySelectorAll('{response_selector}');
    if (responses.length > {index}) {{
        responses[{index}].innerText || responses[{index}].textContent || 'NO_TEXT';
    }} else {{
        'NO_RESPONSE_ELEMENT';
    }}
    """
    result = tab.call_method("Runtime.evaluate", expression=response_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get response text. Result: {result}")
    
    response = result['result']['value']
    
    if response in ['NO_TEXT', 'NO_RESPONSE_ELEMENT']:
        raise ValueError(f"Could not extract response text: {response}")
    
    return response

# Example usage in a loop
while True:
    question = input("Enter your question (or 'quit' to exit): ")
    if question.lower() == 'quit':
        break
    try:
        answer = ask_question(question)
        print("Answer:", answer)
    except Exception as e:
        print("Error:", str(e))

# Stop and close the tab
tab.stop()
browser.close_tab(tab)
