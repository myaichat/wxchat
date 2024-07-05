import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
import sys

device = "cuda"  # the device to load the model onto

if 0:
    print('CUDA available:', torch.cuda.is_available())
    print('Device name:', torch.cuda.get_device_properties('cuda').name)
    print('FlashAttention available:', torch.backends.cuda.flash_sdp_enabled())

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2-7B-Instruct",
    torch_dtype="auto",
    device_map="auto",
    cache_dir="./cache",
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-7B-Instruct")

prompt = "Give me a short introduction to large language model."
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": prompt}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(device)

# Set up the streamer with a small chunk size
streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True, skip_prompt=True, timeout=1)

# Function to preprocess chunks
def preprocess_chunk(chunk):
    # Example preprocessing: convert to uppercase
    return chunk.upper()

# Start the generation
print("Streaming output:")
sys.stdout.flush()

# Start the generation with streaming
generation_output = model.generate(
    input_ids=model_inputs['input_ids'],
    max_new_tokens=512,
    use_cache=True,
    streamer=streamer
)

# Processing and printing the streamed output
for chunk in streamer:
    processed_chunk = preprocess_chunk(chunk)
    print(processed_chunk, end='', flush=True)

print("\nGeneration complete.")
