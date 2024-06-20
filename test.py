from transformers import AutoModelForCausalLM, AutoTokenizer , BitsAndBytesConfig
#import torch
from PIL import Image 
import sys
e=sys.exit
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    quantization_method="fp4",  # or another appropriate method
)

model = AutoModelForCausalLM.from_pretrained(
    "openbmb/MiniCPM-Llama3-V-2_5-int4", 
    cache_dir="./cache2",
    trust_remote_code=True,
    quantization_config=bnb_config,
    low_cpu_mem_usage=True
) #.to("cuda")

#print(next(model.parameters()).is_cuda)
#e()
tokenizer = AutoTokenizer.from_pretrained(
    "openbmb/MiniCPM-Llama3-V-2_5-int4",
    cache_dir="./cache2", 
    trust_remote_code=True
)
image = Image.open("Art\\0_1.png")

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