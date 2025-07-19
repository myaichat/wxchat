#!/usr/bin/env python3
"""
Debug script to find the correct Gemini input selectors
"""

import asyncio
import json
import websockets

class GeminiSelectorDebug:
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
    
    async def debug_selectors(self):
        """Debug available selectors"""
        print("\n=== Debugging Gemini selectors ===")
        
        # Test various selectors
        selectors = [
            ".ql-editor",
            ".ql-editor.textarea.new-input-ui",
            ".ql-editor:not(.ql-clipboard)",
            "div[contenteditable='true']",
            "div[contenteditable='true']:not(.ql-clipboard)",
            "textarea",
            "[role='textbox']",
            "div.textarea",
            "div.new-input-ui"
        ]
        
        for selector in selectors:
            try:
                response = await self.send_command("Runtime.evaluate", {
                    "expression": f"document.querySelector('{selector}') !== null",
                    "returnByValue": True
                })
                
                result = response.get('result', {}).get('result', {})
                found = result.get('value', False)
                
                print(f"  {selector}: {'✅ FOUND' if found else '❌ NOT FOUND'}")
                
                if found:
                    # Get more details about this element
                    response = await self.send_command("Runtime.evaluate", {
                        "expression": f"""
                            (() => {{
                                const el = document.querySelector('{selector}');
                                return el ? {{
                                    tagName: el.tagName,
                                    className: el.className,
                                    id: el.id,
                                    contentEditable: el.contentEditable,
                                    placeholder: el.placeholder || el.getAttribute('placeholder') || 'none'
                                }} : null;
                            }})()
                        """,
                        "returnByValue": True
                    })
                    
                    details = response.get('result', {}).get('result', {}).get('value')
                    if details:
                        print(f"    Details: {details}")
                
            except Exception as e:
                print(f"  {selector}: ❌ ERROR - {e}")
        
        # Test if we can find all contenteditable elements
        print("\n=== All contenteditable elements ===")
        try:
            response = await self.send_command("Runtime.evaluate", {
                "expression": """
                    Array.from(document.querySelectorAll('div[contenteditable="true"]')).map((el, i) => ({
                        index: i,
                        className: el.className,
                        id: el.id || 'no-id',
                        placeholder: el.placeholder || el.getAttribute('placeholder') || 'none',
                        visible: el.offsetWidth > 0 && el.offsetHeight > 0
                    }))
                """,
                "returnByValue": True
            })
            
            elements = response.get('result', {}).get('result', {}).get('value', [])
            for el in elements:
                print(f"  Element {el['index']}: {el}")
                
        except Exception as e:
            print(f"  Error getting contenteditable elements: {e}")
    
    async def close(self):
        if self.websocket:
            await self.websocket.close()
            print("Disconnected")

async def main():
    print("Gemini Selector Debug Tool")
    print("=" * 50)
    
    debugger = GeminiSelectorDebug()
    
    try:
        websocket_url = "ws://localhost:9222/devtools/page/8D25B8EDED124ED7635252EF0F0E4217"
        
        await debugger.connect(websocket_url)
        await debugger.debug_selectors()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await debugger.close()

if __name__ == "__main__":
    asyncio.run(main())
