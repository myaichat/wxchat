import base64
from anthropic import Anthropic
from PIL import Image
import io

client = Anthropic()
MODEL_NAME = "claude-3-sonnet-20240229"

def get_base64_encoded_image(image_path):
    with Image.open(image_path) as image:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

def image_fusion_description(image_paths, prompt=None, chat_history=[]):
    content = []
    for image_path in image_paths:
        b_data = get_base64_encoded_image(image_path)
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b_data
            }
        })
    
    if prompt is None:
        prompt = """I want you to imagine and describe in detail a single image that fuses elements from all the provided images. 
        Focus on how the elements from each image interact and blend together. 
        Be specific about colors, shapes, textures, and composition. 
        Your description should be cohesive, as if describing a real painting or photograph that fuses these elements.

        Before providing the final description in <fused_image> tags, think through your process step-by-step in <thinking> tags."""
    
    content.append({"type": "text", "text": prompt})
    
    message_list = chat_history + [
        {
            "role": 'user',
            "content": content
        }
    ]

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2048,
        messages=message_list
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

image_paths = ["image1.jpg", "image2.jpg", "image3.jpg"]  # Replace with your actual image paths

fused_description, chat_history = image_fusion_description(image_paths)
print("Fused Image Description:")
print(fused_description)

# If you want to continue the conversation or get more details about the fused image
follow_up_prompt = "Can you elaborate on how the elements from the different images blend together in this fused image?"
response, chat_history = image_fusion_description(image_paths, prompt=follow_up_prompt, chat_history=chat_history)
print("\nFollow-up Response:")
print(response)