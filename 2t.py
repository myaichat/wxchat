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
msgs = []
system_prompt = 'Answer in detail.'
prompt = 'Caption this two images'
tgt_path = ['Art\\0_1.png', 'Art\\0_1.jpg']
if system_prompt: 
    msgs.append(dict(type='text', value=system_prompt))
if isinstance(tgt_path, list):
    msgs.extend([dict(type='image', value=p) for p in tgt_path])
else:
    msgs = [dict(type='image', value=tgt_path)]
msgs.append(dict(type='text', value=prompt))

content = []
for x in msgs:
    if x['type'] == 'text':
        content.append(x['value'])
    elif x['type'] == 'image':
        image = Image.open(x['value']).convert('RGB')
        content.append(image)
msgs = [{'role': 'user', 'content': content}]

while True:
    question = input("Ask a question: ")
    if not question:
        
        prompt = "What is the main object shown in the image?"


    chat = model.chat(
        msgs=msgs,
        context=None,
        image=None,
        tokenizer=tokenizer,
        sampling=True,
        temperature=0.8,    
    )
    

    print(chat)

