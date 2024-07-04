import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import sys

device = "cuda" if torch.cuda.is_available() else "cpu"
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2-7B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto",
    cache_dir="./cache",
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-7B-Instruct")

def generate_response(prompt):
    model.eval()
    with torch.no_grad():
        input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(device)
        generated_ids = model.generate(
            input_ids,
            max_new_tokens=512,
            do_sample=True,
            top_p=0.95,
            temperature=0.7,
            repetition_penalty=1.2,
        )
    return tokenizer.batch_decode(generated_ids[:, input_ids.shape[1]:], skip_special_tokens=True)[0]

while True:
    try:
        prompt = sys.stdin.readline().strip()
        if not prompt:
            break
        response = generate_response(prompt)
        print(response)
    except KeyboardInterrupt:
        print("\nExiting...")
        break