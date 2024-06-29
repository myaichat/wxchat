# pip install bitsandbytes accelerate
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(load_in_8bit=True)

tokenizer = AutoTokenizer.from_pretrained("google/gemma-2-9b-it")
model = AutoModelForCausalLM.from_pretrained(
    "google/gemma-2-9b-it",
    device_map="auto",
    cache_dir="./cache",
    quantization_config=quantization_config
)

input_text = "Write a function that checks if a year is a leap year. no explanation needed"
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

# Initial context
generated_ids = input_ids['input_ids']

# Stream output
for _ in range(100):  # Adjust the range for desired length
    outputs = model.generate(
        generated_ids,
        max_new_tokens=1,  # Generate one token at a time
        do_sample=True,    # Use sampling to introduce variability
        temperature=0.7,   # Control the randomness
    )
    
    # Get the new token
    new_token_id = outputs[:, -1].unsqueeze(0)
    generated_ids = torch.cat((generated_ids, new_token_id), dim=1)
    
    # Decode and print the new token
    new_token = tokenizer.decode(new_token_id[0])
    print(new_token, end='', flush=True)

print()  # For newline at the end of output
