import openai
import os
from dotenv import load_dotenv
load_dotenv()



# Set your OpenAI API key here
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the client
client = openai.OpenAI()

def stream_response(prompt):
    # Create a chat completion request with streaming enabled
    stream = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a chatbot that assists with Apache Spark queries."},
            {"role": "user", "content": prompt}
        ],
        stream=True
    )

    # Print each response chunk as it arrives
    try:
        for message in stream:
            print("Inspecting message structure...")
            print(dir(message))  # To see all attributes of the message object
            print("Choices attribute:", dir(message.choices[0]))  # To inspect the structure of choices
            if message.choices:
                print("Content:", message.choices[0].content)
    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    stream_response("Hey, what are new features of Apache Spark?")
