#!/usr/bin/env python3
"""
ask_claude.py - Command line interface for asking questions to Claude.ai
Usage: python ask_claude.py "Your question here"
"""

import sys
import asyncio
from pup_streaming_claude import ChromeDebugChatBot

async def main_async_with_question(question):
    """Modified version of main_async from pup_streaming_claude.py that accepts a question parameter"""
    bot = ChromeDebugChatBot()
    
    try:
        bot.log("=== Starting Claude Chat Bot with Streaming ===")
        
        # Connect to existing Chrome tab
        if await bot.connect_to_existing_tab():
            
            # Send the question and stream the response
            bot.log(f"Sending question: {question}")
            
            print("\n=== STREAMING RESPONSE ===")
            full_response = ""
            
            async for chunk in bot.send_message_and_stream_response(question):
                if not chunk.startswith("Error:"):
                    print(chunk, end='', flush=True)  # Print each chunk as it arrives
                    full_response += chunk
                else:
                    print(f"\nError: {chunk}")
                    break
            
            print("\n=== END OF STREAMING ===")
            
            if full_response:
                bot.log(f"Complete response received ({len(full_response)} characters)")
                return full_response
            else:
                bot.log("No response received")
                return None
                
        else:
            bot.log("Failed to connect to Chrome debug session")
            bot.log("💡 Make sure Chrome is running with debug enabled:")
            bot.log("   chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug")
            return None
            
    except Exception as e:
        bot.log(f"Error in main: {e}")
        return None
        
    finally:
        bot.log("Cleaning up resources...")
        await bot.close()
        bot.log("=== Claude Chat Bot Finished ===")

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage: python ask_claude.py \"Your question here\"")
        print("Example: python ask_claude.py \"What is the weather like today?\"")
        sys.exit(1)
    
    # Join all arguments after the script name as the question
    question = " ".join(sys.argv[1:])
    
    if not question.strip():
        print("❌ Error: Question cannot be empty")
        sys.exit(1)
    
    print(f"🚀 Starting Claude Chat Bot...")
    
    # Run the async function using the main_async pattern
    try:
        response = asyncio.run(main_async_with_question(question))
        if response:
            print(f"\n✅ Successfully got response from Claude!")
        else:
            print(f"\n❌ Failed to get response from Claude")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
