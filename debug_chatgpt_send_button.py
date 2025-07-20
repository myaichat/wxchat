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

def find_send_button():
    print("=== Finding Send Button ===")
    
    # Look for the actual send button - it's usually near the textarea
    try:
        result = tab.call_method("Runtime.evaluate", 
            expression="""
            // Look for buttons in the composer area
            const composerButtons = Array.from(document.querySelectorAll('button')).filter(btn => {
                const rect = btn.getBoundingClientRect();
                const isVisible = rect.width > 0 && rect.height > 0;
                const hasArrowOrSend = btn.innerHTML.includes('arrow') || 
                                     btn.innerHTML.includes('send') || 
                                     btn.getAttribute('aria-label')?.toLowerCase().includes('send') ||
                                     btn.innerHTML.includes('M8 12l-3 3 3 3m5-6H4') || // common send arrow path
                                     btn.innerHTML.includes('M2.01 21L23 12 2.01 3 2 10l15 2-15 2z'); // another send icon path
                return isVisible && hasArrowOrSend;
            });
            
            composerButtons.map((btn, index) => ({
                index: index,
                outerHTML: btn.outerHTML.substring(0, 300),
                disabled: btn.disabled,
                ariaLabel: btn.getAttribute('aria-label'),
                dataTestId: btn.getAttribute('data-testid'),
                className: btn.className,
                innerHTML: btn.innerHTML.substring(0, 200)
            }))
            """, 
            returnByValue=True)
        buttons = result.get('result', {}).get('value', [])
        print(f"Potential send buttons found: {len(buttons)}")
        for btn in buttons:
            print(f"Button {btn['index']}:")
            print(f"  Disabled: {btn['disabled']}")
            print(f"  Aria Label: {btn['ariaLabel']}")
            print(f"  Class: {btn['className']}")
            print(f"  HTML: {btn['outerHTML']}")
            print()
    except Exception as e:
        print(f"Send button search error: {e}")

def test_input_interaction():
    print("=== Testing Input Interaction ===")
    
    # Test setting value on the textarea
    try:
        result = tab.call_method("Runtime.evaluate", 
            expression="""
            const textarea = document.querySelector('#prompt-textarea');
            if (textarea) {
                textarea.value = 'test message';
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                textarea.dispatchEvent(new Event('change', { bubbles: true }));
                'SUCCESS: Set textarea value'
            } else {
                'ERROR: Textarea not found'
            }
            """, 
            returnByValue=True)
        status = result.get('result', {}).get('value', 'ERROR')
        print(f"Textarea interaction: {status}")
    except Exception as e:
        print(f"Textarea interaction error: {e}")
    
    # Now check if any send buttons became enabled
    try:
        result = tab.call_method("Runtime.evaluate", 
            expression="""
            Array.from(document.querySelectorAll('button')).filter(btn => {
                const rect = btn.getBoundingClientRect();
                const isVisible = rect.width > 0 && rect.height > 0;
                const nearTextarea = btn.closest('form') || btn.closest('[class*="composer"]') || btn.closest('[class*="input"]');
                return isVisible && nearTextarea && !btn.disabled;
            }).map((btn, index) => ({
                index: index,
                disabled: btn.disabled,
                ariaLabel: btn.getAttribute('aria-label'),
                className: btn.className,
                innerHTML: btn.innerHTML.substring(0, 100)
            }))
            """, 
            returnByValue=True)
        buttons = result.get('result', {}).get('value', [])
        print(f"Enabled buttons near textarea: {len(buttons)}")
        for btn in buttons:
            print(f"  Button {btn['index']}: {btn['ariaLabel']} - {btn['className'][:50]}...")
    except Exception as e:
        print(f"Enabled buttons search error: {e}")

# Run tests
find_send_button()
test_input_interaction()

# Stop the tab
tab.stop()
print("\nSend button debug complete!")
