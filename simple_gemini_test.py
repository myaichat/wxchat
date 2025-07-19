#!/usr/bin/env python3
"""
Simple test script to diagnose Gemini Chrome debug connection issues
"""

import asyncio
import json
import websockets
import requests

class SimpleGeminiTest:
    def __init__(self):
        self.websocket = None
        self.message_id = 0
    
    def get_message_id(self):
        self.message_id += 1
        return self.message_id
    
    async def connect(self, websocket_url):
        print(f"Connecting to: {websocket_url}")
        self.websocket = await websockets.connect(websocket_url)
        
        # Enable Runtime domain
        await self.send_command("Runtime.enable")
        print("Connected and enabled Runtime domain")
    
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
    
    async def simple_js_test(self):
        """Test basic JavaScript execution"""
        print("\n=== Testing basic JavaScript execution ===")
        
        # Test 1: Simple expression
        try:
            response = await self.send_command("Runtime.evaluate", {
                "expression": "2 + 2",
                "returnByValue": True
            })
            print(f"Test 1 (2+2): {response}")
        except Exception as e:
            print(f"Test 1 failed: {e}")
        
        # Test 2: Get page title
        try:
            response = await self.send_command("Runtime.evaluate", {
                "expression": "document.title",
                "returnByValue": True
            })
            print(f"Test 2 (page title): {response}")
        except Exception as e:
            print(f"Test 2 failed: {e}")
        
        # Test 3: Check if elements exist
        try:
            response = await self.send_command("Runtime.evaluate", {
                "expression": "document.querySelectorAll('div').length",
                "returnByValue": True
            })
            print(f"Test 3 (div count): {response}")
        except Exception as e:
            print(f"Test 3 failed: {e}")
        
        # Test 4: Find input elements
        try:
            response = await self.send_command("Runtime.evaluate", {
                "expression": """
                    Array.from(document.querySelectorAll('input, textarea, div[contenteditable]')).map(el => ({
                        tag: el.tagName,
                        type: el.type || 'none',
                        contenteditable: el.contentEditable
                    }))
                """,
                "returnByValue": True
            })
            print(f"Test 4 (input elements): {response}")
        except Exception as e:
            print(f"Test 4 failed: {e}")
    
    async def close(self):
        if self.websocket:
            await self.websocket.close()
            print("Disconnected")

async def main():
    print("Simple Gemini Chrome Debug Test")
    print("Testing basic connection and JavaScript execution")
    
    tester = SimpleGeminiTest()
    
    try:
        # Use the WebSocket URL from your JSON
        websocket_url = "ws://localhost:9222/devtools/page/8D25B8EDED124ED7635252EF0F0E4217"
        
        await tester.connect(websocket_url)
        await tester.simple_js_test()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())
