from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from threading import Thread
import torch

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
input_text ="""
Create amazing image prompt like this: 1950s Pinup Girl inspired by the Wildflowers of Ukraine's Summer Fields

"""

# Tokenize the input
inputs = tokenizer(input_text, return_tensors="pt")
input_ids = inputs["input_ids"].to(model.device)
attention_mask = inputs["attention_mask"].to(model.device)

# Set up the streamer
streamer = TextIteratorStreamer(tokenizer)

# Generate text using streaming
generation_kwargs = dict(
    input_ids=input_ids,
    max_length=1000,
    num_return_sequences=1,
    no_repeat_ngram_size=2,
    temperature=1.7,
    top_k=50,
    top_p=0.95,
    do_sample=True,
    pad_token_id=tokenizer.eos_token_id,
    attention_mask=attention_mask,
    streamer=streamer,
)

# Run the generation in a separate thread
thread = Thread(target=model.generate, kwargs=generation_kwargs)
thread.start()

# Print the generated text as it's produced
for text in streamer:
    print(text, end="", flush=True)

print()  # Print a newline at the end
thread.join()