#!/usr/bin/env python3
"""
Quick test for Claude streaming - just run this
"""

import asyncio
from claude_simple_cdp_streaming import StreamingClaude

async def test():
    claude = StreamingClaude()
    
    if not claude.get_claude_tab():
        print("❌ No Claude tab found. Open claude.ai in Chrome first!")
        return
    
    print("✅ Testing streaming...")
    
    async for chunk in claude.send_message_with_streaming("Hello, how are you?"):
        if "error" in chunk:
            print(f"Error: {chunk['error']}")
            break
        
        new_text = chunk.get("chunk", "")
        if new_text:
            print(new_text, end='', flush=True)
        
        if chunk.get("complete"):
            print("\n✅ Done!")
            break

if __name__ == "__main__":
    asyncio.run(test())
