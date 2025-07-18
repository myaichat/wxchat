#!/usr/bin/env python3
"""
Simple example showing how to use the async streaming method in your own code
"""

import asyncio
from claude_simple_cdp_streaming import StreamingClaude

async def example_usage():
    """Example of how to use the async streaming method"""
    
    # Initialize the Claude streaming client
    claude = StreamingClaude()
    
    # Check if Claude tab is available
    if not claude.get_claude_tab():
        print("Please open Claude.ai in Chrome with debug port")
        return
    
    # Your question
    question = "Explain what machine learning is in simple terms"
    
    print(f"Asking: {question}")
    print("Response:")
    
    # Use the async generator to get chunks
    async for chunk in claude.send_message_with_streaming(question):
        # Handle errors
        if "error" in chunk:
            print(f"Error: {chunk['error']}")
            break
        
        # Print new text as it comes in
        new_text = chunk.get("chunk", "")
        if new_text:
            print(new_text, end='', flush=True)
        
        # Check if response is complete
        if chunk.get("complete"):
            print()  # New line
            print(f"\nFinal response length: {chunk.get('length', 0)} characters")
            break

async def collect_full_response():
    """Example of collecting the full response while streaming"""
    
    claude = StreamingClaude()
    
    if not claude.get_claude_tab():
        print("Please open Claude.ai in Chrome with debug port")
        return
    
    question = "Write a short poem about coding"
    full_response = ""
    
    print(f"Asking: {question}")
    print("Collecting response...")
    
    async for chunk in claude.send_message_with_streaming(question):
        if "error" in chunk:
            print(f"Error: {chunk['error']}")
            break
        
        # Collect chunks
        new_text = chunk.get("chunk", "")
        if new_text:
            full_response += new_text
            print(".", end='', flush=True)  # Show progress
        
        if chunk.get("complete"):
            break
    
    print("\n\nFull response collected:")
    print("=" * 40)
    print(full_response)
    print("=" * 40)

async def process_chunks():
    """Example of processing chunks as they come in"""
    
    claude = StreamingClaude()
    
    if not claude.get_claude_tab():
        print("Please open Claude.ai in Chrome with debug port")
        return
    
    question = "List 5 programming languages and their uses"
    word_count = 0
    
    print(f"Asking: {question}")
    print("Processing chunks...")
    
    async for chunk in claude.send_message_with_streaming(question):
        if "error" in chunk:
            print(f"Error: {chunk['error']}")
            break
        
        # Process each chunk
        new_text = chunk.get("chunk", "")
        if new_text:
            # Count words in this chunk
            words_in_chunk = len(new_text.split())
            word_count += words_in_chunk
            
            print(f"[+{words_in_chunk} words] ", end='', flush=True)
            print(new_text, end='', flush=True)
        
        if chunk.get("complete"):
            print(f"\n\nTotal words received: {word_count}")
            break

def main():
    print("🚀 Async Streaming Usage Examples")
    print("=" * 40)
    print()
    
    print("1. Basic streaming example")
    asyncio.run(example_usage())
    
    print("\n" + "=" * 40)
    print("2. Collect full response example")
    asyncio.run(collect_full_response())
    
    print("\n" + "=" * 40)
    print("3. Process chunks example")
    asyncio.run(process_chunks())

if __name__ == "__main__":
    main()
