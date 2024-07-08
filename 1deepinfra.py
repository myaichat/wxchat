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
         A captivating, panoramic image featuring a fierce Ukrainian female figure striking a powerful pose. She wears a traditional vyshyvanka dress flowing gracefully as she strides forward, gripping dual pistols tightly. The upper portion of the image showcases a surreal backdrop of brightly illuminated, floating shattered mirrors, each reflecting different aspects of her identity and the intricate details of her dress. This symbolizes societal pressures and the strength of female identity. The lower portion transitions into a chaotic landscape of fragmented shapes, reminiscent of abstract expressionism. The central figure is rendered with photorealistic precision, her long dark hair whipping in an unseen wind, and her face displaying a determined expression as she focuses on an unseen target. A web of splatters, drips, and textures unifies the realistic and abstract elements, giving the piece a raw, street art aesthetic. The background is a tempestuous sea of blue and yellow, evoking the colors of the Ukrainian flag, with vibrant yellow splashes cutting through azure swathes like lightning bolts. As the light fades into twilight, an ethereal Ukrainian spiritess emerges from the shadows, her ghostly apparition floating effortlessly over the desolate landscape. The magical transition between day and night is captured in the subtle shifts of color and light, with wildflowers bursting forth in a riot of colors against the darkening backdrop of the evening sky. The spiritess's form is semi-transparent, allowing the viewer to glimpse the intricate patterns of her traditional Ukrainian attire and the stories told by the wildflowers beneath her. The overall effect symbolizes strength, resilience, and the fusion of traditional and modern elements in Ukrainian culture.

Please create a vivid, detailed description of a single imaginary image that combines elements from all of these descriptions. 
Focus on how the elements from each description interact and blend together. 
Be specific about colors, shapes, textures, and composition. 
Your description should be cohesive, as if describing a real painting or photograph that fuses these elements.

Before Providing the final description in <fused_prompt> tag, list weights of each emage use used in description and short info about it in <weights> tags. .
Do not mention weights in fused_prompt.         


"""}], stream =True
)
if 0:
    print(chat_completion.choices[0].message.content)
    print(chat_completion.usage.prompt_tokens, chat_completion.usage.completion_tokens)


for chunk in chat_completion:
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")

