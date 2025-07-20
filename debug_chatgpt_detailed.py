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

def get_send_button_info():
    print("=== Detailed Send Button Analysis ===")
    
    # Look for buttons with SVG (likely send buttons)
    try:
        result = tab.call_method("Runtime.evaluate", 
            expression="""
            Array.from(document.querySelectorAll('button:has(svg)')).map((btn, index) => ({
                index: index,
                outerHTML: btn.outerHTML.substring(0, 200),
                disabled: btn.disabled,
                ariaLabel: btn.getAttribute('aria-label'),
                dataTestId: btn.getAttribute('data-testid'),
                className: btn.className,
                parentClassName: btn.parentElement ? btn.parentElement.className : 'no parent'
            }))
            """, 
            returnByValue=True)
        buttons = result.get('result', {}).get('value', [])
        print(f"Buttons with SVG found: {len(buttons)}")
        for btn in buttons:
            print(f"Button {btn['index']}:")
            print(f"  Disabled: {btn['disabled']}")
            print(f"  Class: {btn['className']}")
            print(f"  Parent Class: {btn['parentClassName']}")
            print(f"  HTML: {btn['outerHTML']}")
            print()
    except Exception as e:
        print(f"Send button analysis error: {e}")

def get_input_info():
    print("=== Detailed Input Analysis ===")
    
    # Check both prompt-textarea and the fallback textarea
    selectors = ['#prompt-textarea', 'textarea._fallbackTextarea_276o5_2']
    
    for selector in selectors:
        try:
            result = tab.call_method("Runtime.evaluate", 
                expression=f"""
                const el = document.querySelector('{selector}');
                if (el) {{
                    {{
                        exists: true,
                        value: el.value,
                        placeholder: el.placeholder,
                        disabled: el.disabled,
                        readOnly: el.readOnly,
                        className: el.className,
                        id: el.id
                    }}
                }} else {{
                    {{ exists: false }}
                }}
                """, 
                returnByValue=True)
            info = result.get('result', {}).get('value', {})
            print(f"{selector}: {info}")
        except Exception as e:
            print(f"{selector}: ERROR - {e}")

def test_message_containers():
    print("=== Message Container Analysis ===")
    
    # Look for common message container patterns
    selectors = [
        'div[data-testid*="conversation"]',
        'div[role="main"]',
        'main',
        'div[data-testid*="message"]',
        'article',
        '.prose',
        'div[class*="message"]',
        'div[class*="conversation"]'
    ]
    
    for selector in selectors:
        try:
            result = tab.call_method("Runtime.evaluate", 
                expression=f"document.querySelectorAll('{selector}').length", 
                returnByValue=True)
            count = result.get('result', {}).get('value', 'ERROR')
            print(f"{selector}: {count} elements")
        except Exception as e:
            print(f"{selector}: ERROR - {e}")

# Run detailed analysis
get_input_info()
get_send_button_info()
test_message_containers()

# Stop the tab
tab.stop()
print("\nDetailed debug complete!")
