#!/usr/bin/env python
"""
simple_ask_claude.py  –  directly call ChromeDebugChatBot and stream the reply

Usage:
    python simple_ask_claude.py "Your prompt here"
"""

import asyncio
import json
import sys
import io
import os
from datetime import datetime

# Import the ChromeDebugChatBot class
from chat_handlers.claude_streaming_chat import ChromeDebugChatBot

# Fix Windows console encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

TIMEOUT_SEC = 60


def safe_print(text, end="\n", flush=False):
    """Print text with Unicode error handling for Windows console"""
    try:
        print(text, end=end, flush=flush)
    except UnicodeEncodeError:
        # Handle all Unicode characters properly by encoding with error replacement
        safe_text = text.encode('utf-8', errors='replace').decode('utf-8')
        try:
            print(safe_text, end=end, flush=flush)
        except UnicodeEncodeError:
            # Fallback: replace common problematic characters
            fallback_text = safe_text.replace("🚀", "[ROCKET]").replace("✅", "[CHECK]").replace("❌", "[X]")
            # Replace any remaining problematic characters
            fallback_text = fallback_text.encode('ascii', errors='replace').decode('ascii')
            print(fallback_text, end=end, flush=flush)


def save_chat_log(question: str, answer: str, model: str = "claude-3.5-sonnet"):
    """Save individual chat session to timestamped JSON file"""
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Create timestamp for filename and log entry
    timestamp = datetime.now()
    filename_timestamp = timestamp.strftime("%Y%m%d_%H%M%S")
    iso_timestamp = timestamp.isoformat()
    
    # Create log entry
    log_entry = {
        "timestamp": iso_timestamp,
        "question": question,
        "answer": answer,
        "model": model
    }
    
    # Save to individual timestamped file
    filename = f"logs/simple_ask_claude_chat_session_{filename_timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)
    
    safe_print(f"Chat session logged to: {filename}")
    return filename


async def stream_chat(prompt: str):
    """Stream chat using ChromeDebugChatBot - simplified version with timeout"""
    bot = ChromeDebugChatBot()
    complete_answer = ""
    
    try:
        safe_print("🚀  Connecting to Chrome debug session...")
        
        # Connect to existing Chrome tab
        if await bot.connect_to_existing_tab():
            safe_print("✅  Connected successfully")
            safe_print(f"📝  Sending question: {prompt}")
            safe_print("\n=== STREAMING RESPONSE ===")
            
            # Use asyncio.wait_for to add a timeout to the streaming
            try:
                async def stream_with_timeout():
                    async for chunk in bot.send_message_with_streaming(prompt):
                        if not chunk.startswith("Error:"):
                            safe_print(chunk, end='', flush=True)
                            complete_answer_ref[0] += chunk
                        else:
                            safe_print(f"\n❌  Error: {chunk}")
                            complete_answer_ref[0] = f"Error: {chunk}"
                            break
                
                # Use a list to make complete_answer mutable in the nested function
                complete_answer_ref = [complete_answer]
                
                # Set a reasonable timeout (30 seconds)
                await asyncio.wait_for(stream_with_timeout(), timeout=30.0)
                complete_answer = complete_answer_ref[0]
                
            except asyncio.TimeoutError:
                safe_print(f"\n⏰  Response timeout after 30 seconds")
                complete_answer = complete_answer_ref[0] if complete_answer_ref[0] else "Timeout: Response took too long"
            
            safe_print("\n=== END OF STREAMING ===")
            safe_print("\n✅  Complete")
            
            # Save the complete conversation to log
            try:
                save_chat_log(prompt, complete_answer)
            except Exception as e:
                safe_print(f"Error saving chat log: {e}")
                
        else:
            error_msg = "Failed to connect to Chrome debug session. Make sure Chrome is running with debug enabled."
            safe_print(f"❌  {error_msg}")
            complete_answer = f"Error: {error_msg}"
            try:
                save_chat_log(prompt, complete_answer)
            except Exception as e:
                safe_print(f"Error saving chat log: {e}")
                
    except Exception as e:
        safe_print(f"\n❌  Unexpected error: {e}")
        complete_answer = f"Error: {e}"
        try:
            save_chat_log(prompt, complete_answer)
        except Exception as log_e:
            safe_print(f"Error saving chat log: {log_e}")
    
    finally:
        # Clean up resources
        try:
            await bot.close()
        except Exception as e:
            safe_print(f"Error during cleanup: {e}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_ask_claude.py \"Your prompt here\"")
        sys.exit(1)

    await stream_chat(sys.argv[1])


if __name__ == "__main__":
    asyncio.run(main())
