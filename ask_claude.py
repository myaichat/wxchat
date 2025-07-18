#!/usr/bin/env python3
"""
ask_claude.py - Command line interface for asking questions to Claude.ai
Usage: python ask_claude.py "Your question here"
"""

import sys
import asyncio
from pup_test_claude import ChromeDebugChatBot

async def ask_claude(question):
    """Ask Claude a question and return the response"""
    bot = ChromeDebugChatBot()
    
    try:
        print(f"🤖 Connecting to Claude.ai...")
        
        # Connect to existing Chrome tab
        if await bot.connect_to_existing_tab():
            print(f"✅ Connected successfully!")
            print(f"📝 Asking: {question}")
            print(f"⏳ Waiting for response...")
            
            # Send question and get response
            response = await bot.send_message_and_get_response(question)
            
            if response:
                print(f"\n🎯 Claude's Response:")
                print("=" * 50)
                print(response)
                print("=" * 50)
                return response
            else:
                print("❌ Failed to get response from Claude")
                return None
                
        else:
            print("❌ Failed to connect to Chrome debug session")
            print("💡 Make sure Chrome is running with debug enabled:")
            print("   chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
        
    finally:
        print("🧹 Cleaning up...")
        await bot.close()

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
    
    # Run the async function
    try:
        response = asyncio.run(ask_claude(question))
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
