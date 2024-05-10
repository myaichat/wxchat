import asyncio
import os
from dotenv import load_dotenv
import openai

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("API key is not loaded!")
else:
    print("API key loaded successfully.")
openai.api_key = api_key

async def stop_on_keypress(task):
    try:
        # Await a specific key press; in this case, using a simple asyncio sleep to simulate.
        await asyncio.sleep(10)  # Here you would integrate your actual keypress detection.
    except asyncio.CancelledError:
        print('Keypress wait was cancelled.')
    finally:
        task.cancel()

async def async_chat_completion(question):
    def fetch_stream():
        return openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question}
            ],
            stream=True
        )

    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(None, fetch_stream)
    
    # Create a task for cancelling this future on a keypress
    stop_task = asyncio.create_task(stop_on_keypress(future))

    try:
        response = await future
        return response
    except asyncio.CancelledError:
        print('The fetch_stream operation was cancelled.')
        return None
    finally:
        if not stop_task.done():
            stop_task.cancel()

async def main():
    response_stream = await async_chat_completion("What are new features of Apache Spark?")
    if response_stream:
        print("Response from GPT-4:")
        try:
            for chunk in response_stream:
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
        except Exception as e:
            print(f"Error handling stream: {e}")

asyncio.run(main())
