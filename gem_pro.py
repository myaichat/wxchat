#
# https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_pro_vision_python.ipynb
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
from vertexai.generative_models import (
    GenerativeModel,
    Image,
    Part,
)

from google.cloud import aiplatform
from google.api_core.exceptions import GoogleAPICallError


def list_models(project_id, location):
    try:
        client = aiplatform.gapic.ModelServiceClient(client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"})
        parent = f"projects/{project_id}/locations/{location}"
        response = client.list_models(parent=parent)
        print("Raw response:", response)  # Print raw response to debug

        if not response.models:
            print("No models found.")
            return

        for model in response.models:
            print("Model name:", model.name)
            print("Model display name:", model.display_name)
            print("Model description:", model.description)
            # Add more fields as needed
    except GoogleAPICallError as e:
        print(f"Failed to list models: {e}")
project_id = PROJECT_ID
location = "us-central1"  # or other region
list_models(project_id, location)
