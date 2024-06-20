from transformers import AutoModelForCausalLM, AutoTokenizer 
#import torch
from PIL import Image 

model = AutoModelForCausalLM.from_pretrained(
    "openbmb/MiniCPM-Llama3-V-2_5", 
    cache_dir="./cache",
    trust_remote_code=True
).to("cuda")

tokenizer = AutoTokenizer.from_pretrained(
    "openbmb/MiniCPM-Llama3-V-2_5", 
    cache_dir="./cache",
    trust_remote_code=True
)
msgs = []
system_prompt = 'Answer in detail.'
prompt = 'Caption this two images'
tgt_path = [
    'Art\\0_3.jpeg',
    'Art\\0_1.png',
   # 'Art\\0_2.png',
    
    ]
if system_prompt: 
    msgs.append(dict(type='text', value=system_prompt))
if isinstance(tgt_path, list):
    msgs.extend([dict(type='image', value=p) for p in tgt_path])
else:
    msgs = [dict(type='image', value=tgt_path)]


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
        vision_hidden_states=None,
        max_new_tokens=1024,
        min_new_tokens=512,
        top_p= 0.8,
        top_k= 100,
        
        do_sample= True,
        repetition_penalty= 1.05,        
        sampling=True,
        max_inp_length=2048,        
        temperature=1.0  
    )
    

    print(chat)

