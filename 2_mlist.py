import requests

import os

DEEPSEEK_API_KEY= os.getenv("DEEPSEEK_API_KEY")

url = "https://api.deepseek.com/models"

payload={}
headers = {
  'Accept': 'application/json',
  'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)