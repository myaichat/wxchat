from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
import torch
import time
from threading import Thread

class CustomStreamer(TextIteratorStreamer):
    def __init__(self, tokenizer, skip_special_tokens=False, custom_function=None):
        super().__init__(tokenizer, skip_special_tokens)
        self.custom_function = custom_function

    def on_finalized_text(self, text):
        print(text.upper(), end="", flush=True)

def custom_function(text):
    # Apply your custom processing here
    return text.upper()  # Example: convert to uppercase

start = time.time()

# Load the model and tokenizer
model_name = "PygmalionAI/mythalion-13b"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name, 
    torch_dtype=torch.float16, 
    device_map="auto",
    cache_dir="./cache",
    trust_remote_code=True,
    low_cpu_mem_usage=True,
    attn_implementation="flash_attention_2"
)

# Prepare the input text
input_text = """
### Instruction:
Create amazing detailed image description infused with Ukrainian essence like this: "1950s Pinup Girl inspired by the Wildflowers of Ukraine's Summer Fields.The vibrant bouquet of blue and yellow wildflowers adorns the beauty's long,"
Do not give image references. do not use html. Do not use special characters. Do not use emojis. Do not use urls. Do not use any other language than English. Do not return detailed description in <fused_image> tags.
### Response:
"""

# Tokenize the input
inputs = tokenizer(input_text, return_tensors="pt")
input_ids = inputs["input_ids"].to(model.device)
attention_mask = inputs["attention_mask"].to(model.device)

streamer = CustomStreamer(tokenizer, skip_special_tokens=True, custom_function=custom_function)

# Generate text using streaming
generation_kwargs = dict(
    input_ids=input_ids,
    max_length=1000,
    min_length=500,
    num_return_sequences=1,
    no_repeat_ngram_size=2,
    temperature=1.4,
    top_k=150,
    top_p=0.95,
    do_sample=True,
    pad_token_id=tokenizer.eos_token_id,
    attention_mask=attention_mask,
    streamer=streamer
)

print("\nStreaming:", time.time() - start)

# Run the generation in a separate thread
thread = Thread(target=model.generate, kwargs=generation_kwargs)
thread.start()

# Wait for the generation to complete
thread.join()

print("\nTotal:", time.time() - start)