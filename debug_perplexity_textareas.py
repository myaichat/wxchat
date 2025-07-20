import pychrome
import time
import requests
import json

def find_perplexity_tab():
    """Find an existing Perplexity tab"""
    try:
        response = requests.get("http://localhost:9222/json")
        tab_list = response.json()
        print(f"🔍 Found {len(tab_list)} tabs")
        
        # Look for a real Perplexity tab
        for tab_info in tab_list:
            url = tab_info.get('url', '')
            title = tab_info.get('title', '')
            
            if ('perplexity.ai' in url.lower() and 
                'stripe.network' not in url.lower() and
                'service_worker' not in url.lower() and
                'iframe' not in url.lower() and
                tab_info.get('type') == 'page'):
                
                print(f"📱 Found Perplexity tab: {title} - {url}")
                return tab_info
        
        print("❌ No suitable Perplexity tab found")
        return None
        
    except Exception as e:
        print(f"❌ Error finding tabs: {e}")
        return None

# Find existing Perplexity tab
tab_info = find_perplexity_tab()
if not tab_info:
    exit(1)

# Connect to browser and get the tab
browser = pychrome.Browser(url="http://localhost:9222")
tabs = browser.list_tab()
tab = None
for t in tabs:
    if t.id == tab_info['id']:
        tab = t
        break

if not tab:
    print("❌ Could not connect to the Perplexity tab")
    exit(1)

# Start the tab
tab.start()

# Enable necessary domains
tab.call_method("Runtime.enable")

print("🔍 Debugging textarea elements on Perplexity page...")

# Check for all textareas
js_code = """
(function() {
    const results = {
        allTextareas: [],
        inputElements: [],
        editableElements: [],
        possibleChatInputs: []
    };
    
    // Find all textarea elements
    const textareas = document.querySelectorAll('textarea');
    console.log('Found textareas:', textareas.length);
    
    textareas.forEach((textarea, index) => {
        results.allTextareas.push({
            index: index,
            id: textarea.id || 'no-id',
            className: textarea.className || 'no-class',
            placeholder: textarea.placeholder || 'no-placeholder',
            name: textarea.name || 'no-name',
            visible: textarea.offsetParent !== null,
            disabled: textarea.disabled,
            readonly: textarea.readOnly,
            value: textarea.value.substring(0, 50) + (textarea.value.length > 50 ? '...' : ''),
            outerHTML: textarea.outerHTML.substring(0, 200) + (textarea.outerHTML.length > 200 ? '...' : '')
        });
    });
    
    // Find all input elements that might be text inputs
    const inputs = document.querySelectorAll('input[type="text"], input:not([type]), input[type="search"]');
    inputs.forEach((input, index) => {
        results.inputElements.push({
            index: index,
            type: input.type,
            id: input.id || 'no-id',
            className: input.className || 'no-class',
            placeholder: input.placeholder || 'no-placeholder',
            name: input.name || 'no-name',
            visible: input.offsetParent !== null,
            disabled: input.disabled,
            readonly: input.readOnly,
            value: input.value.substring(0, 50) + (input.value.length > 50 ? '...' : ''),
            outerHTML: input.outerHTML.substring(0, 200) + (input.outerHTML.length > 200 ? '...' : '')
        });
    });
    
    // Find contenteditable elements
    const editables = document.querySelectorAll('[contenteditable="true"], [contenteditable=""]');
    editables.forEach((editable, index) => {
        results.editableElements.push({
            index: index,
            tagName: editable.tagName,
            id: editable.id || 'no-id',
            className: editable.className || 'no-class',
            visible: editable.offsetParent !== null,
            textContent: editable.textContent.substring(0, 50) + (editable.textContent.length > 50 ? '...' : ''),
            outerHTML: editable.outerHTML.substring(0, 200) + (editable.outerHTML.length > 200 ? '...' : '')
        });
    });
    
    // Look for elements that might be chat inputs based on common patterns
    const possibleSelectors = [
        'textarea[placeholder*="Ask"]',
        'textarea[placeholder*="ask"]',
        'textarea[placeholder*="question"]',
        'textarea[placeholder*="search"]',
        'input[placeholder*="Ask"]',
        'input[placeholder*="ask"]',
        'input[placeholder*="question"]',
        'input[placeholder*="search"]',
        '[contenteditable][placeholder*="Ask"]',
        '[contenteditable][placeholder*="ask"]',
        '[role="textbox"]',
        '[aria-label*="Ask"]',
        '[aria-label*="ask"]',
        '[aria-label*="input"]',
        '[aria-label*="search"]'
    ];
    
    possibleSelectors.forEach(selector => {
        try {
            const elements = document.querySelectorAll(selector);
            elements.forEach((element, index) => {
                results.possibleChatInputs.push({
                    selector: selector,
                    index: index,
                    tagName: element.tagName,
                    id: element.id || 'no-id',
                    className: element.className || 'no-class',
                    placeholder: element.placeholder || element.getAttribute('aria-label') || 'no-placeholder',
                    visible: element.offsetParent !== null,
                    outerHTML: element.outerHTML.substring(0, 200) + (element.outerHTML.length > 200 ? '...' : '')
                });
            });
        } catch (e) {
            console.log('Error with selector:', selector, e);
        }
    });
    
    return results;
})();
"""

try:
    result = tab.call_method("Runtime.evaluate", 
                            expression=js_code, 
                            returnByValue=True)
    
    data = result.get('result', {}).get('value', {})
    
    print("\n" + "="*60)
    print("TEXTAREA ANALYSIS RESULTS")
    print("="*60)
    
    print(f"\n📝 ALL TEXTAREAS ({len(data.get('allTextareas', []))}):")
    for textarea in data.get('allTextareas', []):
        print(f"  [{textarea['index']}] ID: {textarea['id']}")
        print(f"      Class: {textarea['className']}")
        print(f"      Placeholder: {textarea['placeholder']}")
        print(f"      Visible: {textarea['visible']}")
        print(f"      Disabled: {textarea['disabled']}")
        print(f"      Value: '{textarea['value']}'")
        print(f"      HTML: {textarea['outerHTML']}")
        print()
    
    print(f"\n🔤 INPUT ELEMENTS ({len(data.get('inputElements', []))}):")
    for inp in data.get('inputElements', []):
        print(f"  [{inp['index']}] Type: {inp['type']}, ID: {inp['id']}")
        print(f"      Class: {inp['className']}")
        print(f"      Placeholder: {inp['placeholder']}")
        print(f"      Visible: {inp['visible']}")
        print(f"      HTML: {inp['outerHTML']}")
        print()
    
    print(f"\n✏️  CONTENTEDITABLE ELEMENTS ({len(data.get('editableElements', []))}):")
    for edit in data.get('editableElements', []):
        print(f"  [{edit['index']}] Tag: {edit['tagName']}, ID: {edit['id']}")
        print(f"      Class: {edit['className']}")
        print(f"      Visible: {edit['visible']}")
        print(f"      Content: '{edit['textContent']}'")
        print(f"      HTML: {edit['outerHTML']}")
        print()
    
    print(f"\n🎯 POSSIBLE CHAT INPUTS ({len(data.get('possibleChatInputs', []))}):")
    for chat in data.get('possibleChatInputs', []):
        print(f"  Selector: {chat['selector']}")
        print(f"  [{chat['index']}] Tag: {chat['tagName']}, ID: {chat['id']}")
        print(f"      Class: {chat['className']}")
        print(f"      Placeholder: {chat['placeholder']}")
        print(f"      Visible: {chat['visible']}")
        print(f"      HTML: {chat['outerHTML']}")
        print()
    
    # Test the current selectors from the original script
    print("\n🧪 TESTING ORIGINAL SELECTORS:")
    test_js = """
    (function() {
        const results = {};
        
        // Test original selector 1
        const textareas = document.querySelectorAll('textarea');
        results.allTextareasCount = textareas.length;
        results.lastTextarea = textareas.length > 0 ? {
            exists: true,
            visible: textareas[textareas.length - 1].offsetParent !== null,
            placeholder: textareas[textareas.length - 1].placeholder || 'no-placeholder'
        } : { exists: false };
        
        // Test original selector 2
        const askTextarea = document.querySelector('textarea[placeholder*="Ask"]');
        results.askTextarea = askTextarea ? {
            exists: true,
            visible: askTextarea.offsetParent !== null,
            placeholder: askTextarea.placeholder || 'no-placeholder'
        } : { exists: false };
        
        // Final result of original logic
        const finalTextarea = textareas[textareas.length - 1] || askTextarea;
        results.finalSelection = finalTextarea ? {
            exists: true,
            visible: finalTextarea.offsetParent !== null,
            tagName: finalTextarea.tagName,
            placeholder: finalTextarea.placeholder || 'no-placeholder'
        } : { exists: false };
        
        return results;
    })();
    """
    
    test_result = tab.call_method("Runtime.evaluate", 
                                 expression=test_js, 
                                 returnByValue=True)
    
    test_data = test_result.get('result', {}).get('value', {})
    
    print(f"  All textareas count: {test_data.get('allTextareasCount', 0)}")
    print(f"  Last textarea: {test_data.get('lastTextarea', {})}")
    print(f"  Ask textarea: {test_data.get('askTextarea', {})}")
    print(f"  Final selection: {test_data.get('finalSelection', {})}")
    
except Exception as e:
    print(f"❌ Error during analysis: {e}")

# Stop and close the tab
tab.stop()
browser.close_tab(tab)
