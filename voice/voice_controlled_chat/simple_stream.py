import openai
import os
from dotenv import load_dotenv
load_dotenv()

import openai

# Set your OpenAI API key here
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the client
client = openai.OpenAI()

def stream_response(prompt):
    # Create a chat completion request with streaming enabled
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a chatbot that assists with Python interview ."},
            {"role": "user", "content": prompt}
        ],
        stream=True
    )

    # Print each response chunk as it arrives
    for chunk in response:
        if hasattr(chunk.choices[0].delta, 'content'):
            content = chunk.choices[0].delta.content
            print(content, end='', flush=True)

if __name__ == "__main__":
    stream_response("Hey,  what is the fastes was to sort in python?")


