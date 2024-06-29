from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import transformers
import torch
import time
start= time.time()
model_id = "google/gemma-2-9b-it"
dtype = torch.bfloat16

tokenizer = AutoTokenizer.from_pretrained(model_id)
print("tokenizer:", time.time() - start)

quantization_config = BitsAndBytesConfig(load_in_8bit=True)


model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=quantization_config,
    device_map="cuda",
    cache_dir="./cache",
    torch_dtype=dtype,
    #attn_implementation="flash_attention_2"
    )
print("model:", time.time() - start)
chat = [
    { "role": "user", "content": "Write a function that checks if a year is a leap year. no explanation needed." },
]
if 1:
    prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")
    outputs = model.generate(input_ids=inputs.to(model.device), max_new_tokens=500)
    print(tokenizer.decode(outputs[0]))
    print("Total:", time.time() - start)
