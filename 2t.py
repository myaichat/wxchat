import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

print(torch.cuda.is_available())

model_id = "Gryphe/MythoMax-L2-13b"
#model = AutoModelForCausalLM.from_pretrained(model_id, cache_dir="./cache", trust_remote_code=True).cuda()
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    cache_dir="./cache",
    trust_remote_code=True, #,
    low_cpu_mem_usage=True,
    attn_implementation="flash_attention_2"
).cuda()


# Define the prompt
prompt = "What's the capital of france?"

# Tokenize the prompt, automatically add attention mask
inputs = tokenizer(prompt, return_tensors="pt",  padding=True, truncation=True).to('cuda')

terminators = [
    tokenizer.eos_token_id,
    #tokenizer.convert_tokens_to_ids("50256")
]

# Move tokenized inputs to GPU
inputs = {k: v.to('cuda') for k, v in inputs.items()}

# Generate text
output = model.generate(**inputs, 
    max_length=50,  # Adjust based on desired response length
    num_return_sequences=1,
    do_sample=True,
    temperature=0.5, top_p=0.65,
    eos_token_id=terminators,
    top_k=50,  # Limits the possibilities for randomness
    #top_p=0.9  # Ensures focus in generation
    )

# Decode and print the generated text
generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
print(123,generated_text)