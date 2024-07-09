

from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "***"
)

completion = client.chat.completions.create(
  model="meta/llama3-70b-instruct",
  messages=[{"role":"user","content":"""
You have perfect artistic sence and pay great attention to detail which makes you an expert at describing images.        
Provide the answer in <fused_image> tags.             
Write image prompt using this as inspiration, be as artistic and as wierd as possible. add ukrainian essence to it:
Craft a wide, 16:9 HD and vivid interpretation of the Ukrainian pinup concept, with a strong focus on brightness and clarity. In this panoramic view, the Ukrainian female figure strikes a captivating pinup pose, adorned with a traditional flower crown and vyshyvanka dress, against a surreal backdrop. The landscape is alive with brightly illuminated, floating shattered mirrors, each reflecting different aspects of her identity and the intricate details of her dress. This scene not only embraces the pinup aesthetic but also incorporates a modern twist through the symbolism of the mirrors, which reflect the societal pressures and the strength and complexity of female identity. The combination of traditional Ukrainian elements with the bold, expressive qualities of pinup art creates a striking visual statement, challenging conventional beauty standards and celebrating empowerment.
"""}],
  temperature=0.5,
  top_p=1,
  max_tokens=512,
  stream=True
)

for chunk in completion:
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")
