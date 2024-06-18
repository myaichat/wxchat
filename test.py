from transformers import AutoModelForCausalLM, AutoTokenizer 
#import torch
from PIL import Image 

model = AutoModelForCausalLM.from_pretrained(
    "openbmb/MiniCPM-Llama3-V-2_5", 
    trust_remote_code=True
).to("cuda")
tokenizer = AutoTokenizer.from_pretrained(
    "openbmb/MiniCPM-Llama3-V-2_5", 
    trust_remote_code=True
)
image = Image.open("Art\\0_1.jpg")

while True:
    question = input("Ask a question: ")
    if not question:
        
        prompt = "What is the main object shown in the image?"
    chat = model.chat(
        image=image, 
        #question=prompt, 
        tokenizer=tokenizer,
        generate_args={"temperature": 0.8},
        msgs = [
        {"role": "user", "content": question}
    ]
    )

    print(chat)