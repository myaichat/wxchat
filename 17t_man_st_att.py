from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import time

class ManualStreamer:
    def __init__(self, tokenizer, skip_special_tokens=True):
        self.tokenizer = tokenizer
        self.skip_special_tokens = skip_special_tokens
        self.generated_text = ""

    def stream(self, input_ids, attention_mask, model, max_new_tokens=100, temperature=1.0, top_p=0.95, top_k=50):
        generated_ids = input_ids
        generated_attention_mask = attention_mask
        for _ in range(max_new_tokens):
            outputs = model.generate(
                input_ids=generated_ids,
                attention_mask=generated_attention_mask,
                do_sample=True,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_new_tokens=1,
                pad_token_id=self.tokenizer.eos_token_id
            )
            next_token_id = outputs[:, -1:]
            generated_ids = torch.cat((generated_ids, next_token_id), dim=1)
            next_token = self.tokenizer.decode(next_token_id.squeeze(), skip_special_tokens=self.skip_special_tokens)
            self.generated_text += next_token
            print(next_token, end='', flush=True)  # Print each chunk of text as it is generated

            # Update the attention mask to include the new token
            new_attention_mask = torch.ones((attention_mask.size(0), 1), device=attention_mask.device)
            generated_attention_mask = torch.cat((generated_attention_mask, new_attention_mask), dim=1)

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

# Initialize manual streamer
streamer = ManualStreamer(tokenizer, skip_special_tokens=True)

# Generate output with parameters manually
print("Starting generation")
streamer.stream(input_ids, attention_mask, model, max_new_tokens=300, temperature=1.0, top_p=0.95, top_k=50)
print("\nGeneration finished")

# Print the full generated text at the end
print("\n\nGenerated Text:", streamer.generated_text)

# Print the time taken
print("\nTime:", time.time() - start)
