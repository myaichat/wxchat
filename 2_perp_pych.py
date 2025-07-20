import json
import time
import itertools
from websocket import create_connection  # pip install websocket-client

class CDPClient:
    def __init__(self, ws_url):
        self.ws = create_connection(ws_url)
        self.id_gen = itertools.count(1)
        self.results = {}

    def send(self, method, params=None):
        if params is None:
            params = {}
        cmd_id = next(self.id_gen)
        command = {"id": cmd_id, "method": method, "params": params}
        self.ws.send(json.dumps(command))
        return cmd_id

    def receive(self, cmd_id):
        while True:
            message = self.ws.recv()
            resp = json.loads(message)
            if 'id' in resp and resp['id'] == cmd_id:
                if 'error' in resp:
                    raise Exception(f"CDP Error: {resp['error']}")
                return resp.get('result')
            elif 'method' in resp:
                pass

    def evaluate(self, expression, return_by_value=True):
        params = {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": True
        }
        cmd_id = self.send("Runtime.evaluate", params)
        result = self.receive(cmd_id)
        if 'result' in result:
            return result['result'].get('value')
        return None

def main():
    ws_url = "ws://localhost:9222/devtools/page/F583A4254DC132512B2654E4517790F0"
    try:
        client = CDPClient(ws_url)
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # Enable necessary domains
    client.send("Runtime.enable")
    client.receive(1)  # Wait for enable response

    # Function to get page info for debug
    title = client.evaluate("document.title")
    print(f"Connected to page: {title}")

    # Debug: Check for contenteditable or textarea
    debug_input = client.evaluate("""
    ( () => {
        const textarea = document.querySelector('textarea');
        const contenteditable = document.querySelector('div[contenteditable="true"]');
        return {
            textarea: !!textarea,
            contenteditable: !!contenteditable,
            roleTextbox: !!document.querySelector('[role="textbox"]')
        };
    })()
    """)
    print("Debug input elements:", debug_input)

    # Function to ask a question
    def ask_question(question):
        js = f"""
        (async () => {{
            let inputElement = document.querySelector('div[contenteditable="true"]') || document.querySelector('[role="textbox"]');
            if (!inputElement) {{
                inputElement = document.querySelector('textarea');
            }}
            if (!inputElement) {{
                return 'No input element found';
            }}
            inputElement.focus();
            if (inputElement.tagName === 'DIV') {{
                inputElement.textContent = '{question.replace("'", "\\'").replace('\\', '\\\\')}';
            }} else {{
                inputElement.value = '{question.replace("'", "\\'").replace('\\', '\\\\')}';
            }}
            inputElement.dispatchEvent(new Event('input', {{ bubbles: true, composed: true }}));
            await new Promise(resolve => setTimeout(resolve, 500));
            const buttonSelector = 'button[aria-label^="Submit"], button[type="submit"], button[class*="submit"], button.absolute.right, button:has(> svg), button:has(svg), button[class*="send"]';
            const submitButton = document.querySelector(buttonSelector);
            if (submitButton) {{
                submitButton.click();
                return 'Clicked submit button';
            }} else {{
                // Simulate Enter key press
                const eventOpts = {{ bubbles: true, composed: true, key: 'Enter', code: 'Enter', which: 13, keyCode: 13, shiftKey: false }};
                inputElement.dispatchEvent(new KeyboardEvent('keydown', eventOpts));
                inputElement.dispatchEvent(new KeyboardEvent('keypress', eventOpts));
                inputElement.dispatchEvent(new KeyboardEvent('keyup', eventOpts));
                return 'Simulated Enter key press';
            }}
        }})();
        """
        result = client.evaluate(js)
        print("Submit result:", result if result else 'No return value (likely success)')

    # Function to get answer count
    def get_answer_count():
        js = 'document.querySelectorAll(\'[class*="prose"]\').length'
        count = client.evaluate(js)
        return count or 0

    # Function to get latest answer
    def get_latest_answer():
        js = """
        const proses = document.querySelectorAll('[class*="prose"]');
        if (proses.length > 0) {
            const last = proses[proses.length - 1];
            return last.innerText || last.textContent;
        }
        return '';
        """
        return client.evaluate(js) or ''

    # Debug for answer selector
    debug_answer = client.evaluate("""
    document.querySelectorAll('[class*="prose"]').length + ' prose, ' + document.querySelectorAll('div.markdown').length + ' markdown, ' + document.querySelectorAll('div[class*="answer"]').length + ' answer'
    """)
    print("Debug answer counts:", debug_answer)

    # Function to wait for new answer
    def wait_for_new_answer(timeout=120, poll_interval=1, stable_checks=5):
        initial_count = get_answer_count()
        initial_text = get_latest_answer()
        start_time = time.time()
        print(f"Initial answer count: {initial_count}, initial text length: {len(initial_text)}")

        # Wait for change
        while time.time() - start_time < timeout:
            current_count = get_answer_count()
            current_text = get_latest_answer()
            if current_count > initial_count or (current_count == initial_count and current_text != initial_text and current_text):
                print(f"Detected change: count {current_count}, text length {len(current_text)}")
                break
            time.sleep(poll_interval)

        if get_answer_count() == initial_count and get_latest_answer() == initial_text:
            return "Timeout: No new answer detected."

        # Stabilize
        prev_text = ''
        stable_count = 0
        while stable_count < stable_checks and time.time() - start_time < timeout:
            current_text = get_latest_answer()
            if current_text == prev_text and current_text != '':
                stable_count += 1
            else:
                stable_count = 0
                prev_text = current_text
            time.sleep(poll_interval)
            print(f"Stabilizing: stable_count {stable_count}, text length {len(current_text)}")  # Debug

        if stable_count < stable_checks:
            return "Timeout: Answer did not stabilize. Last text: " + prev_text[:200]  # Truncate for print

        return prev_text

    print("Connected to Perplexity chat tab. Type 'exit' to quit.")
    while True:
        question = input("Your question: ")
        if question.lower() == 'exit':
            break
        print("Initial answer count before ask:", get_answer_count())
        ask_question(question)
        time.sleep(1)
        print("Waiting for answer...")
        answer = wait_for_new_answer()
        print("Answer:\n", answer)

    client.ws.close()

if __name__ == "__main__":
    main()