from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import TextStreamer
import torch
import time

class CustomTextStreamer(TextStreamer):
    def __init__(self, tokenizer, skip_special_tokens=True):
        super().__init__(tokenizer, skip_special_tokens)
        self.generated_text = ""

    def __call__(self, token_ids, **kwargs):
        # Decode the token ids and append to the generated text
        text = self.tokenizer.decode(token_ids, skip_special_tokens=self.skip_special_tokens)
        self.generated_text += text
        print(text, end='', flush=True)  # Print each chunk of text

# Start the timer
start = time.time()

# Model ID
model_id="google/gemma-2-9b-it"
#model_id = "google/gemma-2-27b-it"

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    cache_dir="./cache",
    trust_remote_code=True ,
    low_cpu_mem_usage=True
)

# Prepare input text
input_text = "Write me a poem about Machine Learning."
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

# Initialize custom streamer
streamer = CustomTextStreamer(tokenizer, skip_special_tokens=True)

# Generate output with parameters
_ = model.generate(
    input_ids['input_ids'],
    max_new_tokens=100,
    do_sample=True,
    temperature=1.0,
    top_p=0.95,      # Nucleus sampling
    top_k=50,         # Limiting to top_k choices
    streamer=streamer
)

# Print the full generated text at the end
print("\n\nGenerated Text:", streamer.generated_text)

# Print the time taken
print("\nTime:", time.time() - start)
