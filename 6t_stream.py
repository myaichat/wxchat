from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
import torch
import time

start = time.time()
model_id="google/gemma-2-27b-it"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    cache_dir="./cache",
    trust_remote_code=True,
    low_cpu_mem_usage=True
)

input_text = "Write me a poem about Machine Learning."
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

# Set up the streamer
streamer = TextIteratorStreamer(tokenizer)

# Generate the text with streaming
outputs = model.generate(
    **input_ids,
    streamer=streamer,
    max_new_tokens=100,  # Adjust as needed
    do_sample=False  # Disable sampling to get deterministic output
)

# Print the streamed output
for new_text in streamer:
    print(new_text, end='', flush=True)

print("\nTime:", time.time() - start)
