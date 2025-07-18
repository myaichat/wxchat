#!/usr/bin/env python3
"""
Demo script showing how to use the async streaming method
Usage: python demo_async_streaming.py "your question"
"""

import sys
import asyncio
from claude_simple_cdp_streaming import StreamingClaude

async def demo_streaming(question):
    """Demo the async streaming functionality"""
    print("🚀 Claude Async Streaming Demo")
    print("=" * 40)
    print(f"📝 Question: {question}")
    print()
    
    # Initialize Claude
    claude = StreamingClaude()
    
    # Check if Claude tab is available
    if not claude.get_claude_tab():
        print("❌ No Claude.ai tab found")
        print("Please open https://claude.ai in Chrome with debug port")
        return
    
    print("✅ Found Claude.ai tab")
    print("📤 Sending question and starting stream...")
    print()
    print("🤖 Claude's response (streaming):")
    print("-" * 40)
    
    full_response = ""
    chunk_count = 0
    
    try:
        async for chunk_data in claude.send_message_with_streaming(question):
            chunk_count += 1
            
            # Handle errors
            if "error" in chunk_data:
                print(f"\n❌ Error: {chunk_data['error']}")
                break
            
            # Get the new chunk
            chunk = chunk_data.get("chunk", "")
            full_text = chunk_data.get("full_text", "")
            is_complete = chunk_data.get("complete", False)
            is_generating = chunk_data.get("generating", False)
            length = chunk_data.get("length", 0)
            
            # Print the new chunk
            if chunk:
                print(chunk, end='', flush=True)
                full_response += chunk
            
            # Handle reformatted text (when Claude reorganizes the response)
            if chunk_data.get("reformatted"):
                print(f"\n[Text reformatted - {length} chars]", end='', flush=True)
            
            # Show progress every 10 chunks
            if chunk_count % 10 == 0 and is_generating:
                print(f"\n[Chunk #{chunk_count}, {length} chars total]", end='', flush=True)
            
            # Check if complete
            if is_complete:
                print()  # New line
                print("-" * 40)
                
                if chunk_data.get("timeout"):
                    print("⏰ Streaming timed out")
                elif chunk_data.get("reason") == "no_new_content":
                    print("✅ Response complete (no new content)")
                else:
                    print("✅ Response complete!")
                
                print(f"📊 Total chunks received: {chunk_count}")
                print(f"📏 Final length: {length} characters")
                break
    
    except Exception as e:
        print(f"\n❌ Exception during streaming: {e}")
    
    print()
    print("📋 Final Response:")
    print("=" * 40)
    print(full_response or full_text)
    print("=" * 40)

async def demo_multiple_questions():
    """Demo streaming multiple questions in sequence"""
    questions = [
        "Hello, how are you?",
        "What is Python?",
        "Tell me a joke"
    ]
    
    claude = StreamingClaude()
    
    if not claude.get_claude_tab():
        print("❌ No Claude.ai tab found")
        return
    
    print("🚀 Multiple Questions Demo")
    print("=" * 40)
    
    for i, question in enumerate(questions, 1):
        print(f"\n📝 Question {i}: {question}")
        print("-" * 30)
        
        async for chunk_data in claude.send_message_with_streaming(question):
            if "error" in chunk_data:
                print(f"❌ Error: {chunk_data['error']}")
                break
            
            chunk = chunk_data.get("chunk", "")
            if chunk:
                print(chunk, end='', flush=True)
            
            if chunk_data.get("complete"):
                print()
                break
        
        # Wait between questions
        if i < len(questions):
            print("\n⏳ Waiting before next question...")
            await asyncio.sleep(3)

def main():
    if len(sys.argv) < 2:
        print("Usage: python demo_async_streaming.py 'your question'")
        print("   or: python demo_async_streaming.py --multiple")
        print()
        print("Examples:")
        print("  python demo_async_streaming.py 'Tell me about Python'")
        print("  python demo_async_streaming.py --multiple")
        return
    
    if sys.argv[1] == "--multiple":
        asyncio.run(demo_multiple_questions())
    else:
        question = sys.argv[1]
        asyncio.run(demo_streaming(question))

if __name__ == "__main__":
    main()
