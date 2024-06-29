# pip install accelerate
from transformers import AutoTokenizer, AutoModelForCausalLM
import time
import torch

model_id = "google/gemma-2-9b-it"
#model_id = "google/gemma-2-27b-it"
start= time.time()

tokenizer = AutoTokenizer.from_pretrained(model_id)


from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(load_in_4bit=True)







model = AutoModelForCausalLM.from_pretrained(
    model_id,
    #quantization_config=quantization_config,
    device_map="auto",
    cache_dir="./cache",
    torch_dtype=torch.bfloat16
    ,attn_implementation="flash_attention_2"
)

    
input_text = "Write a function that checks if a year is a leap year. no explanation needed."
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

# Function to generate text and stream output
def generate_and_stream(input_ids, max_length=100):
    generated_ids = input_ids['input_ids']
    
    for _ in range(max_length):
        # Generate the next token
        outputs = model.generate(generated_ids, max_new_tokens=1, 
            do_sample=True,
            temperature=1.0,
            top_p=0.95,      # Nucleus sampling
            top_k=50        # Limiting to top_k choices)
        )
        new_token_id = outputs[0, -1].unsqueeze(0).unsqueeze(0)
        generated_ids = torch.cat((generated_ids, new_token_id), dim=-1)
        
        # Decode and print the new token
        new_token = tokenizer.decode(new_token_id[0], skip_special_tokens=True)
        #print(123)
        print(new_token, end='', flush=True)
        
        # Break if the end of sequence token is generated
        if new_token_id.item() == tokenizer.eos_token_id:
            break

# Stream the generated text
generate_and_stream(input_ids)
print("\nTime:", time.time() - start)