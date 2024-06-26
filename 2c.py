import base64
from anthropic import Anthropic

client = Anthropic()
#claude-3-haiku-20240307"
#"claude-3-opus-20240229"
#"claude-3-sonnet-20240229"
#"claude-3-5-sonnet-20240620"
#claude-3-5-sonnet-20240620	claude-3-opus-20240229	claude-3-sonnet-20240229	claude-3-haiku-20240307
MODEL_NAME = "claude-3-haiku-20240307"
MODEL_NAME = "claude-3-5-sonnet-20240620"


from PIL import Image
import io
import base64

def get_base64_encoded_image(image_path):
    # Open the image and convert it to JPEG
    with Image.open(image_path) as image:
        with io.BytesIO() as buffer:
            image.convert('RGB').save(buffer, format="JPEG")
            binary_data = buffer.getvalue()
    
    # Encode the JPEG binary data to base64
    base_64_encoded_data = base64.b64encode(binary_data)
    base64_string = base_64_encoded_data.decode('utf-8')
    return base64_string

def chat_with_image(image_path, prompt, chat_history=[]):
    b_data = get_base64_encoded_image(image_path)
    
    message_list = chat_history + [
        {
            "role": 'user',
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b_data}},
                {"type": "text", "text": prompt}
            ]
        }
    ]

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2048,
        temperature=0.7,
        top_p=0.9,
        #frequency_penalty=0.2,  # Slight penalty for frequent tokens
        #presence_penalty=0.2,   # Slight penalty for new tokens        
        #stop_sequences=["Human:", "AI:"],
        stop_sequences=["Human:", "User:", "Assistant:", "AI:"],
        #system="You have perfect artistic sense and pay great attention to detail which makes you an expert at describing images.",
        system="You have perfect artistic sense and pay great attention to detail which makes you an expert at describing images.",
        messages=message_list,
        stream=False,
    )
    
    assistant_message = {
        "role": "assistant",
        "content": response.content[0].text
    }
    
    chat_history.append(message_list[-1])  # Add user's message to history
    chat_history.append(assistant_message)  # Add assistant's response to history
    
    return response.content[0].text, chat_history

# Example usage
chat_history = []
ifn="test.jpeg"
ifn="superpower.jpg"
prompt1 = """ 
Give formal analysis of this artwork? Before providing the answer in <answer> 
tags, think step by step in <thinking> tags and analyze every part of the image.
"""

response1, chat_history = chat_with_image(ifn, prompt1, chat_history)
print("First response:")
print(response1)
if 0:
    prompt2 = "Now, can you tell me about the color palette used in this artwork?"

    response2, chat_history = chat_with_image(ifn, prompt2, chat_history)
    print("\nSecond response:")
    print(response2)

# You can continue the conversation by calling chat_with_image with new prompts and passing the chat_history