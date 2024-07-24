
import os
import numpy as np
import random
import torch
from diffusers import StableDiffusion3Pipeline, SD3Transformer2DModel, FlowMatchEulerDiscreteScheduler

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16

repo = "stabilityai/stable-diffusion-3-medium-diffusers"
pipe = StableDiffusion3Pipeline.from_pretrained(repo, torch_dtype=torch.float16).to(device)

MAX_SEED = np.iinfo(np.int32).max
MAX_IMAGE_SIZE = 1344

def infer(prompt, negative_prompt, seed, randomize_seed, width, height, guidance_scale, num_inference_steps):

    if randomize_seed:
        seed = random.randint(0, MAX_SEED)
        
    generator = torch.Generator().manual_seed(seed)
    
    image = pipe(
        prompt = prompt, 
        negative_prompt = negative_prompt,
        guidance_scale = guidance_scale, 
        num_inference_steps = num_inference_steps, 
        width = width, 
        height = height,
        generator = generator
    ).images[0] 
    
    return image, seed


if __name__    == '__main__':
    prompt = (
        "A highly detailed oil painting of a young Ukrainian woman holding a delicate bouquet of wildflowers wearing Flower Wreath Headband Vinok, "
    
    )
    negative_prompt = (
        "low-quality, low-resolution, "
        "crooked fingers, deformed limbs, extra fingers, missing fingers, "
        "distorted hands, unnatural poses, disproportionate body parts, "
        "anomalous anatomy, exaggerated features, unnatural proportions, "
        "mutated limbs, awkward angles, malformed hands, unrealistic joints, "
        "incorrect anatomy, incomplete limbs, broken fingers"
    )
    seed = 0
    randomize_seed = True
    width = 1024
    height = 1024
    guidance_scale = 7.0
    num_inference_steps = 28
    image, new_seed = infer(prompt, negative_prompt, seed, randomize_seed, width, height, guidance_scale, num_inference_steps)
    print(new_seed)
    # Save the image to a file
    image_path = "output_image.png"
    image.save(image_path)
    print(image_path)
    # Open the image with the default image viewer
    os.system(f'start {image_path}')
