# python3
# please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI

DEEPSEEK_API_KEY= os.getenv("DEEPSEEK_API_KEY")

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-coder",
    messages=[
        #{"role": "system", "content": "You are a wxPython expert"},
        #{"role": "user", "content": "write a wxPython app to display hello world"},
        {"role": "system", "content": "You have perfect artistic sense and pay great attention to detail which makes you an expert at describing images"},
        {"role": "user", "content": """

        You have perfect artistic sense and pay great attention to detail which makes you an expert at describing images.
        Your job is to imagine and describe in detail a single image that fuses 
        elements from all the provided image descriptions. 
        Focus on how the elements from each image interact and blend together. 
        Be specific about colors, shapes, textures, and composition. 
        Your description should be cohesive, as if describing a real painting or photograph that fuses these elements.
        Image_1:
         
The image presents a surreal fusion of human and flora, where the subject seems to embody sunflowers. The person is positioned in such as way that they appear part-human with large flowers for shoulders blades or possibly wings made up from petals unfurling at their skin's edges into bloom-like formations covering her arms. A headpiece adorning multiple shades like green-yellow-white mimics daisy chains on toppling together creating an organic halo above this figure/flower hybrid; its leaves are lushly intertwined throughout what appears both hairline-to-limb. Her left leg rests lightly upon some dried wood pieces against white peeling walls adding texture - she stands balanced precariously by one foot near chipping painted areas suggestive perhaps once more vivid colors before fading away leaving them cracked now much bleached out Intricate shadows across legs suggest further depth suggesting light source low thus accentuating details all around within scene yet still retains essence so harmonious
         

        Before providing the final description in <fused_image> tags, think through your process step-by-step in <thinking> tags. 
        add pinup art essence , make it visually stunning.
         
         
         """},        
        
    ],
    stream=True
)

for chunk in response:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="")
