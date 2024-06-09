from PIL import Image 
import requests 
from transformers import AutoModelForCausalLM 
from transformers import AutoProcessor 

model_id = "microsoft/Phi-3-vision-128k-instruct" 

model = AutoModelForCausalLM.from_pretrained(model_id, device_map="cuda", trust_remote_code=True, torch_dtype="auto", _attn_implementation='flash_attention_2') # use _attn_implementation='eager' to disable flash attention

processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True) 

messages = [ 
    {"role": "user", "content": "<|image_1|>\nWhat is shown in this image?"}, 
    {"role": "assistant", "content": 'The image depicts a scene of conflict or war. A person is holding a Ukrainian flag aloft, suggesting a theme of nationalism or resistance. The individual is equipped with a rifle and is surrounded by a group of soldiers, some of whom are engaged in combat, and others are in the background. The setting appears to be a battlefield with a desolate landscape, and the weather is overcast, contributing to the somber atmosphere of the scene.'},
    {"role": "user", "content": "add ukrainian essence to the image and show updated description. "}, 
    {"role": "assistant", "content": "The image has been updated to include a Ukrainian flag, which now flutters in the wind, adding a sense of national pride and identity to the scene. The flag's vibrant colors contrast with the otherwise muted tones of the battlefield. The updated description reflects the presence of the flag and its significance in the context of the image."},
    {"role": "user", "content": 'Show full upated description.'},
] 

messages = [{"role": "user", "content": "<|image_1|>\nWhat is shown in this image? Be as detailed and as artistic as possible"}]

messages = [{"role": "user", "content": "<|image_1|>\nWhat is shown in this image? Provide a detailed and artistically rich description of the image provided by the user. Focus on capturing the essence, mood, and atmosphere. Highlight intricate details, colors, textures, and emotions. Use evocative language to paint a vivid picture that brings the image to life in the reader's mind"}]
fn = '0_3.jpg'
image = Image.open(fn)

prompt = processor.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
while True:
    fn=input("Enter the file name: ")
    if fn == "exit":
        break
    if not fn:
        fn = '0_3.jpg'
    image = Image.open(fn)
    inputs = processor(prompt, [image], return_tensors="pt").to("cuda:0") 

    generation_args = { 
        "max_new_tokens": 1500, 
        "temperature": 1, 
        "do_sample": False, 
    } 

    generate_ids = model.generate(**inputs, eos_token_id=processor.tokenizer.eos_token_id, **generation_args) 

    # remove input tokens 
    generate_ids = generate_ids[:, inputs['input_ids'].shape[1]:]
    response = processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0] 

    print(response)
