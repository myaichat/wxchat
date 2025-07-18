"""
Simple proxy server that can bridge between Streamlit and browser-based Claude interactions.
This server runs separately and can handle the Playwright interactions while exposing
a simple HTTP API that Streamlit can use.
"""

from flask import Flask, request, jsonify, Response
import asyncio
import json
import threading
from typing import Optional
import time
import sys
import os

# Import the original claude streaming chat functionality
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from chat_handlers.claude_streaming_chat import ChromeDebugChatBot

app = Flask(__name__)

class ClaudeProxyServer:
    def __init__(self, debug_port: int = 9222):
        self.debug_port = debug_port
        self.bot = None
        self.loop = None
        self.thread = None
    
    def start_async_loop(self):
        """Start the async event loop in a separate thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def ensure_loop(self):
        """Ensure the async loop is running"""
        if self.loop is None or not self.loop.is_running():
            self.thread = threading.Thread(target=self.start_async_loop, daemon=True)
            self.thread.start()
            time.sleep(0.1)  # Give the loop time to start
    
    async def get_bot(self):
        """Get or create a bot instance"""
        if self.bot is None:
            self.bot = ChromeDebugChatBot(debug_port=self.debug_port)
            if not await self.bot.connect_to_existing_tab():
                self.bot = None
                raise Exception("Failed to connect to Chrome debug session")
        return self.bot
    
    def ask_claude_sync(self, question: str, streaming: bool = True):
        """Synchronous wrapper for asking Claude"""
        self.ensure_loop()
        
        async def _ask():
            try:
                bot = await self.get_bot()
                if streaming:
                    response_chunks = []
                    async for chunk in bot.send_message_with_streaming(question):
                        if not chunk.startswith("Error:"):
                            response_chunks.append(chunk)
                        else:
                            return {"error": chunk}
                    return {"response": "".join(response_chunks)}
                else:
                    response = await bot.send_message_and_get_response(question)
                    return {"response": response} if response else {"error": "No response received"}
            except Exception as e:
                return {"error": str(e)}
        
        future = asyncio.run_coroutine_threadsafe(_ask(), self.loop)
        return future.result(timeout=60)  # 60 second timeout

# Global proxy server instance
proxy_server = ClaudeProxyServer()

@app.route('/ask', methods=['POST'])
def ask_claude():
    """Handle Claude questions via HTTP POST"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        streaming = data.get('streaming', True)
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        result = proxy_server.ask_claude_sync(question, streaming)
        
        if "error" in result:
            return jsonify(result), 500
        else:
            return jsonify(result)
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ask_stream', methods=['POST'])
def ask_claude_stream():
    """Handle Claude questions with streaming response"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        def generate():
            proxy_server.ensure_loop()
            
            async def _stream():
                try:
                    bot = await proxy_server.get_bot()
                    async for chunk in bot.send_message_with_streaming(question):
                        if not chunk.startswith("Error:"):
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        else:
                            yield f"data: {json.dumps({'error': chunk})}\n\n"
                            break
                    yield f"data: {json.dumps({'done': True})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            future = asyncio.run_coroutine_threadsafe(_stream(), proxy_server.loop)
            try:
                async_gen = future.result(timeout=5)
                for item in async_gen:
                    yield item
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/plain')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "debug_port": proxy_server.debug_port})

@app.route('/status', methods=['GET'])
def status():
    """Status endpoint to check Chrome connection"""
    try:
        # Try to get bot status
        result = proxy_server.ask_claude_sync("test", streaming=False)
        if "error" in result:
            return jsonify({"status": "disconnected", "error": result["error"]})
        else:
            return jsonify({"status": "connected", "debug_port": proxy_server.debug_port})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Claude Proxy Server')
    parser.add_argument('--port', '-p', type=int, default=8080, help='Server port (default: 8080)')
    parser.add_argument('--debug-port', '-d', type=int, default=9222, help='Chrome debug port (default: 9222)')
    parser.add_argument('--host', default='localhost', help='Server host (default: localhost)')
    
    args = parser.parse_args()
    
    proxy_server = ClaudeProxyServer(debug_port=args.debug_port)
    
    print(f"Starting Claude Proxy Server on {args.host}:{args.port}")
    print(f"Chrome debug port: {args.debug_port}")
    print("Make sure Chrome is running with debug enabled:")
    print(f"chrome --remote-debugging-port={args.debug_port} --user-data-dir=/tmp/chrome-debug")
    
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
