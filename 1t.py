# python3
# please install OpenAI SDK first: `pip3 install openai`
from openai import OpenAI

client = OpenAI(api_key="sk-b15f8e97c01d4d0ab11a53d23a63188a", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-coder",
    messages=[
        {"role": "system", "content": "You are wxpython expert"},
        {"role": "user", "content": "write wxpython app to display hello world"},
    ],
    stream=True
)

print(response.choices[0].message.content)