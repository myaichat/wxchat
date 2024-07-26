from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
import torch
import time

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

start = time.time()

# Load the model and tokenizer
model_name = "PygmalionAI/mythalion-13b"
tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
tokenizer.add_special_tokens({'pad_token': '[PAD]'})
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

streamer = CustomTextStreamer(tokenizer)

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
    pad_token_id=tokenizer.pad_token_id,
    attention_mask=attention_mask,
    streamer=streamer
)

print("\nStreaming:", time.time() - start)
model.generate(**generation_kwargs)

print("\nTotal:", time.time() - start)