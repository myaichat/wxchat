import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread

device = "cuda" # the device to load the model onto

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

# Set up the streamer
streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

# Run the generation in a separate thread
generation_kwargs = dict(
    model_inputs,
    streamer=streamer,
    max_new_tokens=512,
)

thread = Thread(target=model.generate, kwargs=generation_kwargs)
thread.start()

# Print the generated text as it's produced
print("Streaming output:")
for text in streamer:
    print(text, end='', flush=True)

thread.join()

print("\n\nGeneration complete.")