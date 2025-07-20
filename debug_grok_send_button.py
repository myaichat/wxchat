import pychrome
import time

# Connect to the browser
browser = pychrome.Browser(url="http://localhost:9222")

# Find the specific tab by ID
tab_id = "2E53C20504E50BBFD36C0AA987A63DD3"
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

print("🔍 DEBUGGING GROK SEND BUTTON")
print("=" * 50)

# First, let's see what buttons are available
debug_buttons_expr = """
(() => {
    const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
    
    return buttons.map((btn, index) => {
        return {
            index: index,
            tagName: btn.tagName,
            type: btn.type || 'N/A',
            textContent: btn.textContent?.trim() || 'N/A',
            ariaLabel: btn.getAttribute('aria-label') || 'N/A',
            title: btn.title || 'N/A',
            className: btn.className || 'N/A',
            id: btn.id || 'N/A',
            disabled: btn.disabled,
            visible: btn.offsetParent !== null
        };
    });
})()
"""

result = tab.call_method("Runtime.evaluate", expression=debug_buttons_expr, returnByValue=True)
buttons_info = result.get('result', {}).get('value', [])

print("🔘 Available buttons:")
for btn in buttons_info:
    print(f"  [{btn['index']}] {btn['tagName']} - Text: '{btn['textContent']}' - Aria: '{btn['ariaLabel']}' - Class: '{btn['className']}' - Visible: {btn['visible']}")

print("\n" + "=" * 50)

# Now let's look specifically around the textarea
debug_textarea_area_expr = """
(() => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return 'No textarea found';
    
    // Get the parent container
    const container = textarea.closest('div');
    if (!container) return 'No container found';
    
    // Find all buttons within the container or nearby
    const nearbyButtons = container.querySelectorAll('button');
    
    return {
        textareaInfo: {
            placeholder: textarea.placeholder,
            value: textarea.value,
            parentTagName: textarea.parentElement?.tagName
        },
        nearbyButtons: Array.from(nearbyButtons).map((btn, index) => ({
            index: index,
            textContent: btn.textContent?.trim() || 'N/A',
            ariaLabel: btn.getAttribute('aria-label') || 'N/A',
            title: btn.title || 'N/A',
            className: btn.className || 'N/A',
            disabled: btn.disabled,
            visible: btn.offsetParent !== null,
            innerHTML: btn.innerHTML
        }))
    };
})()
"""

result = tab.call_method("Runtime.evaluate", expression=debug_textarea_area_expr, returnByValue=True)
textarea_area_info = result.get('result', {}).get('value', {})

print("📝 Textarea area info:")
print(f"  Textarea: {textarea_area_info.get('textareaInfo', 'N/A')}")
print("  Nearby buttons:")
for btn in textarea_area_info.get('nearbyButtons', []):
    print(f"    [{btn['index']}] Text: '{btn['textContent']}' - Aria: '{btn['ariaLabel']}' - Class: '{btn['className']}' - Visible: {btn['visible']}")
    print(f"        HTML: {btn['innerHTML'][:100]}...")

print("\n" + "=" * 50)

# Let's also check for SVG icons or other send indicators
debug_send_indicators_expr = """
(() => {
    // Look for elements that might be send buttons (including SVG icons)
    const allElements = Array.from(document.querySelectorAll('*'));
    
    const sendIndicators = allElements.filter(el => {
        const text = (el.textContent || '').toLowerCase();
        const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
        const title = (el.title || '').toLowerCase();
        const className = (el.className || '').toLowerCase();
        
        return (text.includes('send') || ariaLabel.includes('send') || 
                title.includes('send') || className.includes('send') ||
                el.tagName === 'svg' && (ariaLabel.includes('send') || title.includes('send'))) &&
               el.offsetParent !== null; // visible
    });
    
    return sendIndicators.map((el, index) => ({
        index: index,
        tagName: el.tagName,
        textContent: el.textContent?.trim().substring(0, 50) || 'N/A',
        ariaLabel: el.getAttribute('aria-label') || 'N/A',
        title: el.title || 'N/A',
        className: el.className || 'N/A',
        id: el.id || 'N/A',
        clickable: el.tagName === 'BUTTON' || el.onclick !== null || el.getAttribute('role') === 'button'
    }));
})()
"""

result = tab.call_method("Runtime.evaluate", expression=debug_send_indicators_expr, returnByValue=True)
send_indicators = result.get('result', {}).get('value', [])

print("📤 Send indicators found:")
for indicator in send_indicators:
    print(f"  [{indicator['index']}] {indicator['tagName']} - Text: '{indicator['textContent']}' - Aria: '{indicator['ariaLabel']}' - Clickable: {indicator['clickable']}")

print("\n" + "=" * 50)

# Let's set some text in the textarea and see what happens
print("📝 Setting test text in textarea...")

set_text_expr = """
(() => {
    const textarea = document.querySelector('textarea');
    if (textarea) {
        textarea.focus();
        textarea.value = 'Test message';
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        return 'Text set successfully';
    }
    return 'Textarea not found';
})()
"""

result = tab.call_method("Runtime.evaluate", expression=set_text_expr, returnByValue=True)
print(f"Result: {result.get('result', {}).get('value', 'Unknown')}")

time.sleep(2)

# Now check if any buttons changed state after adding text
print("\n🔄 Checking button states after adding text...")

result = tab.call_method("Runtime.evaluate", expression=debug_buttons_expr, returnByValue=True)
buttons_info_after = result.get('result', {}).get('value', [])

print("🔘 Button states after adding text:")
for btn in buttons_info_after:
    if not btn['disabled'] and btn['visible']:
        print(f"  [{btn['index']}] {btn['tagName']} - Text: '{btn['textContent']}' - Aria: '{btn['ariaLabel']}' - Class: '{btn['className']}'")

# Stop and close
print("\n✅ Debug completed!")
tab.stop()
