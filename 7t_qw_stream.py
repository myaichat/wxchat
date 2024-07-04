import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Set up the device
device = "cuda" if torch.cuda.is_available() else "cpu"

# Initialize the model with streaming enabled
model = AutoModelForCausalLM.from_pretrained(
"Qwen/Qwen2-7B-Instruct",
torch_dtype="auto",
    device_map="auto",
    cache_dir="./cache",
    trust_remote_code=True,  # This is required for Qwen models
    use_cache=True,          # Enables caching for streaming
    # Other arguments as needed
)

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-7B-Instruct")

prompt = "Give me a short introduction to large language model."
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": prompt}
]

# Process each message in a loop or sequentially
for message in messages:
    text = tokenizer.apply_chat_template(
        [message],
        tokenize=False,
        add_generation_prompt=True
    )
    model_inputs = tokenizer(text, return_tensors="pt").to(device)

    # Generate tokens one by one
    for new_token in model.generate(
        model_inputs.input_ids,
        max_new_tokens=512,
        do_sample=True,
        top_p=0.95,
        temperature=0.8,
        repetition_penalty=1.2,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
        #stream_output=True,
    ):
        # Print or process the token as it becomes available
        print(new_token.item(), end='')
    print()