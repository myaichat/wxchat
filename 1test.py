from transformers import AutoTokenizer, AutoModelForCausalLM, LogitsProcessorList, LogitsProcessor
import torch
import time

class StreamProcessor(LogitsProcessor):
    def __init__(self, tokenizer, model):
        self.tokenizer = tokenizer
        self.model = model
        self.generated_text = ""
        print("\nStart:", time.time() - start)
        self.start= time.time()
    
    def __call__(self, input_ids, scores):
        generated_token_id = torch.argmax(scores, dim=-1)
        generated_token = self.tokenizer.decode(generated_token_id)
        self.generated_text += generated_token
        print(generated_token, end='', flush=True)
        return scores

start = time.time()

model_id="Gryphe/MythoMax-L2-13b"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    cache_dir="./cache",
    trust_remote_code=True, #,
    low_cpu_mem_usage=True,
    attn_implementation="flash_attention_2"
)

input_text = "How are you doing today?"
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

logits_processor = LogitsProcessorList()
logits_processor.append(StreamProcessor(tokenizer, model))

outputs = model.generate(
    **input_ids,
    logits_processor=logits_processor,
    max_new_tokens=100,  # limit the number of new tokens to generate
    do_sample=True,  # disable sampling to get deterministic output
    temperature=1.0,
    top_p=0.95,      # Nucleus sampling
    top_k=50         # Limiting to top_k choices
)
#print(outputs)
print("\nStreaming:", time.time() - logits_processor[0].start)
print("\nTotal:", time.time() - start)