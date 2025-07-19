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

def send_cdp_command(ws, method, params, timeout=20):
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
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise Exception(f"Timeout waiting for response to {method}")
            try:
                response = json.loads(ws.recv())
                if "id" in response and response["id"] == command_id:
                    if "error" in response:
                        print(f"CDP warning for {method}: {response['error']['message']}")
                        # For some methods, errors might be non-fatal
                        if method in ["DOM.enable", "Runtime.enable"]:
                            return {"result": {}}  # Return empty result to continue
                        raise Exception(f"CDP error: {response['error']['message']}")
                    return response
            except WebSocketTimeoutException:
                continue  # Keep trying until overall timeout
    except WebSocketTimeoutException:
        raise Exception(f"Timeout waiting for response to {method}")
    except WebSocketConnectionClosedException:
        raise Exception("WebSocket connection closed unexpectedly")

def debug_grok_page():
    """Debug the Grok page to find the correct selectors."""
    try:
        ws_url = get_websocket_url(target_url_contains="grok.com")
        print(f"Connecting to: {ws_url}")
        ws = create_connection(ws_url, timeout=15)
    except Exception as e:
        print(f"Failed to connect to Grok tab: {e}")
        return

    try:
        print("Enabling DOM and Runtime...")
        send_cdp_command(ws, "DOM.enable", {})
        send_cdp_command(ws, "Runtime.enable", {})
        
        print("Getting page info...")
        
        # Get page title
        result = send_cdp_command(ws, "Runtime.evaluate", {
            "expression": "document.title",
            "returnByValue": True
        })
        title = result.get("result", {}).get("result", {}).get("value", "Unknown")
        print(f"Page title: {title}")
        
        # Check for common input selectors
        input_selectors = [
            "textarea",
            "input[type='text']",
            "[contenteditable='true']",
            "[data-testid*='input']",
            "[data-testid*='textarea']",
            "[data-testid*='prompt']",
            "[placeholder*='Ask']",
            "[placeholder*='Type']",
            "[placeholder*='Message']",
            ".input",
            ".textarea",
            "#input",
            "#textarea"
        ]
        
        print("\nChecking for input elements:")
        for selector in input_selectors:
            try:
                result = send_cdp_command(ws, "Runtime.evaluate", {
                    "expression": f"document.querySelectorAll('{selector}').length",
                    "returnByValue": True
                })
                count = result.get("result", {}).get("result", {}).get("value", 0)
                if count > 0:
                    print(f"  ✓ Found {count} elements with selector: {selector}")
                    
                    # Get more details about the first element
                    result = send_cdp_command(ws, "Runtime.evaluate", {
                        "expression": f"""
                            (() => {{
                                const el = document.querySelector('{selector}');
                                if (el) {{
                                    return {{
                                        tagName: el.tagName,
                                        placeholder: el.placeholder || '',
                                        id: el.id || '',
                                        className: el.className || '',
                                        dataset: Object.keys(el.dataset).map(k => k + '=' + el.dataset[k]).join(', ')
                                    }};
                                }}
                                return null;
                            }})()
                        """,
                        "returnByValue": True
                    })
                    details = result.get("result", {}).get("result", {}).get("value", {})
                    if details:
                        print(f"    Details: {details}")
            except Exception as e:
                print(f"  Error checking {selector}: {e}")
        
        # Check for conversation/message containers
        message_selectors = [
            "[data-testid*='conversation']",
            "[data-testid*='message']",
            "[data-testid*='turn']",
            "[data-testid*='chat']",
            ".message",
            ".conversation",
            ".chat-message",
            "[role='log']",
            "[role='main']"
        ]
        
        print("\nChecking for message/conversation elements:")
        for selector in message_selectors:
            try:
                result = send_cdp_command(ws, "Runtime.evaluate", {
                    "expression": f"document.querySelectorAll('{selector}').length",
                    "returnByValue": True
                })
                count = result.get("result", {}).get("result", {}).get("value", 0)
                if count > 0:
                    print(f"  ✓ Found {count} elements with selector: {selector}")
            except Exception as e:
                print(f"  Error checking {selector}: {e}")
        
        # Get all data-testid attributes
        print("\nGetting all data-testid attributes:")
        result = send_cdp_command(ws, "Runtime.evaluate", {
            "expression": """
                (() => {
                    const elements = document.querySelectorAll('[data-testid]');
                    const testIds = new Set();
                    elements.forEach(el => {
                        if (el.dataset.testid) {
                            testIds.add(el.dataset.testid);
                        }
                    });
                    return Array.from(testIds).sort();
                })()
            """,
            "returnByValue": True
        })
        test_ids = result.get("result", {}).get("result", {}).get("value", [])
        if test_ids:
            print("  Found data-testid values:")
            for test_id in test_ids:
                print(f"    - {test_id}")
        
    except Exception as e:
        print(f"Error during debugging: {e}")
    finally:
        ws.close()

if __name__ == "__main__":
    debug_grok_page()
