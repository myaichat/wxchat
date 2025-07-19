import pychrome
import time

# Connect to the browser
browser = pychrome.Browser(url="http://localhost:9222")

# Find the specific tab by ID
tab_id = "8D25B8EDED124ED7635252EF0F0E4217"
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
    # Selectors
    input_selector = 'rich-textarea > div > p'
    send_button_selector = 'div[class*="send-button-container"] > button'
    response_selector = 'message-content[class*="model-response-text"]'

    # Get current number of responses
    count_expr = f"document.querySelectorAll('{response_selector}').length"
    result = tab.call_method("Runtime.evaluate", expression=count_expr, returnByValue=True)
    
    # Check if the result has the expected structure
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get response count. Result: {result}")
    
    num_responses = result['result']['value']

    # Set the input text
    input_expr = f"document.querySelector('{input_selector}').textContent = `{question.replace('`', '\\`')}`;"
    tab.call_method("Runtime.evaluate", expression=input_expr)

    # Small delay to simulate typing
    time.sleep(1)

    # Click send button
    click_expr = f"document.querySelector('{send_button_selector}').click();"
    tab.call_method("Runtime.evaluate", expression=click_expr)

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

    # Wait additional time for streaming to complete (adjust as needed)
    time.sleep(5)

    # Get the latest response text
    index = current_num - 1
    response_expr = f"document.querySelectorAll('{response_selector}')[{index}].innerText"
    result = tab.call_method("Runtime.evaluate", expression=response_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get response text. Result: {result}")
    
    response = result['result']['value']
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
