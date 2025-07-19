import pychrome
import time
import sys
import threading
import argparse
from queue import Queue

# Connect to the browser
browser = pychrome.Browser(url="http://localhost:9222")

# Find the specific tab by ID
tab_id = "A33755EA6ACA007184A661F801BCFDE7"
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

def get_response_text(tab, response_selector, index):
    """Get the current text of a response element"""
    try:
        response_expr = f"document.querySelectorAll('{response_selector}')[{index}].innerText"
        result = tab.call_method("Runtime.evaluate", expression=response_expr, returnByValue=True)
        
        if 'result' in result and 'value' in result['result']:
            return result['result']['value']
        return ""
    except:
        return ""

def print_streaming_response(text, is_complete=False):
    """Print streaming response with proper formatting"""
    if is_complete:
        print(f"\n✅ Complete Response:\n{text}\n")
    else:
        # Show incremental streaming with word count and length
        word_count = len(text.split())
        char_count = len(text)
        
        # Show first few lines of the response
        lines = text.split('\n')
        preview_lines = lines[:3]  # Show first 3 lines
        preview = '\n'.join(preview_lines)
        
        if len(lines) > 3:
            preview += f"\n... ({len(lines)-3} more lines)"
        
        print(f"\r🔄 Streaming: {word_count} words, {char_count} chars")
        print(f"Preview:\n{preview}")
        print("-" * 50)

def send_message_with_streaming(question, timeout=60):
    """Generator function that yields Gemini response chunks in real-time for use by handlers"""
    print(f"\n📤 Sending question to Gemini: {question}")
    print("🔄 Waiting for response...")
    
    try:
        # Selectors
        input_selector = 'rich-textarea > div > p'
        send_button_selector = 'div[class*="send-button-container"] > button'
        response_selector = 'message-content[class*="model-response-text"]'

        # Get current number of responses
        count_expr = f"document.querySelectorAll('{response_selector}').length"
        result = tab.call_method("Runtime.evaluate", expression=count_expr, returnByValue=True)
        
        # Check if the result has the expected structure
        if 'result' not in result or 'value' not in result['result']:
            raise ValueError(f"Failed to get response count. Result: {result}")
        
        num_responses = result['result']['value']

        # Set the input text
        input_expr = f"document.querySelector('{input_selector}').textContent = `{question.replace('`', '\\`')}`;"
        tab.call_method("Runtime.evaluate", expression=input_expr)

        # Small delay to simulate typing
        time.sleep(1)

        # Click send button
        click_expr = f"document.querySelector('{send_button_selector}').click();"
        tab.call_method("Runtime.evaluate", expression=click_expr)

        # Wait for new response to appear
        start_time = time.time()
        current_num = num_responses
        
        print("⏳ Waiting for response to start...")
        
        # Wait for response to start
        while time.time() - start_time < 30:  # 30 second timeout for response to start
            result = tab.call_method("Runtime.evaluate", expression=count_expr, returnByValue=True)
            if 'result' in result and 'value' in result['result']:
                current_num = result['result']['value']
                if current_num > num_responses:
                    break
            time.sleep(0.5)
        else:
            yield "❌ Timeout waiting for Gemini response to appear."
            return

        # Get the response index
        response_index = current_num - 1
        
        print("🚀 Gemini response started! Streaming...")
        
        # Stream the response by yielding chunks
        previous_text = ""
        previous_length = 0
        last_change_time = time.time()
        stable_count = 0
        update_count = 0
        
        while time.time() - start_time < timeout:
            current_text = get_response_text(tab, response_selector, response_index)
            current_length = len(current_text)
            
            # Only yield updates when text actually changes
            if current_text != previous_text and current_length > previous_length:
                update_count += 1
                
                # Yield the new content that was added
                new_content = current_text[previous_length:] if previous_length > 0 else current_text
                
                if new_content:
                    print(f"🔄 Yielding chunk #{update_count} - {len(new_content)} chars")
                    yield new_content
                
                previous_text = current_text
                previous_length = current_length
                last_change_time = time.time()
                stable_count = 0
            else:
                # Text hasn't changed
                stable_count += 1
                
                # If text has been stable for 3 seconds, consider it complete
                if time.time() - last_change_time > 3 and len(current_text) > 0:
                    print("✅ Gemini response appears complete (stable for 3 seconds)")
                    break
                    
                # If we've had many stable checks and have some content, likely done
                if stable_count > 6 and len(current_text) > 50:
                    print("✅ Gemini response appears complete (stable checks)")
                    break
            
            time.sleep(0.5)
        
        print("🏁 Gemini streaming completed")
            
    except Exception as e:
        yield f"❌ Gemini streaming error: {str(e)}"

def send_message_non_streaming(question, timeout=60):
    """Non-streaming version that returns the full response (for backward compatibility)"""
    print(f"\n📤 Sending question: {question}")
    print("🔄 Waiting for response...")
    
    try:
        # Collect all chunks from the streaming version
        full_response = ""
        for chunk in send_message_with_streaming(question, timeout):
            if chunk and not chunk.startswith("❌"):
                full_response += chunk
            elif chunk.startswith("❌"):
                print(f"\n❌ Error: {chunk}")
                return ""
        
        if full_response:
            print_streaming_response(full_response, is_complete=True)
            return full_response
        else:
            print("\n❌ No response received")
            return ""
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return ""

def display_welcome():
    """Display welcome message and instructions"""
    print("=" * 60)
    print("🤖 Gem PyChrome Streaming Chat Interface")
    print("=" * 60)
    print("✨ Features:")
    print("  • Real-time streaming responses")
    print("  • Live progress indicators")
    print("  • Console-based interface")
    print("  • Type 'quit' to exit")
    print("=" * 60)
    print()

def display_stats(question_count, total_time):
    """Display session statistics"""
    print("=" * 60)
    print("📊 Session Statistics:")
    print(f"  • Questions asked: {question_count}")
    print(f"  • Total time: {total_time:.1f} seconds")
    print(f"  • Average per question: {total_time/question_count:.1f} seconds" if question_count > 0 else "")
    print("=" * 60)

# Main execution
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Gem PyChrome Streaming Chat Interface')
    parser.add_argument('question', nargs='?', help='Question to ask (if not provided, enters interactive mode)')
    parser.add_argument('--timeout', type=int, default=60, help='Timeout in seconds for response (default: 60)')
    
    args = parser.parse_args()
    
    question_count = 0
    start_session_time = time.time()
    
    try:
        assert args.question
        # Single question mode
        print("🤖 Gem PyChrome Streaming Chat Interface - Single Question Mode")
        print("=" * 60)
        
        question_start_time = time.time()
        answer = send_message_non_streaming(args.question, timeout=args.timeout)
        question_end_time = time.time()
        
        if answer and not answer.startswith("Error:"):
            question_count = 1
            print(f"⏱️  Response time: {question_end_time - question_start_time:.1f} seconds")
        else:
            print("❌ Failed to get response")
        
    
    finally:
        # Cleanup and show stats
        total_session_time = time.time() - start_session_time
        
        print("\n🔄 Cleaning up...")
        try:
            # More graceful cleanup - just stop the tab, don't close it
            tab.stop()
            print("✅ Browser connection stopped successfully")
        except Exception as e:
            print(f"⚠️  Error during cleanup: {str(e)}")
        
        if question_count > 0:
            display_stats(question_count, total_session_time)
        
        print("👋 Thanks for using Gem PyChrome Streaming Chat!")
        print("=" * 60)
