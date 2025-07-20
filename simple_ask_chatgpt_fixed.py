import asyncio
import sys
import os

# Add the current directory to Python path to import chat_handlers
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chat_handlers.chatgpt_streaming_chat import send_message_with_streaming

async def ask_chatgpt_simple(question):
    """Simple function to ask ChatGPT and get streaming response"""
    print(f"Asking ChatGPT: {question}")
    print("=" * 50)
    
    full_response = ""
    previous_content = ""
    
    try:
        async for response in send_message_with_streaming(question, timeout=60):
            status = response['status']
            content = response['content']
            
            if status == "started":
                print("🚀 ChatGPT started responding...")
                print("-" * 50)
            elif status == "streaming":
                # Show only the new chunk (difference from previous content)
                if len(content) > len(previous_content):
                    new_chunk = content[len(previous_content):]
                    try:
                        print(new_chunk, end='', flush=True)
                    except UnicodeEncodeError:
                        # Handle emoji and special characters
                        print(new_chunk.encode('utf-8', errors='replace').decode('utf-8'), end='', flush=True)
                    previous_content = content
            elif status == "complete":
                # Show any final chunk
                if len(content) > len(previous_content):
                    new_chunk = content[len(previous_content):]
                    try:
                        print(new_chunk, end='', flush=True)
                    except UnicodeEncodeError:
                        # Handle emoji and special characters
                        print(new_chunk.encode('utf-8', errors='replace').decode('utf-8'), end='', flush=True)
                
                full_response = content
                print(f"\n{'-' * 50}")
                print(f"✅ Response complete ({len(content)} chars)")
                break
            elif status in ["timeout", "error"]:
                print(f"\n❌ {status}: {content}")
                break
                
    except Exception as e:
        print(f"Error: {e}")
        return None
    
    return full_response

async def main():
    """Main interactive loop"""
    print("Simple ChatGPT Ask Tool (Using WebSocket Streaming)")
    print("=" * 55)
    print("This uses the working streaming chat implementation.")
    print("Make sure Chrome is running with debug port 9222 and ChatGPT is open.")
    print()
    
    while True:
        try:
            question = input("Enter your question (or 'quit' to exit): ")
            if question.lower() in ['quit', 'exit', 'q']:
                break
                
            if not question.strip():
                print("Please enter a question.")
                continue
                
            print()
            response = await ask_chatgpt_simple(question.strip())
            
            if response:
                print("\n" + "=" * 50)
                print("Full Response:")
                print("=" * 50)
                print(response)
                print("=" * 50 + "\n")
            else:
                print("No response received or error occurred.\n")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
