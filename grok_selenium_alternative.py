"""
Alternative Grok chat automation using Selenium WebDriver.
This approach might be more reliable than CDP for Grok.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_chrome_driver(existing_session=True):
    """Setup Chrome driver to connect to existing session or create new one."""
    chrome_options = Options()
    
    if existing_session:
        # Connect to existing Chrome instance with debugging enabled
        chrome_options.add_experimental_option("debuggerAddress", "localhost:9222")
    else:
        # Create new Chrome instance
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Failed to setup Chrome driver: {e}")
        return None

def find_grok_tab(driver):
    """Find and switch to Grok tab."""
    try:
        # Get all window handles
        handles = driver.window_handles
        
        for handle in handles:
            driver.switch_to.window(handle)
            current_url = driver.current_url
            if "grok.com" in current_url:
                print(f"Found Grok tab: {current_url}")
                return True
        
        print("No Grok tab found")
        return False
    except Exception as e:
        print(f"Error finding Grok tab: {e}")
        return False

def find_input_element(driver):
    """Find the input element on Grok page using multiple strategies."""
    
    # List of possible selectors for Grok input
    selectors = [
        "textarea[placeholder*='Ask']",
        "textarea[placeholder*='Type']",
        "textarea[placeholder*='Message']",
        "textarea[data-testid*='prompt']",
        "textarea[data-testid*='input']",
        "textarea",
        "input[type='text']",
        "[contenteditable='true']",
        "[data-testid*='textarea']",
        "[data-testid*='input']"
    ]
    
    wait = WebDriverWait(driver, 10)
    
    for selector in selectors:
        try:
            print(f"Trying selector: {selector}")
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            
            # Check if element is visible and interactable
            if element.is_displayed() and element.is_enabled():
                print(f"✓ Found input element with selector: {selector}")
                return element
        except TimeoutException:
            continue
        except Exception as e:
            print(f"Error with selector {selector}: {e}")
            continue
    
    print("No suitable input element found")
    return None

def send_message_to_grok(driver, message):
    """Send a message to Grok."""
    try:
        # Find input element
        input_element = find_input_element(driver)
        if not input_element:
            return False
        
        # Clear any existing text and type message
        input_element.clear()
        input_element.send_keys(message)
        
        # Try to send the message
        # Method 1: Press Enter
        try:
            input_element.send_keys(Keys.RETURN)
            print("Sent message using Enter key")
            return True
        except:
            pass
        
        # Method 2: Look for send button
        send_button_selectors = [
            "button[aria-label*='Send']",
            "button[data-testid*='send']",
            "button:contains('Send')",
            "[role='button'][aria-label*='Send']"
        ]
        
        for selector in send_button_selectors:
            try:
                send_button = driver.find_element(By.CSS_SELECTOR, selector)
                if send_button.is_displayed() and send_button.is_enabled():
                    send_button.click()
                    print(f"Sent message using button: {selector}")
                    return True
            except:
                continue
        
        # Method 3: Try Ctrl+Enter
        try:
            input_element.send_keys(Keys.CONTROL + Keys.RETURN)
            print("Sent message using Ctrl+Enter")
            return True
        except:
            pass
        
        print("Could not find a way to send the message")
        return False
        
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def get_grok_response(driver, timeout=30):
    """Wait for and retrieve Grok's response."""
    try:
        # Wait a moment for the response to start appearing
        time.sleep(2)
        
        # Look for response elements
        response_selectors = [
            "[data-testid*='conversation']",
            "[data-testid*='message']",
            "[data-testid*='response']",
            ".message",
            ".response",
            "[role='log'] > div",
            "[role='main'] > div"
        ]
        
        wait = WebDriverWait(driver, timeout)
        
        for selector in response_selectors:
            try:
                # Wait for elements to appear
                elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                
                if len(elements) >= 2:  # Should have at least user message and bot response
                    # Get the last element (should be Grok's response)
                    last_element = elements[-1]
                    response_text = last_element.text
                    
                    if response_text and len(response_text.strip()) > 10:
                        print(f"Found response using selector: {selector}")
                        return response_text
                        
            except TimeoutException:
                continue
            except Exception as e:
                print(f"Error with response selector {selector}: {e}")
                continue
        
        print("No response found")
        return None
        
    except Exception as e:
        print(f"Error getting response: {e}")
        return None

def ask_grok_selenium(question):
    """Main function to ask Grok a question using Selenium."""
    driver = None
    try:
        # Setup driver
        driver = setup_chrome_driver(existing_session=True)
        if not driver:
            print("Failed to setup Chrome driver")
            return None
        
        # Find Grok tab
        if not find_grok_tab(driver):
            print("Could not find Grok tab")
            return None
        
        print(f"Current page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Send message
        if not send_message_to_grok(driver, question):
            print("Failed to send message")
            return None
        
        # Get response
        response = get_grok_response(driver)
        return response
        
    except Exception as e:
        print(f"Error in ask_grok_selenium: {e}")
        return None
    finally:
        if driver:
            # Don't close the driver since we're using existing session
            pass

def main():
    """Test the Selenium approach."""
    question = "Hello! Please respond with 'Selenium test successful' to confirm this works."
    
    print(f"Testing Selenium approach with Grok...")
    print(f"Question: {question}")
    
    response = ask_grok_selenium(question)
    
    if response:
        print(f"\n✓ SUCCESS! Grok responded:")
        print(f"Response: {response}")
    else:
        print("\n✗ FAILED: No response received")

if __name__ == "__main__":
    main()
