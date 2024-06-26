#
#https://github.com/anthropics/anthropic-cookbook/blob/main/multimodal/best_practices_for_vision.ipynb

import base64
from anthropic import Anthropic


client = Anthropic()
MODEL_NAME = "claude-3-opus-20240229"

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

#b_data=get_base64_encoded_image("test.jpeg")
b_data=get_base64_encoded_image("test2.png")
prompt="""You have perfect artistic sence and pay great attention to detail which makes you an expert at describing images.
Give formal analysis of this artwork? Before providing the answer in <answer> 
tags, think step by step in <thinking> tags and analyze every part of the image."""

message_list = [
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
    messages=message_list
    
)
print(response.content[0].text)