#!/usr/bin/env python3
"""
Simple test script for claude_streaming_chat_streamlit_fix.py with better error handling

Usage:
    python test_claude_simple.py "Your question here"
"""

import sys
import asyncio
import requests
from chat_handlers.claude_streaming_chat_streamlit_fix import ChromeDebugChatBot

async def test_connection_only():
    """Test just the connection without sending messages"""
    print("🔍 Testing Chrome debug connection...")
    
    # First check if Chrome debug is accessible
    try:
        response = requests.get("http://localhost:9222/json", timeout=5)
        if response.status_code == 200:
            tabs = response.json()
            print(f"✅ Found {len(tabs)} tabs via HTTP")
            
            # Find Claude.ai tab
            claude_tab = None
            for tab in tabs:
                if "claude.ai" in tab.get("url", "").lower():
                    claude_tab = tab
                    print(f"✅ Found Claude.ai tab: {tab.get('title', 'Unknown')}")
                    print(f"   URL: {tab.get('url', 'Unknown')}")
                    break
            
            if not claude_tab:
                print("❌ No Claude.ai tab found")
                return False
        else:
            print(f"❌ Chrome debug not accessible: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Chrome debug: {e}")
        return False
    
    # Test Playwright connection
    bot = ChromeDebugChatBot(debug_port=9222)
    try:
        print("🔄 Testing Playwright connection...")
        success = await bot.connect_to_existing_tab()
        if success:
            print("✅ Playwright connection successful!")
            
            # Test page access
            if bot.page:
                url = bot.page.url
                title = await bot.page.title()
                print(f"✅ Page accessible: {title}")
                print(f"   URL: {url}")
                
                # Test basic page interaction
                try:
                    content_sample = await bot.page.evaluate("document.body.innerText.substring(0, 200)")
                    print(f"✅ Page content accessible (first 200 chars): {content_sample[:100]}...")
                    
                    # Look for input elements
                    input_elements = await bot.page.query_selector_all('input, textarea, [contenteditable]')
                    print(f"✅ Found {len(input_elements)} input elements")
                    
                    for i, elem in enumerate(input_elements[:3]):  # Show first 3
                        tag = await elem.evaluate('el => el.tagName')
                        attrs = await elem.evaluate('el => ({placeholder: el.placeholder, type: el.type, class: el.className})')
                        print(f"   Element {i+1}: {tag} - {attrs}")
                    
                except Exception as page_error:
                    print(f"❌ Page interaction failed: {page_error}")
                    return False
            else:
                print("❌ No page object available")
                return False
        else:
            print("❌ Playwright connection failed")
            return False
    except Exception as e:
        print(f"❌ Playwright error: {e}")
        return False
    finally:
        await bot.close()
    
    return True

async def test_simple_message(question):
    """Test sending a simple message with timeout"""
    print(f"\n🚀 Testing message sending: '{question}'")
    
    bot = ChromeDebugChatBot(debug_port=9222)
    try:
        if await bot.connect_to_existing_tab():
            print("✅ Connected, attempting to send message...")
            
            # Set a shorter timeout for testing
            response_chunks = []
            timeout_seconds = 10
            
            try:
                # Use asyncio.wait_for to add timeout
                async def collect_response():
                    async for chunk in bot.send_message_with_streaming(question):
                        if chunk.startswith("Error:"):
                            print(f"❌ Streaming error: {chunk}")
                            return None
                        response_chunks.append(chunk)
                        print(f"📝 Received chunk: {chunk[:50]}...")
                        if len(''.join(response_chunks)) > 100:  # Stop after getting some content
                            break
                    return ''.join(response_chunks)
                
                response = await asyncio.wait_for(collect_response(), timeout=timeout_seconds)
                
                if response:
                    print(f"✅ Got response ({len(response)} chars): {response[:200]}...")
                    return response
                else:
                    print("❌ No response received")
                    return None
                    
            except asyncio.TimeoutError:
                print(f"⏰ Timeout after {timeout_seconds} seconds")
                if response_chunks:
                    partial_response = ''.join(response_chunks)
                    print(f"📝 Partial response received: {partial_response}")
                    return partial_response
                return None
        else:
            print("❌ Failed to connect")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        await bot.close()

async def main():
    """Main test function"""
    if len(sys.argv) < 2:
        print("Usage: python test_claude_simple.py \"Your question here\"")
        sys.exit(1)
    
    question = sys.argv[1]
    
    print("=" * 60)
    print("🧪 Claude Streamlit Fix - Simple Test")
    print("=" * 60)
    
    # Test 1: Connection only
    connection_ok = await test_connection_only()
    
    if not connection_ok:
        print("\n❌ Connection test failed. Please check:")
        print("1. Chrome is running with debug mode")
        print("2. Claude.ai is open and logged in")
        print("3. Run: powershell -ExecutionPolicy Bypass -File start_chrome_debug.ps1")
        sys.exit(1)
    
    # Test 2: Simple message
    response = await test_simple_message(question)
    
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS")
    print("=" * 60)
    
    if response:
        print("✅ SUCCESS: Message sent and response received")
        print(f"📝 Final response: {response}")
    else:
        print("❌ FAILED: No response received")
        print("💡 This might be due to:")
        print("   - Page not ready for input")
        print("   - Input selectors not matching")
        print("   - Claude taking too long to respond")
    
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(0)
