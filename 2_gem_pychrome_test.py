import pychrome
import time
import json

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

# Wait a bit for the page to be ready
time.sleep(2)

# Test evaluation
test_expr = "document.title"
test_result = tab.call_method("Runtime.evaluate", expression=test_expr, returnByValue=True)
print("Test result:", json.dumps(test_result, indent=2))

def handle_evaluate_result(eval_result):
    result = eval_result['result']
    if 'exceptionDetails' in result:
        exception = result['exceptionDetails']['exception']['description']
        raise ValueError(f"JavaScript evaluation error: {exception}")
    if 'value' not in result:
        raise ValueError(f"No 'value' in result: {json.dumps(result)}")
    return result['value']

# Updated selectors - adjust based on inspection if needed
input_selector = 'div[contenteditable="true"][aria-label*="prompt"], div[contenteditable="true"][role="textbox"]'  # Possible input selectors
send_button_selector = 'button[aria-label="Send message"], button[class*="send-button"]'
response_selector = '[class*="model-message"], [class*="response-message"], model-response'  # Possible response containers

def ask_question(question, timeout=30):
    # Get current number of responses
    expr = f"document.querySelectorAll('{response_selector}').length"
    eval_result = tab.call_method("Runtime.evaluate", expression=expr, returnByValue=True)
    num_responses = handle_evaluate_result(eval_result)

    # Set the input text
    expr = f"""(function() {{
        let input = document.querySelector('{input_selector}');
        if (!input) return 'Input not found';
        input.textContent = `{question.replace('`', '\\`')}`;
        return 'OK';
    }})();"""
    eval_result = tab.call_method("Runtime.evaluate", expression=expr, returnByValue=True)
    set_result = handle_evaluate_result(eval_result)
    if set_result != 'OK':
        raise ValueError(set_result)

    # Small delay to simulate typing
    time.sleep(1)

    # Click send button
    expr = f"""(function() {{
        let button = document.querySelector('{send_button_selector}');
        if (!button) return 'Button not found';
        button.click();
        return 'OK';
    }})();"""
    eval_result = tab.call_method("Runtime.evaluate", expression=expr, returnByValue=True)
    click_result = handle_evaluate_result(eval_result)
    if click_result != 'OK':
        raise ValueError(click_result)

    # Wait for new response to appear
    start_time = time.time()
    while time.time() - start_time < timeout:
        eval_result = tab.call_method("Runtime.evaluate", expression=expr, returnByValue=True)
        current_num = handle_evaluate_result(eval_result)
        if current_num > num_responses:
            break
        time.sleep(1)
    else:
        raise TimeoutError("Timeout waiting for response to appear.")

    # Wait additional time for streaming to complete (adjust as needed)
    time.sleep(5)

    # Get the latest response text
    index = current_num - 1
    expr = f"""(function() {{
        let responses = document.querySelectorAll('{response_selector}');
        if (responses.length <= {index}) return 'Response not found';
        return responses[{index}].innerText;
    }})();"""
    eval_result = tab.call_method("Runtime.evaluate", expression=expr, returnByValue=True)
    response = handle_evaluate_result(eval_result)

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