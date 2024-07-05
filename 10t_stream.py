from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer

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
    # flashattention=True,    
    # use_cuda=True,
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-7B-Instruct")

prompt = "Give me a short introduction to large language model."

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    #{"role": "system", "content": "You are transformers lib API expert."},
    {"role": "user", "content": prompt}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(device)

# Setting up the streamer for streaming output
streamer = TextStreamer(tokenizer, skip_special_tokens=True)

# Generating the response with streaming enabled
model.generate(
    model_inputs.input_ids,
    max_new_tokens=4096,
    streamer=streamer
)