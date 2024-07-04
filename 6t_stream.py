import torch
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

class CustomTextStreamer(TextStreamer):
    skip_special_tokens=True
    def put(self, value, **kwargs):
        # Ensure value is a tensor and convert to a list of token IDs
        if isinstance(value, torch.Tensor):
            value = value.tolist()
        # Decode the list of token IDs to text
        text = self.tokenizer.decode(value[0], skip_special_tokens=self.skip_special_tokens, **kwargs)
        # Customize your output handling here
        custom_output = f"Custom processed output: {text}"
        # Print or process the custom output as needed
        print(text, end='', flush=True)


# Setting up the streamer for streaming output
streamer = CustomTextStreamer(tokenizer, skip_special_tokens=True)

# Generating the response with streaming enabled
model.generate(
    model_inputs.input_ids,
    max_new_tokens=4096,
    min_new_tokens=1,
    do_sample=True,
    top_p=0.95,
    top_k=40,
    temperature=float(0.8),
    repetition_penalty=1.2,   
    length_penalty=1.0,  
    num_beams = 1,
    use_cache = True,
    streamer=streamer
)
