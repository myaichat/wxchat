import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# Check if CUDA is available
print(torch.cuda.is_available())

# Define model ID
model_id = "Gryphe/MythoMax-L2-13b"

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Load the model with optimized settings
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    cache_dir="./cache",
    trust_remote_code=True,
    low_cpu_mem_usage=True,
    attn_implementation="flash_attention_2"
).cuda()

# Define a text generation pipeline without specifying the device
generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer
)

# Function to generate text
def stream_text(prompt, max_length=300, temperature=1.2, top_p=0.9):
    results = generator(prompt, max_length=max_length,min_length=200, temperature=temperature, top_p=top_p, return_full_text=True)
    for result in results:
        # Get the generated text
        generated_text = result['generated_text'] if isinstance(result, dict) else result
        # Print the generated text
        print(generated_text)

# Example usage
prompt = "In this image In the midst of twilight, a Ukrainian female warrior stand before a magnificent Ukrainian Tryzub sculpture "
stream_text(prompt)
