#https://www.datacamp.com/tutorial/gemini-pro-api-tutorial
import google.generativeai as genai
from google.generativeai.types import ContentType
from PIL import Image
#from IPython.display import Markdown
import time
import cv2

GOOGLE_API_KEY = 'your key'
genai.configure(api_key=GOOGLE_API_KEY)
if 0:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)

model = genai.GenerativeModel('gemini-1.5-pro-latest')

response = model.generate_content("Please provide a list of the most influential people in the world.")
print(response.text)

