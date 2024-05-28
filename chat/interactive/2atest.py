import asyncio
import keyboard
import os
from dotenv import load_dotenv
import openai

load_dotenv()

# Set your OpenAI API key here
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("API key is not loaded!")
else:
    print("API key loaded successfully.")
openai.api_key = api_key

# This function waits for a certain duration and then cancels a task
async def stop_on_keypress(task, key):
    await asyncio.get_running_loop().run_in_executor(None, lambda: keyboard.wait(key))
    task.cancel()

async def async_chat_completion(question):
    # Streamed response handling
    def fetch_stream():
        return openai.ChatCompletion.create(
            model="gpt-4",  # Change the model to GPT-4
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question}
            ],
            stream=True  # Enable streaming
        )

    loop = asyncio.get_event_loop()

    future = loop.run_in_executor(None, fetch_stream)
    task = asyncio.ensure_future(future)

    # Create a task that will cancel the fetch_stream task when Ctrl+S is pressed
    stop_task = asyncio.create_task(stop_on_keypress(task, 'ctrl+s'))

    try:
        # Wait for the fetch_stream task to complete
        response = await task
    except asyncio.CancelledError:
        print('The fetch_stream operation was cancelled.')

    # Cancel the stop_task if it's still running
    if not stop_task.done():
        stop_task.cancel()

    return response

# Usage
async def main():
    response_stream = await async_chat_completion("What are new features of apache spark?")
    
    # Handle streaming output
    try:
        print("Response from GPT-4:")
        for chunk in response_stream:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)
    except Exception as e:
        print(f"Error handling stream: {e}")

asyncio.run(main())
