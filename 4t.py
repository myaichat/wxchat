import requests
from pprint import pprint as pp
API_TOKEN  = "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"
headers = {"Authorization": f"Bearer {API_TOKEN}"}
API_URL = "https://api-inference.huggingface.co/models/bert-base-uncased"
def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()
data = query({"inputs": "The answer to the universe is [MASK]."})
pp (data)