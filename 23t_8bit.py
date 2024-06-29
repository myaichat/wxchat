# pip install bitsandbytes accelerate
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(load_in_4bit=True)

tokenizer = AutoTokenizer.from_pretrained("google/gemma-2-9b-it")
model = AutoModelForCausalLM.from_pretrained(
    "google/gemma-2-9b-it",
    device_map="auto",
    cache_dir="./cache",
    quantization_config=quantization_config
)

input_text = "Write a function that checks if a year is a leap year. no explanation needed"
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

outputs = model.generate(
    **input_ids,
    max_new_tokens=100,  # Increase the number of tokens to generate
    do_sample=True,      # Use sampling if needed
    temperature=0.7,     # Control the randomness of the output
 num_return_sequences=1,
streaming_output=True
)

output_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(output_text)
