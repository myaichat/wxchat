from openai import OpenAI

# Create an OpenAI client with your Deepinfra token and endpoint
openai = OpenAI(
    api_key="9oTWofT85PhzE7d7ZsX5gas1VBUo1zd3",
    base_url="https://api.deepinfra.com/v1/openai",
)

chat_completion = openai.chat.completions.create(
    model="Gryphe/MythoMax-L2-13b",
    messages=[
        {
            "role": "system",
            "content": """
You possess a perfect artistic sense and pay great attention to detail, making you an expert at describing images. 
Create an amazing image prompt. Be as creative and weird as possible. Add a pinup essence. 
Provide the answer within <fused_image> tags.
            """
        },
        {
            "role": "user",
            "content": """
Use this as inspiration: A surreal scene featuring a Ukrainian woman with long blonde hair, wearing a military camouflage bikini and holding a rifle, with a Ukrainian theme. She stands in a desert-like environment with a large, swirling vortex in the background. The woman appears distressed, with wide eyes and an open mouth as if screaming. The vortex is bright orange and yellow, resembling a tornado or whirlpool. Her hair blows in the wind, and the background is filled with blue and orange hues, creating a chaotic and intense atmosphere. Elements of Ukrainian culture are incorporated, such as traditional Ukrainian patterns on her bikini, a Ukrainian flag patch on her rifle, and the swirling vortex featuring shades of blue and yellow. The overall mood is dramatic and urgent.
            """
        }
    ],
    stream=True,
    temperature=1.0,
    top_p=1.0,
)

for event in chat_completion:
    if event.choices[0].delta.content:
        print(event.choices[0].delta.content, end="")
