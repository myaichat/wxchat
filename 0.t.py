#import torch
import os
from transformers import AutoProcessor, AutoModelForCausalLM  
from PIL import Image
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
    generated_ids = model.generate(
      input_ids=inputs["input_ids"].cuda(),
      pixel_values=inputs["pixel_values"].cuda(),
      max_new_tokens=1024,
      early_stopping=False,
      do_sample=False,
      num_beams=3,
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed_answer = processor.post_process_generation(
        generated_text, 
        task=task_prompt, 
        image_size=(image.width, image.height),
        #stream=True
    )

    return parsed_answer

#url = "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/transformers/tasks/car.jpg?download=true"
fn='ray_ban_meta.jpeg'
image = Image.open(fn)

task_prompt = '<MORE_DETAILED_CAPTION>'
ret=run_example(task_prompt)
print(ret)