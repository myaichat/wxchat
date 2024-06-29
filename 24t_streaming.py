# pip install bitsandbytes accelerate
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch

quantization_config = BitsAndBytesConfig(load_in_8bit=True)

tokenizer = AutoTokenizer.from_pretrained("google/gemma-2-9b-it")
model = AutoModelForCausalLM.from_pretrained(
    "google/gemma-2-9b-it",
    device_map="auto",
    cache_dir="./cache",    
    quantization_config=quantization_config)

input_text = "Write a function that checks if a year is a leap year. no explanation needed"
input_ids = tokenizer.encode(input_text, return_tensors="pt").to("cuda")

def generate_with_streaming(input_ids, tokenizer, model, max_length=1000, num_return_sequences=1):
    generated_tokens = []
    current_ids = input_ids.clone()
    with torch.no_grad():
        for _ in range(max_length):
            outputs = model(current_ids)
            next_token_logits = outputs.logits[:, -1, :]
            next_token_id = torch.argmax(next_token_logits, dim=-1)
            if next_token_id == tokenizer.eos_token_id:
                break
            generated_tokens.append(next_token_id.item())
            current_ids = torch.cat((current_ids, next_token_id.unsqueeze(0)), dim=-1)
            decoded_output = tokenizer.decode(generated_tokens, skip_special_tokens=True)
            print(decoded_output, end="\r", flush=True)
    print()
    return generated_tokens

generated_tokens = generate_with_streaming(input_ids, tokenizer, model)
decoded_output = tokenizer.decode(generated_tokens, skip_special_tokens=True)
print(decoded_output)