import pychrome
import time

# Connect to the browser
browser = pychrome.Browser(url="http://localhost:9222")

# Find the ChatGPT tab by ID
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

def debug_selectors():
    print("=== Debugging ChatGPT Selectors ===")
    
    # Test various input selectors
    input_selectors = [
        '#prompt-textarea',
        'textarea[placeholder*="Message"]',
        'textarea[data-id="root"]',
        'div[contenteditable="true"]',
        'textarea',
        '[role="textbox"]',
        'div[role="textbox"]'
    ]
    
    print("\n--- Testing Input Selectors ---")
    for selector in input_selectors:
        try:
            result = tab.call_method("Runtime.evaluate", 
                expression=f"document.querySelector('{selector}') ? 'FOUND' : 'NOT FOUND'", 
                returnByValue=True)
            status = result.get('result', {}).get('value', 'ERROR')
            print(f"{selector}: {status}")
        except Exception as e:
            print(f"{selector}: ERROR - {e}")
    
    # Test send button selectors
    send_selectors = [
        'button[data-testid="send-button"]',
        'button[aria-label*="Send"]',
        'button[type="submit"]',
        'button svg[data-icon="send"]',
        'button:has(svg)',
        '[data-testid="send-button"]'
    ]
    
    print("\n--- Testing Send Button Selectors ---")
    for selector in send_selectors:
        try:
            result = tab.call_method("Runtime.evaluate", 
                expression=f"document.querySelector('{selector}') ? 'FOUND' : 'NOT FOUND'", 
                returnByValue=True)
            status = result.get('result', {}).get('value', 'ERROR')
            print(f"{selector}: {status}")
        except Exception as e:
            print(f"{selector}: ERROR - {e}")
    
    # Test response selectors
    response_selectors = [
        '[data-message-author-role="assistant"] .markdown',
        '[data-message-author-role="assistant"]',
        '.markdown',
        '[role="presentation"] .markdown',
        'div[data-message-id]',
        '.prose',
        'article'
    ]
    
    print("\n--- Testing Response Selectors ---")
    for selector in response_selectors:
        try:
            result = tab.call_method("Runtime.evaluate", 
                expression=f"document.querySelectorAll('{selector}').length", 
                returnByValue=True)
            count = result.get('result', {}).get('value', 'ERROR')
            print(f"{selector}: {count} elements found")
        except Exception as e:
            print(f"{selector}: ERROR - {e}")
    
    # Get page structure info
    print("\n--- Page Structure Analysis ---")
    try:
        # Get all textareas
        result = tab.call_method("Runtime.evaluate", 
            expression="Array.from(document.querySelectorAll('textarea')).map(el => ({tag: el.tagName, id: el.id, class: el.className, placeholder: el.placeholder}))", 
            returnByValue=True)
        textareas = result.get('result', {}).get('value', [])
        print(f"Textareas found: {len(textareas)}")
        for i, ta in enumerate(textareas):
            print(f"  {i+1}: {ta}")
    except Exception as e:
        print(f"Textarea analysis error: {e}")
    
    try:
        # Get all buttons
        result = tab.call_method("Runtime.evaluate", 
            expression="Array.from(document.querySelectorAll('button')).map(el => ({text: el.textContent.trim(), testid: el.getAttribute('data-testid'), ariaLabel: el.getAttribute('aria-label')}))", 
            returnByValue=True)
        buttons = result.get('result', {}).get('value', [])
        print(f"\nButtons found: {len(buttons)}")
        for i, btn in enumerate(buttons[:10]):  # Show first 10
            print(f"  {i+1}: {btn}")
    except Exception as e:
        print(f"Button analysis error: {e}")

# Run debug
debug_selectors()

# Stop the tab
tab.stop()
print("\nDebug complete!")
