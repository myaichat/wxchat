import os
import base64
import requests
from os.path import isfile
from pprint import pprint as pp
from dotenv import load_dotenv
load_dotenv()

# Set your OpenAI API key here
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("API key is not loaded!")
else:
    print("API key loaded successfully.")

# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

# Path to your image
image_path = "test_image.jpeg"
assert isfile(image_path), image_path
# Getting the base64 string
base64_image = encode_image(image_path)

headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {api_key}"
}

payload = {
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What are in these images? Is there any difference between them?",
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
          },
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
          },
        },
      ],
    }
  ],
  "max_tokens": 300
}

response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
#pp(dir(response))
assert (response.status_code==200)
ret=response.json()
#pp(ret)
try:
  assert 'choices' in ret
  assert  ret['choices'][0]
  assert 'message' in ret['choices'][0]
  assert 'content' in ret['choices'][0]['message']
  pp(ret['choices'][0]['message']['content'])
except:
  print("Error in response")
  pp(ret)
  raise
   
