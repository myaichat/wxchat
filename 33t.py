from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TextStreamer
import torch
import time

# Define a custom streamer class
class CustomStreamer(TextStreamer):
    def __init__(self, tokenizer, skip_special_tokens=True):
        super().__init__(tokenizer, skip_special_tokens=skip_special_tokens)
        self.generated_text = ""
        self.skip_special_tokens = skip_special_tokens

    def on_finalized_text(self, text: str, stream_end: bool = False):
        # This method is called whenever a chunk of text is finalized
        print(text, end="", flush=True)  # Print the chunk immediately
        self.generated_text += text  # Accumulate the text

start = time.time()
model_id = "google/gemma-2-9b-it"
dtype = torch.bfloat16

tokenizer = AutoTokenizer.from_pretrained(model_id)
print("tokenizer:", time.time() - start)

quantization_config = BitsAndBytesConfig(load_in_4bit=True)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=quantization_config,
    device_map="auto",
    cache_dir="./cache",
    torch_dtype=dtype,
    attn_implementation="flash_attention_2"
)
print("model:", time.time() - start)

chat = [
    {"role": "user", "content": "short List major python versions. Index answer"},
    {"role": "assistant", "content": """Here are some major Python versions, indexed:

0. **Python 2.x** (Legacy, End-of-Life)
1. **Python 3.0** (Major rewrite, introduced many changes)
2. **Python 3.1** - **Python 3.9** (Ongoing development, with incremental improvements and bug fixes)
3. **Python 3.10** (Latest stable release as of October 2023)

Let me know if you'd like more details about a specific version!"""},
    {"role": "user", "content": "Tell me more about option 0"},
]

prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

# Ensure the inputs are moved to the same device as the model
inputs = inputs.to(model.device)

# Use the custom streamer
streamer = CustomStreamer(tokenizer, skip_special_tokens=True)

print("\nGenerating response:")
model.generate(input_ids=inputs, max_new_tokens=500, streamer=streamer)

# After generation, print the total time and the full generated text
print("\n\nTotal:", time.time() - start)
print("\nFull Generated Text:", streamer.generated_text)