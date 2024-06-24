import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession

# Initialize Vertex AI with your project ID and location
# TODO(developer): Update and un-comment below line with your actual project ID
# project_id = "PROJECT_ID"

PROJECT_ID = "spatial-flag-427113-n0"
LOCATION="us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Instantiate the generative model
model = GenerativeModel(model_name="gemini-1.5-flash-001")

# Start a chat session
chat = model.start_chat()

# Function to get chat response
def get_chat_response(chat: ChatSession, prompt: str) -> str:
    text_response = []
    responses = chat.send_message(prompt, stream=True)
    for chunk in responses:
        text_response.append(chunk.text)
    return "".join(text_response)

# Sending prompts and printing responses
prompt = "Hello."
print(get_chat_response(chat, prompt))

prompt = "What are all the colors in a rainbow?"
print(get_chat_response(chat, prompt))

prompt = "what di i just ask u about?"
print(get_chat_response(chat, prompt))