import requests
import os
from pprint import pprint as pp

# Set up the API endpoint and headers
url = "https://api.openai.com/v1/images/generations"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
}

# Set up the request payload
payload = {
    "model": "dall-e-3",
    "prompt": "A cute baby sea otter",
    "n": 1,
    "size": "1024x1024"
}

# Make the request
response = requests.post(url, headers=headers, json=payload)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()
    pp(data)
    if 1:
        image_urls = data.get("data", [])
        
        # Directory to save images
        download_dir = "downloaded_images"
        os.makedirs(download_dir, exist_ok=True)
        
        # Download each image
        for i, img_data in enumerate(image_urls):
            img_url = img_data.get("url")
            if img_url:
                img_response = requests.get(img_url)
                if img_response.status_code == 200:
                    with open(os.path.join(download_dir, f"image_{i+1}.jpg"), "wb") as img_file:
                        img_file.write(img_response.content)
                    print(f"Image {i+1} downloaded successfully.")
                else:
                    print(f"Failed to download image {i+1}.")
else:
    print("Failed to generate images:", response.json())
