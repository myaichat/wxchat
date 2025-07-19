#!/usr/bin/env python3
"""
Simple Gemini question script - minimal working version
"""

import asyncio
import json
import websockets
import sys
import time

async def ask_gemini_question(question):
    """Ask Gemini a question and get the response"""
    websocket_url = "ws://localhost:9222/devtools/page/8D25B8EDED124ED7635252EF0F0E4217"
    
    # Connect to Chrome DevTools
    websocket_conn = await websockets.connect(websocket_url)
    message_id = 0
    
    async def send_command(method, params=None):
        nonlocal message_id
        message_id += 1
        command = {
            "id": message_id,
            "method": method,
            "params": params or {}
        }
        
        await websocket_conn.send(json.dumps(command))
        
        # Wait for response
        while True:
            response = await websocket_conn.recv()
            data = json.loads(response)
            
            if data.get("id") == message_id:
                return data
    
    try:
        # Enable Runtime domain
        await send_command("Runtime.enable")
        print(f"🗨️  Asking Gemini: {question}")
        
        # Get baseline AI messages - try multiple selectors
        baseline_response = await send_command("Runtime.evaluate", {
            "expression": """
                (() => {
                    // Try multiple selectors for AI messages
                    const selectors = [
                        'div[data-message-author="ai"]',
                        'div[data-testid*="message"]',
                        'div[class*="message"]',
                        'div[class*="response"]',
                        '.model-response',
                        '.ai-message'
                    ];
                    
                    for (const selector of selectors) {
                        const msgs = Array.from(document.querySelectorAll(selector));
                        if (msgs.length > 0) {
                            const lastMsg = msgs[msgs.length - 1].innerText.trim();
                            if (lastMsg) return lastMsg;
                        }
                    }
                    return '';
                })()
            """,
            "returnByValue": True
        })
        baseline = baseline_response.get('result', {}).get('result', {}).get('value', '')
        print(f"📝 Baseline message length: {len(baseline)}")
        
        # Type the question and send it
        inject_response = await send_command("Runtime.evaluate", {
            "expression": f"""
                (() => {{
                    const input = document.querySelector('.ql-editor:not(.ql-clipboard)');
                    if (!input) return 'NO_INPUT';
                    
                    input.focus();
                    input.innerText = {json.dumps(question)};
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    // Press Enter
                    input.dispatchEvent(new KeyboardEvent('keydown', {{
                        bubbles: true,
                        cancelable: true,
                        key: 'Enter',
                        code: 'Enter',
                        which: 13
                    }}));
                    
                    return 'SENT';
                }})()
            """,
            "returnByValue": True
        })
        
        inject_result = inject_response.get('result', {}).get('result', {}).get('value')
        if inject_result != 'SENT':
            print(f"❌ Failed to send question: {inject_result}")
            return None
        
        print("📤 Question sent, waiting for response...")
        
        # Wait for response
        start_time = time.time()
        last_response = ""
        
        while time.time() - start_time < 30:  # 30 second timeout
            response = await send_command("Runtime.evaluate", {
                "expression": """
                    (() => {
                        // Try multiple selectors for AI messages
                        const selectors = [
                            'div[data-message-author="ai"]',
                            'div[data-testid*="message"]',
                            'div[class*="message"]',
                            'div[class*="response"]',
                            '.model-response',
                            '.ai-message'
                        ];
                        
                        for (const selector of selectors) {
                            const msgs = Array.from(document.querySelectorAll(selector));
                            if (msgs.length > 0) {
                                const lastMsg = msgs[msgs.length - 1].innerText.trim();
                                if (lastMsg) return lastMsg;
                            }
                        }
                        return '';
                    })()
                """,
                "returnByValue": True
            })
            
            current_response = response.get('result', {}).get('result', {}).get('value', '')
            
            if current_response and current_response != baseline:
                if current_response != last_response:
                    print(f"📝 Response: {current_response[:100]}...")
                    last_response = current_response
                
                # Check if response seems complete
                if len(current_response) > 20 and (
                    current_response.endswith(('.', '!', '?')) or
                    time.time() - start_time > 10
                ):
                    # Wait a bit more to see if there's additional content
                    await asyncio.sleep(2)
                    
                    final_response = await send_command("Runtime.evaluate", {
                        "expression": """
                            (() => {
                                const msgs = Array.from(document.querySelectorAll('div[data-message-author="ai"]'));
                                return msgs.length ? msgs[msgs.length - 1].innerText.trim() : '';
                            })()
                        """,
                        "returnByValue": True
                    })
                    
                    final_text = final_response.get('result', {}).get('result', {}).get('value', '')
                    if final_text == current_response:
                        return final_text
                    current_response = final_text
            
            await asyncio.sleep(1)
        
        if last_response and last_response != baseline:
            return last_response
        
        print("⏰ No response received within timeout")
        return None
        
    finally:
        await websocket_conn.close()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_gem_ask.py \"Your question here\"")
        sys.exit(1)
    
    question = " ".join(sys.argv[1:])
    
    try:
        response = await ask_gemini_question(question)
        
        if response:
            print("\n" + "="*50)
            print("🤖 Gemini says:")
            print("="*50)
            print(response)
        else:
            print("❌ No response received")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
