import os, time
import base64
import requests
from colorama import Fore, Style
from os.path import isfile
from pprint import pprint as pp
from dotenv import load_dotenv
load_dotenv()

# Start the timer
start_time = time.time()
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
if 1:
    # Path to your image
    image_path_1 = "test_image_1.jpeg"
    assert isfile(image_path_1), image_path_1
    # Getting the base64 string
    base64_image_1 = encode_image(image_path_1)
if 1:
    # Path to your image
    image_path_2 = "woman_1.jpg"
    assert isfile(image_path_2), image_path_2
    # Getting the base64 string
    base64_image_2 = encode_image(image_path_2)

headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {api_key}"
}

payload = {
  "model": "gpt-4-turbo",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          #"text": "What are in these images? Is there any difference between them?",
          "text": "mix descriptions of these images into one creative description. add depth and emotions.",
        },
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image_1}",
            "detail": "high"
          }
        },
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image_2}",
            "detail": "high"
          }
        },
      ],
    }
  ],
  "max_tokens": 300
}

response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
#pp(dir(response))

ret=response.json()
#pp(ret)

try:
  assert (response.status_code==200)
  assert 'choices' in ret
  assert  ret['choices'][0]
  assert 'message' in ret['choices'][0]
  assert 'content' in ret['choices'][0]['message']
  if 1:
    

    print(f"{Fore.GREEN}")
    print(f"{Style.BRIGHT}")
    print(ret['choices'][0]['message']['content'])
    print(f"{Style.RESET_ALL}")
except:
  print("Error in response")
  pp(ret)
  print(f"{Style.RESET_ALL}")
  raise
   
# Stop the timer
end_time = time.time()

# Calculate the elapsed time
elapsed_time = end_time - start_time
print(f"{Fore.BLUE}")
print(f"{Style.BRIGHT}")
print(f"Elapsed time: {elapsed_time:.2f} seconds")
print(f"{Style.RESET_ALL}")