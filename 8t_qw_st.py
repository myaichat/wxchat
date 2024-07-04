import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Set the device
device = "cuda" if torch.cuda.is_available() else "cpu"

# Load the model
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2-7B-Instruct",
    torch_dtype=torch.float16,
    device_map='auto',
    cache_dir='./cache',
)

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-7B-Instruct")

# Define the prompt
prompt = "Give me a short introduction to large language model."

# Tokenize the prompt
input_text = tokenizer(prompt, return_tensors='pt').to(device)

# Initialize variables
generated_text = ""
input_ids = input_text.input_ids

# Generate text token by token
for token_id in model.generate(input_ids, max_new_tokens=512):
    # Decode the token to text
    token_text = tokenizer.decode(token_id, skip_special_tokens=True)
    # Append the token to the generated text
    generated_text += token_text

    # Print the token as it is generated
    print(token_text, end='', flush=True)
    
print("\nFinished generating text.")