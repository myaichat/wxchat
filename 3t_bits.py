from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import TextStreamer
import torch
import time
import sys
e=sys.exit


#from transformers import GemmaTokenizerFast

#tokenizer = GemmaTokenizerFast.from_pretrained("hf-internal-testing/dummy-gemma")

print('Device name:', torch.cuda.get_device_properties('cuda').name)
print('FlashAttention available:', torch.backends.cuda.flash_sdp_enabled())
print(f'torch version: {torch.__version__}')
#e()
start = time.time()

from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(load_in_4bit=True)

quantization_config = BitsAndBytesConfig(
load_in_4bit=True,
bnb_4bit_use_double_quant=True,
bnb_4bit_quant_type="nf4",
bnb_4bit_compute_dtype=torch.bfloat16
)


model_id="google/gemma-2-27b-it"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    #torch_dtype=torch.bfloat16,
    quantization_config=quantization_config,
    cache_dir="./cache",
    trust_remote_code=True,
    low_cpu_mem_usage=True
)

input_text = "Write me a poem about Machine Learning."
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

streamer = TextStreamer(tokenizer, skip_special_tokens=True)

outputs = model.generate(
    **input_ids,
    max_new_tokens=100,
    do_sample=False,
    temperature=1.0,
    streamer=streamer,
    top_p=0.95,      # Nucleus sampling
    top_k=50         # Limiting to top_k choices
)
#print(outputs)
print("\nTime:", time.time() - start)