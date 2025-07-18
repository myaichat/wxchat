#!/usr/bin/env python
"""
simple_ask_chatgpt.py  –  directly call send_message_with_streaming and stream the reply

Usage:
    python simple_ask_chatgpt.py "Your prompt here"
"""

import asyncio
import json
import sys
import io
import os
from datetime import datetime

# Import the streaming function directly
from chat_handlers.chatgpt_streaming_chat import send_message_with_streaming

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


def save_chat_log(question: str, answer: str, model: str = "gpt-4o"):
    """Save individual chat session to timestamped JSON file (silently)"""
    try:
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
        filename = f"logs/simple_ask_chatgpt_chat_session_{filename_timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=2)
        
        return filename
    except Exception:
        # Silently ignore any logging errors
        return None


async def stream_chat(prompt: str):
    """Stream chat using direct streaming_chat function"""
    previous = ""
    complete_answer = ""
    
    # Print the question
    safe_print(f"Question: {prompt}")
    safe_print("-" * 50)
    safe_print("Response:")
    
    try:
        async for chunk in send_message_with_streaming(prompt, TIMEOUT_SEC):
            status = chunk.get("status")
            content = chunk.get("content", "")
            
            if status == "streaming":
                # Simple streaming - display new content as it arrives
                if len(content) > len(previous):
                    new_chunk = content[len(previous):]
                    safe_print(new_chunk, end="", flush=True)
                    previous = content
            elif status == "complete":
                complete_answer = content
                # Show any remaining content that wasn't displayed during streaming
                if len(content) > len(previous):
                    remaining = content[len(previous):]
                    safe_print(remaining, end="", flush=True)
                elif len(previous) == 0:
                    # If we never got streaming updates, show the complete content
                    safe_print(content, end="", flush=True)
                safe_print("\n")
                
                # Save the complete conversation to log (silently)
                try:
                    save_chat_log(prompt, complete_answer)
                except Exception:
                    pass  # Silently ignore logging errors
                break
            elif status in ["timeout", "error"]:
                complete_answer = f"Error: {content}"
                safe_print(f"\nError: {content}")
                
                # Save error response to log (silently)
                try:
                    save_chat_log(prompt, complete_answer)
                except Exception:
                    pass  # Silently ignore logging errors
                break
                
    except Exception as e:
        safe_print(f"\nError: {e}")
        complete_answer = f"Error: {e}"
        try:
            save_chat_log(prompt, complete_answer)
        except Exception:
            pass  # Silently ignore logging errors


async def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_ask_chatgpt.py \"Your prompt here\"")
        sys.exit(1)

    await stream_chat(sys.argv[1])


if __name__ == "__main__":
    asyncio.run(main())
