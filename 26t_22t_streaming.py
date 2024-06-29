# pip install accelerate
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch

model_id = "google/gemma-2-9b-it"

tokenizer = AutoTokenizer.from_pretrained(model_id)

quantization_config = BitsAndBytesConfig(load_in_8bit=True)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    #quantization_config=quantization_config,
    device_map="auto",
    cache_dir="./cache",
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2"    
)

input_text = "Write a function that checks if a year is a leap year. no explanation needed."
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

# Function to generate text and stream output
def generate_and_stream(input_ids, max_length=100, batch_size=5):
    generated_ids = input_ids['input_ids']
    
    for _ in range(0, max_length, batch_size):
        # Generate the next batch of tokens
        outputs = model.generate(
            generated_ids,
            max_new_tokens=batch_size, 
            do_sample=True,
            temperature=1.0,
            top_p=0.95,      # Nucleus sampling
            top_k=50        # Limiting to top_k choices
        )
        
        # Extract the new tokens
        new_token_ids = outputs[:, -batch_size:]
        generated_ids = torch.cat((generated_ids, new_token_ids), dim=1)
        
        # Decode and print each new token
        new_tokens = tokenizer.decode(new_token_ids[0], skip_special_tokens=True)
        print(new_tokens, end='', flush=True)
        
        # Break if the end of sequence token is generated
        if tokenizer.eos_token_id in new_token_ids:
            break

# Stream the generated text
generate_and_stream(input_ids)
