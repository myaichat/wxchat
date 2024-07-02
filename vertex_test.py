#
#https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/configure-safety-attributes
#

import vertexai

from vertexai.generative_models import (
    GenerativeModel,
    Image,
    Part,
)

from vertexai import generative_models

# TODO(developer): Update and un-comment below line
# project_id = "PROJECT_ID"

PROJECT_ID = "spatial-flag-427113-n0"  # @param {type:"string"}
LOCATION = "us-central1"  # @param {type:"string"}

vertexai.init(project=PROJECT_ID, location=LOCATION)

model = generative_models.GenerativeModel(model_name="gemini-1.5-flash-001")

# Generation config
generation_config = generative_models.GenerationConfig(
    max_output_tokens=2048, temperature=0.4, top_p=1, top_k=32
)

# Safety config
safety_config = [
    generative_models.SafetySetting(
        category=generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=generative_models.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    ),
    generative_models.SafetySetting(
        category=generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=generative_models.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    ),
]

image_file = Part.from_uri(
    "gs://cloud-samples-data/generative-ai/image/scones.jpg", "image/jpeg"
)

# Generate content
responses = model.generate_content(
    [image_file, "What is in this image?"],
    generation_config=generation_config,
    safety_settings=safety_config,
    stream=True,
)

text_responses = []
for response in responses:
    print(response.text)
    text_responses.append(response.text)