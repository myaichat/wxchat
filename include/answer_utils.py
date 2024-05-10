import openai
import os
from dotenv import load_dotenv
load_dotenv()

# Set your OpenAI API key here
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("API key is not loaded!")
else:
    print("API key loaded successfully.")
openai.api_key = api_key

def stream_response(prompt):
    # Create a chat completion request with streaming enabled
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a chatbot that assists with Apache Spark queries."},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )

        # Print each response chunk as it arrives
        print("Streaming response:")

        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    stream_response("Hey, what are new features of Apache Spark?")
