import os
from openai import OpenAI

# Create an OpenAI client with your deepinfra token and endpoint
openai = OpenAI(
    api_key=os.getenv("DEEPINFRA_API_KEY"),
    base_url="https://api.deepinfra.com/v1/openai",
)

chat_completion = openai.chat.completions.create(
    model="Qwen/Qwen2-72B-Instruct",
    messages=[
        {"role": "system", "content": "You have perfect artistic sense and pay great attention to detail which makes you an expert at generating image and art prompts"},
        {"role": "user", "content": """
I want you to imagine and describe in detail a single image that fuses elements from multiple image descriptions. 
Here are the descriptions of the input images:

Prompt_1:
        A surreal scene featuring a Ukrainian woman with long blonde hair, wearing a military camouflage bikini and holding a rifle, with a Ukrainian theme. She stands in a desert-like environment with a large, swirling vortex in the background. The woman appears distressed, with wide eyes and an open mouth as if screaming. The vortex is bright orange and yellow, resembling a tornado or whirlpool. Her hair blows in the wind, and the background is filled with blue and orange hues, creating a chaotic and intense atmosphere. Elements of Ukrainian culture are incorporated, such as traditional Ukrainian patterns on her bikini, a Ukrainian flag patch on her rifle, and the swirling vortex featuring shades of blue and yellow. The overall mood is dramatic and urgent.

Please create a vivid, detailed description of a single imaginary image that combines elements from all of these descriptions. 
Focus on how the elements from each description interact and blend together. 
Be specific about colors, shapes, textures, and composition. 
Your description should be cohesive, as if describing a real painting or photograph that fuses these elements.

         Add ukrainian essence to the image.     


"""}], stream =True,
temperature=1.0,
max_tokens=500,
top_p=1.0,
n=1,
stop=None,
presence_penalty=0.5, #Positive values penalize new tokens based on whether they appear in the text so far,
# increasing the model's likelihood to talk about new topics.
#-2 ≤ presence_penalty ≤ 2
frequency_penalty=0.5, #Positive values penalize new tokens based on how many times they appear in the text so far, 
# increasing the model's likelihood to talk about new topics.
#-2 ≤ frequency_penalty ≤ 2
#repetition_penalty=1.0, #(> 1 penalize, < 1 encourage)
)
if 0:
    print(chat_completion.choices[0].message.content)
    print(chat_completion.usage.prompt_tokens, chat_completion.usage.completion_tokens)


for chunk in chat_completion:
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")
