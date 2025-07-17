import json
import time
import uuid
import requests
from websocket import create_connection, WebSocketTimeoutException, WebSocketConnectionClosedException

def get_websocket_url(port=9222, target_url_contains="claude.ai"):
    """Fetch the WebSocket URL for the tab containing the target URL."""
    try:
        response = requests.get(f"http://localhost:{port}/json")
        tabs = response.json()
        for tab in tabs:
            if target_url_contains in tab.get("url", ""):
                return tab["webSocketDebuggerUrl"]
        raise Exception(f"No tab found with URL containing '{target_url_contains}'.")
    except Exception as e:
        raise Exception(f"Failed to fetch WebSocket URL: {e}")

WS_URL = get_websocket_url(target_url_contains="claude.ai")

WS_URL = get_websocket_url()

def send_cdp_command(ws, method, params, timeout=10):
    """Send a CDP command with timeout."""
    ws.settimeout(timeout)
    command_id = str(uuid.uuid4())
    payload = {
        "id": command_id,
        "method": method,
        "params": params
    }
    try:
        ws.send(json.dumps(payload))
        while True:
            response = json.loads(ws.recv())
            if "id" in response and response["id"] == command_id:
                if "error" in response:
                    raise Exception(f"CDP error: {response['error']['message']}")
                return response
    except WebSocketTimeoutException:
        raise Exception(f"Timeout waiting for response to {method}")
    except WebSocketConnectionClosedException:
        raise Exception("WebSocket connection closed unexpectedly")

def enable_dom_and_runtime(ws):
    """Enable DOM and Runtime domains in CDP."""
    send_cdp_command(ws, "DOM.enable", {})
    send_cdp_command(ws, "Runtime.enable", {})

def get_element(ws, selector):
    """Find a DOM element by CSS selector."""
    result = send_cdp_command(ws, "DOM.querySelector", {
        "nodeId": 1,  # Document root
        "selector": selector
    })
    return result.get("result", {}).get("nodeId", 0)

def get_element_text(ws, node_id):
    """Get the text content of a DOM node."""
    result = send_cdp_command(ws, "Runtime.evaluate", {
        "expression": f"document.querySelectorAll('div.conversation-item')[{node_id}].innerText",
        "returnByValue": True
    })
    return result.get("result", {}).get("result", {}).get("value", "")

def send_chat_message(ws, message, input_selector="textarea"):
    """Send a chat message by typing into the input field and pressing Enter."""
    input_node_id = get_element(ws, input_selector)
    if not input_node_id:
        raise Exception("Input element not found")

    send_cdp_command(ws, "DOM.focus", {"nodeId": input_node_id})

    for char in message:
        send_cdp_command(ws, "Input.dispatchKeyEvent", {
            "type": "char",
            "text": char
        })
        time.sleep(0.01)

    send_cdp_command(ws, "Input.dispatchKeyEvent", {
        "type": "keyDown",
        "key": "Enter",
        "code": "Enter",
        "windowsVirtualKeyCode": 13
    })
    time.sleep(0.1)
    send_cdp_command(ws, "Input.dispatchKeyEvent", {
        "type": "keyUp",
        "key": "Enter",
        "code": "Enter",
        "windowsVirtualKeyCode": 13
    })

def get_chat_response(ws, response_selector, max_attempts=10, wait_time=1):
    """Retrieve the latest chat response from the DOM."""
    attempts = 0
    last_response = ""
    stable_count = 0
    stable_threshold = 2

    while attempts < max_attempts:
        result = send_cdp_command(ws, "DOM.querySelectorAll", {
            "nodeId": 1,
            "selector": response_selector
        })
        node_ids = result.get("result", {}).get("nodeIds", [])

        if not node_ids:
            time.sleep(wait_time)
            attempts += 1
            continue

        text = get_element_text(ws, len(node_ids)-1)

        if text == last_response:
            stable_count += 1
            if stable_count >= stable_threshold:
                return text
        else:
            stable_count = 0
            last_response = text

        time.sleep(wait_time)
        attempts += 1

    return last_response if last_response else None

def main():
    try:
        ws = create_connection(WS_URL, timeout=10)
    except Exception as e:
        print(f"Failed to connect to WebSocket: {e}")
        return

    try:
        enable_dom_and_runtime(ws)
        chat_message = "Hello, can you provide an update on the Ukraine battlefield?"
        send_chat_message(ws, chat_message)
        response_selector = "div.conversation-item"  # Replace with actual selector
        response = get_chat_response(ws, response_selector)
        
        if response:
            print("Response:", response)
        else:
            print("No response received or timeout occurred.")

    finally:
        ws.close()

if __name__ == "__main__":
    main()