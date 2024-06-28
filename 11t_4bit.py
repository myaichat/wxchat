from transformers import AutoTokenizer, AutoModelForCausalLM, GemmaTokenizerFast
from transformers import TextStreamer
import torch
import time

start = time.time()
model_id="google/gemma-2-27b-it"
#from transformers import GemmaTokenizerFast

#tokenizer = GemmaTokenizerFast.from_pretrained("hf-internal-testing/dummy-gemma")
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(load_in_4bit=True)

quantization_config1 = BitsAndBytesConfig(
load_in_4bit=True,
bnb_4bit_use_double_quant=True,
bnb_4bit_quant_type="nf4",
bnb_4bit_compute_dtype=torch.bfloat16
)

tokenizer = GemmaTokenizerFast.from_pretrained(model_id)
print("tokenizer:", time.time() - start)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    #torch_dtype=torch.float16,
    #torch_dtype=torch.bfloat16,
    #revision="float16",
    cache_dir="./cache",
    trust_remote_code=True,
    low_cpu_mem_usage=True
    #,attn_implementation="flash_attention_2"
    ,quantization_config=quantization_config,
)
print("model Load:", time.time() - start)
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch


input_text = "Write me a poem about Machine Learning."
input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")


#tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

streamer = TextStreamer(tokenizer, skip_special_tokens=True, clean_up_tokenization_spaces=False)

outputs = model.generate(
    **input_ids,
    max_new_tokens=100,
    do_sample=False,
    temperature=1.0,
    top_p=0.95,      # Nucleus sampling
    top_k=50         # Limiting to top_k choices
    ,streamer=streamer
)
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(generated_text)
print("\nTime:", time.time() - start)