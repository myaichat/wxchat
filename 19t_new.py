from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import time

# Start the timer
start = time.time()

# Model ID
model_id = "google/gemma-2-9b-it"
# model_id = "google/gemma-2-27b-it"

# Load tokenizer and model
print("Loading tokenizer and model")
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    cache_dir="./cache",
    trust_remote_code=True,
    low_cpu_mem_usage=True,
    attn_implementation="flash_attention_2"
)
print("Tokenizer and model loaded")

# Prepare input text
input_text = "Write a function that checks if a year is a leap year. Just code, no explanation needed."
inputs = tokenizer(input_text, return_tensors="pt").to("cuda")
input_ids = inputs['input_ids']
attention_mask = inputs['attention_mask']

generated_text = ""
for _ in range(100):  # Generate up to 100 new tokens
    outputs = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=1,
        do_sample=True,
        temperature=1.2,  # Increase temperature for more diversity
        top_p=0.9,        # Nucleus sampling
        top_k=40,         # Limiting to top_k choices for more diverse output
        pad_token_id=tokenizer.eos_token_id
    )
    next_token_id = outputs[:, -1:]
    input_ids = torch.cat((input_ids, next_token_id), dim=1)
    
    # Update the attention mask to include the new token
    attention_mask = torch.cat((attention_mask, torch.ones((attention_mask.size(0), 1), device=attention_mask.device)), dim=1)
    
    next_token = tokenizer.decode(next_token_id.squeeze(), skip_special_tokens=True)
    generated_text += next_token
    print(next_token, end='', flush=True)  # Print each token as it is generated

print("\nGeneration finished")

# Print the full generated text at the end
print("\n\nGenerated Text:", generated_text)

# Print the time taken
print("\nTime:", time.time() - start)
