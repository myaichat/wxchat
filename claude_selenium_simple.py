#!/usr/bin/env python3
"""
Simple Claude alternative using Selenium (no Playwright, no CDP)
Direct replacement for: python '.\chat_handlers\claude_streaming_chat.py' 'how ry?'
"""

import sys
import time
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python claude_selenium_simple.py 'your question'")
        print("Example: python claude_selenium_simple.py 'how ry?'")
        return
    
    question = sys.argv[1]
    
    print("Claude Selenium Simple (No Playwright)")
    print("=" * 40)
    print(f"Question: {question}")
    print()
    
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.keys import Keys
    except ImportError:
        print("❌ Selenium not installed")
        print("Install with: pip install selenium")
        print("Also need ChromeDriver: https://chromedriver.chromium.org/")
        return
    
    # Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--headless")  # Uncomment for headless mode
    
    driver = None
    try:
        print("Starting Chrome...")
        driver = webdriver.Chrome(options=chrome_options)
        
        print("Navigating to Claude.ai...")
        driver.get("https://claude.ai")
        
        # Wait for page to load
        time.sleep(3)
        
        # Check if we need to login
        if "login" in driver.current_url.lower() or "sign" in driver.current_url.lower():
            print("❌ Please login to Claude.ai first")
            print("The browser will stay open - login manually and run the script again")
            input("Press Enter after logging in...")
            driver.refresh()
            time.sleep(3)
        
        print("Looking for input field...")
        
        # Try different selectors for the input field
        input_selectors = [
            'div[contenteditable="true"]',
            'textarea',
            '[data-testid="chat-input"]',
            '.ProseMirror',
            '[role="textbox"]',
            'div[role="textbox"]'
        ]
        
        input_element = None
        for selector in input_selectors:
            try:
                input_element = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                print(f"✅ Found input field with selector: {selector}")
                break
            except:
                continue
        
        if not input_element:
            print("❌ Could not find input field")
            print("Make sure you're on the Claude conversation page")
            return
        
        print("Typing question...")
        input_element.click()
        input_element.clear()
        
        # Type the question
        if input_element.tag_name == 'div':
            # For contenteditable div
            driver.execute_script("arguments[0].textContent = arguments[1];", input_element, question)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", input_element)
        else:
            # For textarea
            input_element.send_keys(question)
        
        time.sleep(1)
        
        print("Looking for send button...")
        
        # Try different selectors for send button
        send_selectors = [
            'button[aria-label*="Send"]',
            'button[data-testid="send-button"]',
            'button:has(svg)',
            '.send-button',
            'button[type="submit"]'
        ]
        
        send_button = None
        for selector in send_selectors:
            try:
                send_button = driver.find_element(By.CSS_SELECTOR, selector)
                if send_button.is_enabled():
                    print(f"✅ Found send button with selector: {selector}")
                    break
            except:
                continue
        
        # Fallback: look for any button with Send text or SVG
        if not send_button:
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if ("send" in btn.text.lower() or 
                        btn.find_elements(By.TAG_NAME, "svg") or
                        "arrow" in btn.get_attribute("class").lower()):
                        send_button = btn
                        print("✅ Found send button by text/svg")
                        break
            except:
                pass
        
        if not send_button:
            print("❌ Could not find send button")
            print("Trying Enter key instead...")
            input_element.send_keys(Keys.RETURN)
        else:
            print("Clicking send button...")
            send_button.click()
        
        print("Waiting for response...")
        
        # Wait for response
        response_text = ""
        max_wait = 30
        
        for i in range(max_wait):
            try:
                # Look for response messages
                message_selectors = [
                    '[data-testid="conversation-turn"]',
                    '.message',
                    '[role="article"]',
                    '.prose',
                    '.markdown'
                ]
                
                messages = []
                for selector in message_selectors:
                    try:
                        messages = driver.find_elements(By.CSS_SELECTOR, selector)
                        if messages:
                            break
                    except:
                        continue
                
                if messages:
                    # Get the last message (should be Claude's response)
                    last_message = messages[-1]
                    current_text = last_message.text.strip()
                    
                    # Check if it's different from our question and has content
                    if current_text and current_text != question and len(current_text) > 10:
                        # Check if still generating
                        is_generating = (
                            "▌" in current_text or
                            last_message.find_elements(By.CSS_SELECTOR, ".cursor") or
                            last_message.find_elements(By.CSS_SELECTOR, ".loading") or
                            driver.find_elements(By.CSS_SELECTOR, '[data-testid="stop-button"]')
                        )
                        
                        if not is_generating and current_text != response_text:
                            response_text = current_text
                            break
                        elif is_generating:
                            print(f"Claude is typing... ({len(current_text)} chars)")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Error waiting for response: {e}")
                time.sleep(1)
        
        if response_text:
            print()
            print("Claude Response:")
            print("-" * 40)
            print(response_text)
            print("-" * 40)
            print("✅ Success!")
        else:
            print("❌ No response received")
            print("Try:")
            print("1. Make sure you're logged in")
            print("2. Try asking a question manually first")
            print("3. Check if Claude is working normally")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure ChromeDriver is installed and in PATH")
        
    finally:
        if driver:
            print("Closing browser...")
            driver.quit()

if __name__ == "__main__":
    main()
