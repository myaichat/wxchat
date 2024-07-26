from transformers import AutoTokenizer, AutoModelForCausalLM
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
input_text = "Once upon a time, in a far-off land,"

# Tokenize the input
input_ids = tokenizer.encode(input_text, return_tensors="pt").to(model.device)

# Generate text using streaming
streamer = tokenizer.decode
for output in model.generate(
    input_ids,
    max_length=100,
    num_return_sequences=1,
    no_repeat_ngram_size=2,
    temperature=0.7,
    top_k=50,
    top_p=0.95,
    do_sample=True,
    pad_token_id=tokenizer.eos_token_id,
    streamer=streamer,
):
    print(tokenizer.decode(output, skip_special_tokens=True), end="", flush=True)

print()  # Print a newline at the end