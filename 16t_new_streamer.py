from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import TextIteratorStreamer
import torch
import time
from threading import Thread

class CustomTextStreamer(TextIteratorStreamer):
    def __init__(self, tokenizer, skip_special_tokens=True):
        super().__init__(tokenizer, skip_special_tokens)
        self.generated_text = ""
        print("CustomTextStreamer initialized")

    def on_finalized_text(self, text: str, stream_end: bool = False):
        #print("CustomTextStreamer on_finalized_text invoked")
        # Remove special tokens from the end of the text
        #text = text.replace("<end_of_turn>", "").replace("<eos>", "").strip()
        if 1:
            self.generated_text += text
            print(text, end='', flush=True)  # Print each chunk of text

# Start the timer
start = time.time()

# Model ID
model_id = "google/gemma-2-9b-it"
#model_id = "google/gemma-2-27b-it"

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
inputs = tokenizer(input_text, return_tensors="pt", padding=True)

# Explicitly create the attention mask
attention_mask = torch.ones_like(inputs['input_ids'])

# Move inputs to CUDA
inputs = {k: v.to("cuda") for k, v in inputs.items()}
attention_mask = attention_mask.to("cuda")

# Initialize custom streamer
streamer = CustomTextStreamer(tokenizer, skip_special_tokens=True)

# Generate output with parameters
print("Starting generation")
generation_kwargs = dict(
    input_ids=inputs['input_ids'],
    attention_mask=attention_mask,
    max_new_tokens=100,
    do_sample=True,
    temperature=1.0,
    top_p=0.95,      # Nucleus sampling
    top_k=50,        # Limiting to top_k choices
    streamer=streamer
)

thread = Thread(target=model.generate, kwargs=generation_kwargs)
thread.start()

# Iterate over the generated text
for text in streamer:
    print(123)
    pass  # The printing is handled in on_finalized_text

thread.join()
print("\nGeneration finished")

# Print the full generated text at the end
print("\n\nGenerated Text:", streamer.generated_text)

# Print the time taken
print("\nTime:", time.time() - start)