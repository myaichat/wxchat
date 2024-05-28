'''
'''
import os, sys
from io import BytesIO
from openai import OpenAI
from datetime import datetime  # for formatting date returned with images
import base64                  # for decoding images if recieved in the reply
from PIL import Image          # pillow, for processing image types

from pprint import pprint as pp  # for debugging
e=sys.exit

# client = OpenAI(api_key="sk-xxxxx")  # don't do this, OK?
client = OpenAI()  # will use environment variable "OPENAI_API_KEY"


prompt = (
'''A Ukrainian mother protectively embraces her child, her traditional plakhta emblazoned with the flag's blue 
and yellow. Her hair, interwoven with ribbons, echoes the
 resilience of her spirit. Above them, black rockets ' are falling, shattering their homeland's tranquility.'''[:1000-1]
)
image_params = {
 "model": "dall-e-2",  # Defaults to dall-e-2
 "n": 1,               # Between 2 and 10 is only for DALL-E 2
 "size": "1024x1024",  # 256x256, 512x512 only for DALL-E 2 - not much cheaper
 "prompt": prompt,     # DALL-E 3: max 4000 characters, DALL-E 2: max 1000
 "user": "myName",     # pass a customer ID to OpenAI for abuse monitoring
}

## -- You can uncomment the lines below to include these non-default parameters --

image_params.update({"response_format": "b64_json"})  # defaults to "url" for separate download

## -- DALL-E 3 exclusive parameters --
image_params.update({"model": "dall-e-3"})  # Upgrade the model name to dall-e-3
image_params.update({"size": "1792x1024"})  # 1792x1024 or 1024x1792 available for DALL-E 3
image_params.update({"size": "1024x1792"})  # 1792x1024 or 1024x1792 available for DALL-E 3
image_params.update({"quality": "hd"})      # quality at 2x the price, defaults to "standard" 
#image_params.update({"style": "natural"})   # defaults to "vivid"

# ---- START
try:
    images_response = client.images.generate(**image_params)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    raise

# make a file name prefix from date-time of response
from datetime import datetime, timezone

images_dt = datetime.fromtimestamp(images_response.created, timezone.utc)
img_filename = images_dt.strftime('DALLE-%Y%m%d_%H%M%S')  # like 'DALLE-20231111_144356'

# get the prompt used if rewritten by dall-e-3, null if unchanged by AI
revised_prompt = images_response.data[0].revised_prompt
print(revised_prompt)


image_data_list = []


for image in images_response.data:
    assert image.b64_json, "No image data was returned"
    image_data_list.append(image.model_dump()["b64_json"])

# Initialize an empty list to store the Image objects
image_objects = []

assert image_data_list and all(image_data_list), "No image data was obtained. Maybe bad code?"
# Convert "b64_json" data to png file
for i, data in enumerate(image_data_list):
    image_objects.append(Image.open(BytesIO(base64.b64decode(data))))  # Append the Image object to the list
    image_objects[i].save(f"{img_filename}_{i}.png")
    print(f"{img_filename}_{i}.png was saved")

# ---- END