#!/usr/bin/env python3
"""
Working Gemini chat script using the same approach as simple_gemini_test.py
"""

import asyncio
import json
import websockets
import sys
import time

class WorkingGeminiChat:
    def __init__(self):
        self.websocket = None
        self.message_id = 0
    
    def get_message_id(self):
        self.message_id += 1
        return self.message_id
    
    async def connect(self, websocket_url):
        print(f"Connecting to: {websocket_url}")
        self.websocket = await websockets.connect(websocket_url)
        
        # Enable required domains
        await self.send_command("Runtime.enable")
        await self.send_command("Page.enable")
        print("Connected and enabled Runtime and Page domains")
    
    async def send_command(self, method, params=None):
        message_id = self.get_message_id()
        command = {
            "id": message_id,
            "method": method,
            "params": params or {}
        }
        
        await self.websocket.send(json.dumps(command))
        
        # Wait for response
        while True:
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("id") == message_id:
                return data
    
    async def find_and_click_input(self):
        """Find and focus the input element"""
        try:
            response = await self.send_command("Runtime.evaluate", {
                "expression": """
                    (() => {
                        const input = document.querySelector('.ql-editor:not(.ql-clipboard)');
                        if (input) {
                            input.focus();
                            input.click();
                            return 'FOUND';
                        }
                        return 'NOT_FOUND';
                    })()
                """,
                "returnByValue": True
            })
            
            result = response.get('result', {}).get('result', {})
            return result.get('value') == 'FOUND'
            
        except Exception as e:
            print(f"Error finding input: {e}")
            return False
    
    async def type_message(self, message):
        """Type a message into the input field"""
        try:
            # Clear and type the message
            response = await self.send_command("Runtime.evaluate", {
                "expression": f"""
                    (() => {{
                        const input = document.querySelector('.ql-editor:not(.ql-clipboard)');
                        if (!input) return 'NO_INPUT';
                        
                        // Clear existing content
                        input.innerHTML = '';
                        input.innerText = '';
                        
                        // Set the new message
                        input.innerText = {json.dumps(message)};
                        
                        // Trigger input event
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        
                        return 'TYPED';
                    }})()
                """,
                "returnByValue": True
            })
            
            result = response.get('result', {}).get('result', {})
            return result.get('value') == 'TYPED'
            
        except Exception as e:
            print(f"Error typing message: {e}")
            return False
    
    async def press_enter(self):
        """Press Enter to send the message"""
        try:
            response = await self.send_command("Runtime.evaluate", {
                "expression": """
                    (() => {
                        const input = document.querySelector('.ql-editor:not(.ql-clipboard)');
                        if (!input) return 'NO_INPUT';
                        
                        // Press Enter
                        const enterEvent = new KeyboardEvent('keydown', {
                            bubbles: true,
                            cancelable: true,
                            key: 'Enter',
                            code: 'Enter',
                            which: 13,
                            keyCode: 13
                        });
                        
                        input.dispatchEvent(enterEvent);
                        return 'SENT';
                    })()
                """,
                "returnByValue": True
            })
            
            result = response.get('result', {}).get('result', {})
            return result.get('value') == 'SENT'
            
        except Exception as e:
            print(f"Error pressing enter: {e}")
            return False
    
    async def get_latest_response(self):
        """Get the latest AI response"""
        try:
            response = await self.send_command("Runtime.evaluate", {
                "expression": """
                    (() => {
                        // Try multiple selectors for AI responses
                        const selectors = [
                            'div[data-message-author="ai"]',
                            'div[data-testid*="message"]',
                            'div[class*="message"]',
                            'div[class*="response"]'
                        ];
                        
                        for (const selector of selectors) {
                            const messages = Array.from(document.querySelectorAll(selector));
                            if (messages.length > 0) {
                                const lastMessage = messages[messages.length - 1];
                                const text = lastMessage.innerText.trim();
                                if (text) {
                                    return text;
                                }
                            }
                        }
                        
                        return '';
                    })()
                """,
                "returnByValue": True
            })
            
            result = response.get('result', {}).get('result', {})
            return result.get('value', '')
            
        except Exception as e:
            print(f"Error getting response: {e}")
            return ''
    
    async def ask_question(self, question):
        """Ask a question and wait for response"""
        print(f"🗨️  Asking Gemini: {question}")
        
        # Get baseline response
        print("🔍 Getting baseline...")
        baseline = await self.get_latest_response()
        print(f"📝 Baseline length: {len(baseline)}")
        
        # Find and focus input
        print("🎯 Finding input field...")
        if not await self.find_and_click_input():
            raise Exception("Could not find input field")
        
        # Type the message
        print("⌨️  Typing message...")
        if not await self.type_message(question):
            raise Exception("Could not type message")
        
        # Wait a moment for the UI to update
        await asyncio.sleep(0.5)
        
        # Press Enter
        print("📤 Sending message...")
        if not await self.press_enter():
            raise Exception("Could not send message")
        
        # Wait for response
        print("⏳ Waiting for response...")
        start_time = time.time()
        last_response = ""
        
        while time.time() - start_time < 30:  # 30 second timeout
            current_response = await self.get_latest_response()
            
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
                    final_response = await self.get_latest_response()
                    if final_response == current_response:
                        return final_response
                    current_response = final_response
            
            await asyncio.sleep(1)
        
        if last_response and last_response != baseline:
            return last_response
        
        raise Exception("No response received within timeout")
    
    async def close(self):
        if self.websocket:
            await self.websocket.close()
            print("Disconnected")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python working_gem_chat.py \"Your question here\"")
        sys.exit(1)
    
    question = " ".join(sys.argv[1:])
    
    chat = WorkingGeminiChat()
    
    try:
        websocket_url = "ws://localhost:9222/devtools/page/8D25B8EDED124ED7635252EF0F0E4217"
        
        await chat.connect(websocket_url)
        response = await chat.ask_question(question)
        
        print("\n" + "="*50)
        print("🤖 Gemini says:")
        print("="*50)
        print(response)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await chat.close()

if __name__ == "__main__":
    asyncio.run(main())
