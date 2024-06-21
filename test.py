#
#https://github.com/GoogleCloudPlatform/generative-ai/blob/main/vision/getting-started/visual_question_answering.ipynb
#
import sys
e=sys.exit
# Define project information
PROJECT_ID = "spatial-flag-427113-n0"  # @param {type:"string"}
LOCATION = "us-central1"  # @param {type:"string"}

# Initialize Vertex AI
import vertexai
#from google.colab import auth
#auth.authenticate_user()
vertexai.init(project=PROJECT_ID, location=LOCATION)
from vertexai.preview.vision_models import ImageQnAModel, ImageTextModel, ImageCaptioningModel

image_qna_model = ImageQnAModel.from_pretrained("imagetext@001")

from vertexai.preview.vision_models import Image

import os
import requests


def download_image(url: str) -> str:
    """Downloads an image from the specified URL."""

    # Send a get request to the url
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Failed to download image from {url}")

    # Define image related variables
    image_path = os.path.basename(url)
    image_bytes = response.content
    image_type = response.headers["Content-Type"]

    # Check for image type, currently only PNG or JPEG format are supported
    if image_type not in {"image/png", "image/jpeg"}:
        raise ValueError("Image can only be in PNG or JPEG format")

    # Write image data to a file
    with open(image_path, "wb") as f:
        f.write(image_bytes)
    return image_path

# Download an image
if 0:
    url = "https://storage.googleapis.com/gweb-cloudblog-publish/images/GettyImages-871168786.max-2600x2600.jpg"
    image_path = download_image(url)
else:
    image_path='GettyImages-871168786.max-2600x2600.jpg'
print(image_path)
user_image = Image.load_from_file(image_path)
#user_image.show()
# Ask a question about the image
if 0:
    model = ImageTextModel.from_pretrained("imagetext@001")
    image = Image.load_from_file("GettyImages-871168786.max-2600x2600.jpg")

    captions = model.get_captions(
        image=user_image,
        # Optional:
        number_of_results=1,
        language="en",
    )
    print(captions)


model = ImageCaptioningModel.from_pretrained("imagetext@001")
image = Image.load_from_file("GettyImages-871168786.max-2600x2600.jpg")
captions = model.get_captions(
    image=image,
    # Optional:
    number_of_results=1,
    language="en",
)
print(captions)
e()
result=image_qna_model.ask_question(
    image=user_image,
    question="give detailed description of the image",
    number_of_results=1,
)
print(result)