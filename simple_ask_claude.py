#!/usr/bin/env python
"""
simple_ask_claude.py  –  directly call send_message_with_streaming and stream the reply

Usage:
    python simple_ask_claude.py "Your prompt here"
"""

import asyncio
import json
import sys
import io
import os
from datetime import datetime

# Import the streaming function directly
from chat_handlers.claude_streaming_chat import send_message_with_streaming

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
    """Stream chat using direct streaming_chat function"""
    previous = ""
    response_started = False
    complete_answer = ""
    
    try:
        async for chunk in send_message_with_streaming(prompt, TIMEOUT_SEC):
            status = chunk.get("status")
            content = chunk.get("content", "")
            
            if status == "started":
                safe_print("🚀  assistant started typing\n")
                response_started = True
            elif status == "streaming":
                # Enhanced smart streaming with better breakpoint detection
                if len(content) > len(previous):
                    # More comprehensive safe breakpoints
                    safe_patterns = [
                        '\n\n',  # Paragraph breaks
                        '\n- ',  # List items
                        '\n## ', # Headers
                        '\n### ', # Subheaders
                        '. ',    # Sentence endings
                        '! ',    # Exclamations
                        '? ',    # Questions
                        ', ',    # Commas
                        '; ',    # Semicolons
                        ': ',    # Colons
                        '**.',   # Bold endings with period
                        '**,',   # Bold endings with comma
                        '**:',   # Bold endings with colon
                        '`.',    # Code endings with period
                        '`,',    # Code endings with comma
                        '```\n', # Code block endings
                    ]
                    
                    last_safe_pos = len(previous)
                    
                    # Find the latest safe position
                    for pattern in safe_patterns:
                        pos = content.rfind(pattern, len(previous))
                        if pos != -1 and pos + len(pattern) > last_safe_pos:
                            last_safe_pos = pos + len(pattern)
                    
                    # Also check for complete words (space-bounded)
                    space_pos = content.rfind(' ', len(previous))
                    if space_pos != -1 and space_pos + 1 > last_safe_pos:
                        # Make sure we're not in the middle of markdown formatting
                        check_pos = space_pos + 1
                        if check_pos < len(content):
                            # Don't break if we're in the middle of ** or ` formatting
                            before_space = content[max(0, space_pos-5):space_pos]
                            after_space = content[space_pos:min(len(content), space_pos+5)]
                            if not ('**' in before_space and '**' not in after_space) and not ('`' in before_space and '`' not in after_space):
                                last_safe_pos = check_pos
                    
                    # Display if we have a reasonable chunk and it's safe
                    if last_safe_pos > len(previous) + 15:  # At least 15 chars ahead
                        new_chunk = content[len(previous):last_safe_pos]
                        safe_print(new_chunk, end="", flush=True)
                        previous = content[:last_safe_pos]
                    elif len(content) > len(previous) + 150:  # Force display if buffer gets too large
                        # Find the last space to avoid cutting words
                        force_pos = len(previous) + 100
                        last_space = content.rfind(' ', len(previous), force_pos)
                        if last_space > len(previous):
                            new_chunk = content[len(previous):last_space + 1]
                            safe_print(new_chunk, end="", flush=True)
                            previous = content[:last_space + 1]
            elif status == "complete":
                complete_answer = content
                # Show any remaining content that wasn't displayed during streaming
                if len(content) > len(previous):
                    remaining = content[len(previous):]
                    safe_print(remaining, end="", flush=True)
                elif not response_started:
                    # If we never got streaming updates, show the complete content
                    safe_print(content, end="", flush=True)
                safe_print("\n\n✅  complete")
                
                # Save the complete conversation to log
                try:
                    save_chat_log(prompt, complete_answer)
                except Exception as e:
                    safe_print(f"Error saving chat log: {e}")
                break
            elif status in ["timeout", "error"]:
                complete_answer = f"Error: {content}"
                safe_print(f"\n❌  {status}: {content}")
                
                # Save error response to log
                try:
                    save_chat_log(prompt, complete_answer)
                except Exception as e:
                    safe_print(f"Error saving chat log: {e}")
                break
                
    except Exception as e:
        safe_print(f"\n❌  Unexpected error: {e}")
        complete_answer = f"Error: {e}"
        try:
            save_chat_log(prompt, complete_answer)
        except Exception as log_e:
            safe_print(f"Error saving chat log: {log_e}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_ask_claude.py \"Your prompt here\"")
        sys.exit(1)

    await stream_chat(sys.argv[1])


if __name__ == "__main__":
    asyncio.run(main())
