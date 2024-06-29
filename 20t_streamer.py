import asyncio
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
import torch
import time

start = time.time()
model_id = "google/gemma-2-27b-it"
# model_id = "google/gemma-2-9b-it"  # Comment out this line to avoid reassigning model_id

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

input_text = "Write a function that checks if a year is a leap year. Just code, no explanation needed."
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

# Set up the streamer
streamer = TextIteratorStreamer(tokenizer)

async def generate_text():
    await model.generate(
        **input_ids,
        streamer=streamer,
        max_new_tokens=100,  # Adjust as needed
        do_sample=True  # Disable sampling to get deterministic output
    )

async def print_stream():
    async for new_text in streamer:
        print(new_text, end='', flush=True)

# Create an event loop
loop = asyncio.get_event_loop()

# Run the generation and printing concurrently
tasks = [generate_text(), print_stream()]
loop.run_until_complete(asyncio.gather(*tasks))

print("\nTime:", time.time() - start)
