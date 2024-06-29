from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch
import time

start = time.time()
model_id = "google/gemma-2-9b-it"
# model_id = "google/gemma-2-27b-it"
dtype = torch.bfloat16

tokenizer = AutoTokenizer.from_pretrained(model_id)
print("tokenizer:", time.time() - start)

quantization_config = BitsAndBytesConfig(load_in_4bit=True)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=quantization_config,
    device_map="auto",
    cache_dir="./cache",
    torch_dtype=dtype,
    attn_implementation="flash_attention_2"
)
print("model:", time.time() - start)

chat = [
    {"role": "user", "content": "short List major python versions. Index answer"},
    {"role": "assistant", "content": """Here are some major Python versions, indexed:

0. **Python 2.x** (Legacy, End-of-Life)
1. **Python 3.0** (Major rewrite, introduced many changes)
2. **Python 3.1** - **Python 3.9** (Ongoing development, with incremental improvements and bug fixes)
3. **Python 3.10** (Latest stable release as of October 2023)

Let me know if you'd like more details about a specific version!"""},
    {"role": "user", "content": "Tell me more about option 0"},
]

prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt").to(model.device)

# Initialize an empty list to collect generated tokens
generated_tokens = inputs

# Set the maximum number of tokens to generate and the batch size
max_new_tokens = 2000
batch_size = 10

for _ in range(max_new_tokens // batch_size):
    with torch.no_grad():
        output = model(input_ids=generated_tokens)
    
    # Get the next batch of tokens
    next_tokens = output.logits[:, -1, :].argmax(dim=-1).unsqueeze(0)
    
    # Append new tokens to the generated tokens list
    generated_tokens = torch.cat([generated_tokens, next_tokens], dim=-1)
    
    # Decode and print the new tokens
    new_text = tokenizer.decode(next_tokens[0], skip_special_tokens=True)
    print(new_text, end="", flush=True)
    
    # Check if we've reached the end of generation
    if next_tokens[0].item() == tokenizer.eos_token_id:
        break

# Decode and print the total generated text
total_generated_text = tokenizer.decode(generated_tokens[0], skip_special_tokens=True)
#print("\nGenerated text:", total_generated_text)
print("Total time:", time.time() - start)
