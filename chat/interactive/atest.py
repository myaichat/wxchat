import asyncio
import os
import openai
from dotenv import load_dotenv
load_dotenv()

# Set your OpenAI API key here
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("API key is not loaded!")
else:
    print("API key loaded successfully.")
openai.api_key = api_key


async def async_chat_completion(question):
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, openai.ChatCompletion.create,
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question}
        ],
    )
    return response

# Usage
async def main():
    response = await async_chat_completion("What's the weather like?")
    print(response.choices[0].message['content'])

asyncio.run(main())