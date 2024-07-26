from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from transformers import AutoTokenizer, AutoModelForCausalLM, LogitsProcessorList, LogitsProcessor
import torch
import time
start = time.time()
class StreamProcessor(LogitsProcessor):
    def __init__(self, tokenizer, model):
        self.tokenizer = tokenizer
        self.model = model
        self.generated_text = ""
        print("\nStart:", time.time() - start)
        self.start= time.time()
    
    def __call__(self, input_ids, scores):
        print(f"Processing logits: {input_ids} -> {scores}")
        generated_token_id = torch.argmax(scores, dim=-1)
        generated_token = self.tokenizer.decode(generated_token_id)
        self.generated_text += generated_token
        print(generated_token, end='', flush=True)
        return scores
    
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
### Instruction:
Create amazing detailed image description infused with ukrainian essence like this: "1950s Pinup Girl inspired by the Wildflowers of Ukraine's Summer Fields.The vibrant bouquet of blue and yellow wildflowers adorns the beauty's long,"
Do not give image references. do not use html. Do not use special characters. Do not use emojis. Do not use urls. Do not use any other language than English. Do not
return detailed description in <fused_image> tags.
### Response:
"""


#input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

logits_processor = LogitsProcessorList()
logits_processor.append(StreamProcessor(tokenizer, model))

# Tokenize the input
inputs = tokenizer(input_text, return_tensors="pt")
input_ids = inputs["input_ids"].to(model.device)
attention_mask = inputs["attention_mask"].to(model.device)



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
    pad_token_id=tokenizer.eos_token_id,
    attention_mask=attention_mask,
    
    logits_processor=logits_processor,
)

print("\nStreaming:", time.time() - logits_processor[0].start)
print("\nTotal:", time.time() - start)
