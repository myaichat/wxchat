#import torch
import os
from transformers import AutoProcessor, AutoModelForCausalLM  
from PIL import Image
from pprint import pprint as pp
import requests
import copy

from unittest.mock import patch
from transformers.dynamic_module_utils import get_imports

def fixed_get_imports(filename: str | os.PathLike) -> list[str]:
    if not str(filename).endswith("modeling_florence2.py"):
        return get_imports(filename)
    imports = get_imports(filename)
    imports.remove("flash_attn")
    return imports
#dtype=torch.float16
model_id = 'microsoft/Florence-2-large'
with patch("transformers.dynamic_module_utils.get_imports", fixed_get_imports): #workaround for unnecessary flash_attn requirement
            model = AutoModelForCausalLM.from_pretrained(
                model_id, 
                attn_implementation="sdpa", 
                #attn_implementation="flash_attention_2",
                torch_dtype="auto",
                trust_remote_code=True,
                cache_dir="./cache",
            ).eval().cuda()
            if 0:
                model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True,
                                    torch_dtype="auto",
                                #device_map="auto",
                                cache_dir="./cache",
                                #attn_implementation="flash_attention_2",
                    ).eval()
            processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True,
                                                                    torch_dtype="auto",
                            #device_map="auto",
                            cache_dir="./cache",
                            #attn_implementation="flash_attention_2",
                            )


def run_example(task_prompt, text_input=None):
    if text_input is None:
        prompt = task_prompt
    else:
        prompt = task_prompt + text_input
    inputs = processor(text=prompt, images=image, return_tensors="pt")
    out={}
    for tt in  range(1,20,3):
        temp=tt/10
        for top_k in [1, 10, 30 , 50, 100, 200, 300]:
            for tp in  range(1,20,3):
                top_p=tp/10
                generated_ids = model.generate(
                input_ids=inputs["input_ids"].cuda(),
                pixel_values=inputs["pixel_values"].cuda(),
                max_new_tokens=100,
                early_stopping=False,
                do_sample=True,
                num_beams=3,
                num_return_sequences=1,
                temperature=temp,
                top_k=top_k, 
                top_p=top_p,
                )
                
                for generated_text in  processor.batch_decode(generated_ids, skip_special_tokens=False):
                    parsed_answer = processor.post_process_generation(
                        generated_text, 
                        task=task_prompt, 
                        image_size=(image.width, image.height),
                        #stream=True
                    )
                    out[(temp,top_k, top_p)]=parsed_answer['<OCR>'].strip()
    return out



#url = "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/transformers/tasks/car.jpg?download=true"
fn='2_ray_ban_meta.jpeg'
image = Image.open(fn)

task_prompt = '<MORE_DETAILED_CAPTION>'
task_prompt = '<OCR>'
ret=run_example(task_prompt)
pp(ret)