from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import uvicorn
from datetime import datetime
from chatgpt_streamer import ChatGPTStreamer

app = FastAPI(title="ChatGPT Streaming API", version="1.0.0")

# Initialize the ChatGPT streamer
chatgpt_streamer = ChatGPTStreamer()

class ChatRequest(BaseModel):
    message: str
    timeout: int = 60

async def generate_sse_stream(message: str, timeout: int = 60):
    """Generate Server-Sent Events stream for the chat response"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Starting stream for message:")
    print(f"📝 Message: {message}")
    print(f"⏱️  Timeout: {timeout}s")
    print("-" * 60)
    
    try:
        response_started = False
        full_response = ""
        
        async for response in chatgpt_streamer.send_message_with_streaming(message, timeout):
            status = response.get("status", "")
            content = response.get("content", "")
            
            # Console logging for different response statuses
            if status == "started" and not response_started:
                print("🎯 Response streaming started...")
                response_started = True
            elif status == "streaming":
                # Show incremental content
                if len(content) > len(full_response):
                    new_chunk = content[len(full_response):]
                    print(new_chunk, end='', flush=True)
                    full_response = content
            elif status == "complete":
                # Show any final chunk and completion message
                if len(content) > len(full_response):
                    new_chunk = content[len(full_response):]
                    print(new_chunk, end='', flush=True)
                print(f"\n✅ Response complete! ({len(content)} characters)")
                print("=" * 60)
                full_response = content
            elif status in ["timeout", "error"]:
                print(f"\n❌ {status.upper()}: {content}")
                print("=" * 60)
            
            # Format as Server-Sent Events
            event_data = json.dumps(response)
            yield f"data: {event_data}\n\n"
            
            # End stream on completion, timeout, or error
            if response["status"] in ["complete", "timeout", "error"]:
                break
                
    except Exception as e:
        error_msg = f"Stream error: {str(e)}"
        print(f"\n❌ ERROR: {error_msg}")
        print("=" * 60)
        error_response = {"status": "error", "content": error_msg}
        yield f"data: {json.dumps(error_response)}\n\n"

@app.post("/chatgpt")
async def chat_with_gpt(request: ChatRequest):
    """
    Send a message to ChatGPT and receive streaming response via Server-Sent Events
    """
    # Log incoming request
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*80}")
    print(f"[{timestamp}] 📨 NEW REQUEST to /chatgpt")
    print(f"📝 Message: '{request.message}'")
    print(f"⏱️  Timeout: {request.timeout}s")
    print(f"{'='*80}")
    
    try:
        return StreamingResponse(
            generate_sse_stream(request.message, request.timeout),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )
    except Exception as e:
        error_msg = f"Failed to process request: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "ChatGPT Streaming API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ChatGPT Streaming API"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
