import pychrome
import time

# Connect to the browser
browser = pychrome.Browser(url="http://localhost:9222")

# Find the specific tab by ID
tab_id = "380F834E4C26E56C7421C30120FC7553"
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

print("🔍 DEBUGGING GROK INTERFACE")
print("=" * 50)

# Navigate to chat if needed
navigate_expr = """
(() => {
    // Look for Chat link/button in sidebar
    const chatLinks = Array.from(document.querySelectorAll('a, button')).filter(el => 
        el.textContent?.trim().toLowerCase() === 'chat' ||
        el.textContent?.trim().toLowerCase().includes('grok')
    );
    
    if (chatLinks.length > 0) {
        chatLinks[0].click();
        return 'Clicked chat link';
    }
    
    return 'No chat link found';
})()
"""

result = tab.call_method("Runtime.evaluate", expression=navigate_expr, returnByValue=True)
print(f"🔄 Navigation: {result.get('result', {}).get('value', 'Unknown')}")

time.sleep(3)

# Find textarea and type test message
find_and_type_expr = """
(() => {
    const textarea = document.querySelector('textarea');
    if (textarea) {
        textarea.focus();
        textarea.value = 'test message';
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        return 'Text set in textarea';
    }
    return 'No textarea found';
})()
"""

result = tab.call_method("Runtime.evaluate", expression=find_and_type_expr, returnByValue=True)
print(f"📝 Text input: {result.get('result', {}).get('value', 'Unknown')}")

time.sleep(1)

# Debug: Find all buttons near the textarea
debug_buttons_expr = """
(() => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return 'No textarea found';
    
    // Get the parent container
    const parent = textarea.closest('form, div, section');
    if (!parent) return 'No parent container found';
    
    // Find all buttons in the parent
    const buttons = parent.querySelectorAll('button');
    const buttonInfo = [];
    
    buttons.forEach((btn, index) => {
        const info = {
            index: index,
            text: btn.textContent?.trim() || '',
            ariaLabel: btn.getAttribute('aria-label') || '',
            title: btn.getAttribute('title') || '',
            type: btn.type || '',
            disabled: btn.disabled,
            className: btn.className || '',
            id: btn.id || '',
            hasIcon: btn.querySelector('svg') !== null,
            innerHTML: btn.innerHTML.substring(0, 100) // First 100 chars
        };
        buttonInfo.push(info);
    });
    
    return {
        totalButtons: buttons.length,
        buttons: buttonInfo
    };
})()
"""

result = tab.call_method("Runtime.evaluate", expression=debug_buttons_expr, returnByValue=True)
button_info = result.get('result', {}).get('value', {})

print(f"\n🎯 BUTTON ANALYSIS:")
print(f"Total buttons found: {button_info.get('totalButtons', 0)}")

if 'buttons' in button_info:
    for btn in button_info['buttons']:
        print(f"\nButton {btn['index']}:")
        print(f"  Text: '{btn['text']}'")
        print(f"  Aria-label: '{btn['ariaLabel']}'")
        print(f"  Title: '{btn['title']}'")
        print(f"  Type: '{btn['type']}'")
        print(f"  Disabled: {btn['disabled']}")
        print(f"  Has Icon: {btn['hasIcon']}")
        print(f"  Class: '{btn['className']}'")
        print(f"  ID: '{btn['id']}'")
        print(f"  HTML: {btn['innerHTML'][:50]}...")

# Also check for form submission
form_info_expr = """
(() => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return 'No textarea found';
    
    const form = textarea.closest('form');
    if (form) {
        return {
            hasForm: true,
            formAction: form.action || '',
            formMethod: form.method || '',
            formId: form.id || '',
            formClass: form.className || ''
        };
    }
    
    return { hasForm: false };
})()
"""

result = tab.call_method("Runtime.evaluate", expression=form_info_expr, returnByValue=True)
form_info = result.get('result', {}).get('value', {})

print(f"\n📋 FORM ANALYSIS:")
print(f"Has form: {form_info.get('hasForm', False)}")
if form_info.get('hasForm'):
    print(f"Form action: '{form_info.get('formAction', '')}'")
    print(f"Form method: '{form_info.get('formMethod', '')}'")
    print(f"Form ID: '{form_info.get('formId', '')}'")
    print(f"Form class: '{form_info.get('formClass', '')}'")

# Check what happens when we press Enter
print(f"\n⌨️ TESTING ENTER KEY:")

enter_test_expr = """
(() => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return 'No textarea found';
    
    textarea.focus();
    
    // Try different Enter key approaches
    const results = [];
    
    // Method 1: KeyboardEvent
    const enterEvent = new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter',
        keyCode: 13,
        which: 13,
        bubbles: true,
        cancelable: true
    });
    
    const prevented = !textarea.dispatchEvent(enterEvent);
    results.push(`KeyboardEvent prevented: ${prevented}`);
    
    // Method 2: Form submission if in form
    const form = textarea.closest('form');
    if (form) {
        results.push('Found form - could try form.submit()');
    } else {
        results.push('No form found');
    }
    
    return results.join('; ');
})()
"""

result = tab.call_method("Runtime.evaluate", expression=enter_test_expr, returnByValue=True)
print(f"Enter test result: {result.get('result', {}).get('value', 'Unknown')}")

print("\n✅ Debug complete!")

# Stop and close
tab.stop()
browser.close_tab(tab)
