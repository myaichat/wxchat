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
model_id="google/gemma-2-9b-it"
model_id="google/gemma-2-27b-it"


from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig


quantization_config = BitsAndBytesConfig(load_in_4bit=True)


quantization_config_2 = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)


tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=quantization_config_2,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    cache_dir="./cache",
    trust_remote_code=True #,
    #low_cpu_mem_usage=True
)

input_text = "Write me a poem about Machine Learning."
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
print(outputs)
print("\nStreaming:", time.time() - logits_processor[0].start)
print("\nTotal:", time.time() - start)
