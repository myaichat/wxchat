from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import TextStreamer
import torch
import time

start = time.time()
model_id="google/gemma-2-9b-it"
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

streamer = TextStreamer(tokenizer, skip_special_tokens=True)

_ = model.generate(
    **input_ids,
    max_new_tokens=100,
    do_sample=True,
    temperature=0.7,
    streamer=streamer
)

print("\nTime:", time.time() - start)