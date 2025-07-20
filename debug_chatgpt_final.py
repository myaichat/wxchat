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

def find_actual_send_button():
    print("=== Finding Actual Send Button ===")
    
    # First, clear the textarea
    tab.call_method("Runtime.evaluate", 
        expression="document.querySelector('#prompt-textarea').value = '';")
    
    # Get buttons before entering text
    result_before = tab.call_method("Runtime.evaluate", 
        expression="""
        Array.from(document.querySelectorAll('button')).filter(btn => {
            const rect = btn.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        }).map(btn => ({
            disabled: btn.disabled,
            className: btn.className,
            ariaLabel: btn.getAttribute('aria-label')
        }))
        """, 
        returnByValue=True)
    buttons_before = result_before.get('result', {}).get('value', [])
    disabled_before = sum(1 for btn in buttons_before if btn['disabled'])
    
    print(f"Buttons before text: {len(buttons_before)} total, {disabled_before} disabled")
    
    # Now enter text
    tab.call_method("Runtime.evaluate", 
        expression="""
        const textarea = document.querySelector('#prompt-textarea');
        textarea.value = 'test message';
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        textarea.dispatchEvent(new Event('change', { bubbles: true }));
        """)
    
    time.sleep(0.5)  # Wait for UI to update
    
    # Get buttons after entering text
    result_after = tab.call_method("Runtime.evaluate", 
        expression="""
        Array.from(document.querySelectorAll('button')).filter(btn => {
            const rect = btn.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        }).map(btn => ({
            disabled: btn.disabled,
            className: btn.className,
            ariaLabel: btn.getAttribute('aria-label'),
            innerHTML: btn.innerHTML.substring(0, 100)
        }))
        """, 
        returnByValue=True)
    buttons_after = result_after.get('result', {}).get('value', [])
    disabled_after = sum(1 for btn in buttons_after if btn['disabled'])
    
    print(f"Buttons after text: {len(buttons_after)} total, {disabled_after} disabled")
    
    # Find buttons that changed from disabled to enabled
    print("\n=== Buttons that became enabled ===")
    for i, (before, after) in enumerate(zip(buttons_before, buttons_after)):
        if before['disabled'] and not after['disabled']:
            print(f"Button {i} became enabled:")
            print(f"  Aria Label: {after['ariaLabel']}")
            print(f"  Class: {after['className']}")
            print(f"  HTML: {after['innerHTML']}")
            print()
    
    # Also look for buttons that are enabled and in the composer area
    print("=== All enabled buttons in composer area ===")
    result = tab.call_method("Runtime.evaluate", 
        expression="""
        Array.from(document.querySelectorAll('button')).filter(btn => {
            const rect = btn.getBoundingClientRect();
            const isVisible = rect.width > 0 && rect.height > 0;
            const isEnabled = !btn.disabled;
            const inComposer = btn.closest('[class*="composer"]') || 
                             btn.closest('form') || 
                             btn.closest('[class*="input"]') ||
                             btn.parentElement?.querySelector('#prompt-textarea');
            return isVisible && isEnabled && inComposer;
        }).map((btn, index) => ({
            index: index,
            ariaLabel: btn.getAttribute('aria-label'),
            className: btn.className,
            innerHTML: btn.innerHTML.substring(0, 150),
            outerHTML: btn.outerHTML.substring(0, 200)
        }))
        """, 
        returnByValue=True)
    composer_buttons = result.get('result', {}).get('value', [])
    
    for btn in composer_buttons:
        print(f"Composer Button {btn['index']}:")
        print(f"  Aria Label: {btn['ariaLabel']}")
        print(f"  Class: {btn['className']}")
        print(f"  HTML: {btn['outerHTML']}")
        print()

# Run the analysis
find_actual_send_button()

# Stop the tab
tab.stop()
print("\nFinal debug complete!")
