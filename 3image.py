#https://www.datacamp.com/tutorial/gemini-pro-api-tutorial
import google.generativeai as genai
from google.generativeai.types import ContentType
from PIL import Image
#from IPython.display import display,Markdown
import os, sys
e=sys.exit
from pprint import pprint as pp
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

import asyncio


genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel('gemini-1.5-pro-latest')

text_prompt = "Give detailed artistic description. add ukrainian essence"
bookshelf_image = Image.open("GettyImages-871168786.max-2600x2600.jpg")
prompt = [text_prompt, bookshelf_image]

#response_stream = model.generate_content_async(prompt)


def stream_generate():
    stream = model.generate_content(prompt, stream=True)
    for chunk in stream:
        print(chunk.text, end='', flush=True)
        #wait asyncio.sleep(0.1)

# Run the asynchronous function
#asyncio.run(generate_and_stream())
stream_generate()

if 0:
    response = model.generate_content(prompt)
    txt=response.text
    print(txt)
    print('---')
#md=Markdown(txt)
#pp(dir(md))
#print(md.data)
if 0:
    import vertexai

    from vertexai.generative_models import GenerativeModel, Part

    # TODO(developer): Update and un-comment below line
    # project_id = "PROJECT_ID"
    PROJECT_ID = "spatial-flag-427113-n0"
    vertexai.init(project=PROJECT_ID, location="us-central1")

    model = GenerativeModel(model_name="gemini-1.5-pro")

    response = model.generate_content(
        [
            Part.from_uri(
                "gs://cloud-samples-data/generative-ai/image/scones.jpg",
                mime_type="image/jpeg",
            ),
            "What is shown in this image?",
        ]
    )

    print(response.text)


