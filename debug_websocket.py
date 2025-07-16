#!/usr/bin/env python
"""
Debug script to test WebSocket connection and basic functionality
"""

import asyncio
import websockets
import json

async def test_websocket_connection():
    """Test basic WebSocket connection and console logging"""
    ws_url = "ws://localhost:9222/devtools/page/88E0A660C0870B92DD1E7248EDABA645"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected to WebSocket successfully")
            
            # Enable Runtime domain
            await websocket.send(json.dumps({
                "id": 1,
                "method": "Runtime.enable"
            }))
            
            # Wait for response
            response = await websocket.recv()
            print(f"Runtime.enable response: {response}")
            
            # Test simple console.log
            test_js = '''
                console.log("TEST: WebSocket connection working");
                "Connection test complete";
            '''
            
            await websocket.send(json.dumps({
                "id": 2,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": test_js,
                    "returnByValue": True
                }
            }))
            
            # Wait for evaluation response
            eval_response = await websocket.recv()
            print(f"Evaluation response: {eval_response}")
            
            # Listen for console messages for a few seconds
            print("Listening for console messages...")
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < 5:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if data.get("method") == "Runtime.consoleAPICalled":
                        args = data.get("params", {}).get("args", [])
                        if args:
                            console_message = args[0].get("value", "")
                            print(f"Console: {console_message}")
                            
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
                    
            print("✅ WebSocket test completed successfully")
            
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())
