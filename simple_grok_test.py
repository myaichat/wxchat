import json
import time
import uuid
import requests
from websocket import create_connection, WebSocketTimeoutException, WebSocketConnectionClosedException

def get_websocket_url(port=9222, target_url_contains="grok.com"):
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

def send_simple_command(ws, expression, timeout=10):
    """Send a simple Runtime.evaluate command."""
    ws.settimeout(timeout)
    command_id = str(uuid.uuid4())
    payload = {
        "id": command_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expression,
            "returnByValue": True
        }
    }
    try:
        ws.send(json.dumps(payload))
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise Exception(f"Timeout waiting for response")
            try:
                response = json.loads(ws.recv())
                if "id" in response and response["id"] == command_id:
                    if "error" in response:
                        raise Exception(f"Error: {response['error']['message']}")
                    return response.get("result", {}).get("result", {}).get("value")
            except WebSocketTimeoutException:
                continue
    except WebSocketTimeoutException:
        raise Exception(f"Timeout waiting for response")
    except WebSocketConnectionClosedException:
        raise Exception("WebSocket connection closed unexpectedly")

def test_grok_simple():
    """Simple test without DOM.enable."""
    try:
        ws_url = get_websocket_url(target_url_contains="grok.com")
        print(f"Connecting to: {ws_url}")
        ws = create_connection(ws_url, timeout=10)
    except Exception as e:
        print(f"Failed to connect to Grok tab: {e}")
        return

    try:
        print("Testing basic JavaScript execution...")
        
        # Test basic functionality
        title = send_simple_command(ws, "document.title")
        print(f"Page title: {title}")
        
        url = send_simple_command(ws, "window.location.href")
        print(f"Page URL: {url}")
        
        # Check for textarea elements
        textarea_count = send_simple_command(ws, "document.querySelectorAll('textarea').length")
        print(f"Number of textarea elements: {textarea_count}")
        
        if textarea_count > 0:
            # Get details about textareas
            textarea_info = send_simple_command(ws, """
                (() => {
                    const textareas = document.querySelectorAll('textarea');
                    return Array.from(textareas).map((ta, i) => ({
                        index: i,
                        placeholder: ta.placeholder || '',
                        id: ta.id || '',
                        className: ta.className || '',
                        visible: ta.offsetParent !== null
                    }));
                })()
            """)
            print(f"Textarea details: {json.dumps(textarea_info, indent=2)}")
        
        # Check for input elements
        input_count = send_simple_command(ws, "document.querySelectorAll('input').length")
        print(f"Number of input elements: {input_count}")
        
        # Check for contenteditable elements
        contenteditable_count = send_simple_command(ws, "document.querySelectorAll('[contenteditable=\"true\"]').length")
        print(f"Number of contenteditable elements: {contenteditable_count}")
        
        # Try to find any element with "grok" or "ask" in placeholder
        grok_inputs = send_simple_command(ws, """
            (() => {
                const allInputs = document.querySelectorAll('input, textarea, [contenteditable="true"]');
                const grokInputs = [];
                allInputs.forEach((el, i) => {
                    const placeholder = (el.placeholder || '').toLowerCase();
                    const text = (el.textContent || '').toLowerCase();
                    if (placeholder.includes('grok') || placeholder.includes('ask') || 
                        placeholder.includes('type') || placeholder.includes('message') ||
                        text.includes('ask') || text.includes('type')) {
                        grokInputs.push({
                            index: i,
                            tagName: el.tagName,
                            placeholder: el.placeholder || '',
                            textContent: el.textContent || '',
                            id: el.id || '',
                            className: el.className || ''
                        });
                    }
                });
                return grokInputs;
            })()
        """)
        print(f"Potential Grok input elements: {json.dumps(grok_inputs, indent=2)}")
        
        # Try to send a simple message using the first textarea if available
        if textarea_count > 0:
            print("\nAttempting to send a test message...")
            
            # Focus and type into the first textarea
            result = send_simple_command(ws, """
                (() => {
                    const textarea = document.querySelector('textarea');
                    if (textarea) {
                        textarea.focus();
                        textarea.value = 'Hello from automation test';
                        
                        // Trigger input event
                        textarea.dispatchEvent(new Event('input', { bubbles: true }));
                        
                        // Try to find and click send button
                        const sendButtons = document.querySelectorAll('button');
                        let sendButton = null;
                        
                        for (let btn of sendButtons) {
                            const text = (btn.textContent || '').toLowerCase();
                            const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                            if (text.includes('send') || ariaLabel.includes('send') || 
                                text.includes('submit') || ariaLabel.includes('submit')) {
                                sendButton = btn;
                                break;
                            }
                        }
                        
                        if (sendButton) {
                            sendButton.click();
                            return 'Message sent successfully';
                        } else {
                            // Try pressing Enter
                            textarea.dispatchEvent(new KeyboardEvent('keydown', {
                                key: 'Enter',
                                code: 'Enter',
                                keyCode: 13,
                                bubbles: true
                            }));
                            return 'Tried sending with Enter key';
                        }
                    }
                    return 'No textarea found';
                })()
            """)
            print(f"Send result: {result}")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        ws.close()

if __name__ == "__main__":
    test_grok_simple()
