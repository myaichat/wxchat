from PIL import Image
import os, random
import cv2
import numpy as np
import torch
from diffusers import SD3ControlNetModel, StableDiffusion3ControlNetPipeline
import tempfile
from os.path import basename, join

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16

# Load the controlnet model
controlnet = SD3ControlNetModel.from_pretrained(
    "InstantX/SD3-Controlnet-Canny",
    torch_dtype=torch.float16
).to(device)

# Load the stable diffusion pipeline with controlnet
pipe = StableDiffusion3ControlNetPipeline.from_pretrained(
    "stabilityai/stable-diffusion-3-medium-diffusers", 
    controlnet=controlnet,
    torch_dtype=torch.float16
).to(device)

def make_canny_image(img_path: str) -> Image:
    """ Load an image and apply Canny edge detector """
    control_image = cv2.imread(img_path)
    low_threshold = 100
    high_threshold = 200
    image = cv2.Canny(control_image, low_threshold, high_threshold)
    image = image[:, :, None]
    image = np.concatenate([image, image, image], axis=2)
    return Image.fromarray(image)
in_loc= join ('in', "test_7.png")
# Apply Canny edge detection to the input image
canny_image = make_canny_image(in_loc)
prompt = """
The image portrays a side profile of a woman with an elaborate, fantastical headpiece and attire composed entirely of vibrant
 yellow and blue flowers, symbolizing the colors of the Ukrainian flag. Her headpiece is a voluminous, cloud-like formation
   adorned with a lush, intricate array of yellow daisies, marigolds, chrysanthemums, and smaller blue flowers, including roses 
   and forget-me-nots. The flowers are intricately layered and create a surreal, almost dreamlike texture. Her outfit also 
   integrates these flowers, forming a seamless, organic extension of her headpiece. The background features a soft, cloudy sky,
     complementing the ethereal and natural beauty of the composition.
 The overall atmosphere is serene and majestic, celebrating Ukrainian culture through floral artistry
"""

prompt="""naive screenprint poster art of adorable cat with an expressive face,wearing a blue and yellow scarf.The background is blue and yellow.Above the cat, the phrase "Slava Ukraini!" is written. To the right , there's a sunflower with yellow petals and a 
black center.The style is playful and childlike,charming,2d, poster-like manner.2d"""
negative_prompt = (
    "low-quality, low-resolution, realistic, 3d"
    "crooked fingers, deformed limbs, extra fingers, missing fingers, "
    "distorted hands, unnatural poses, disproportionate body parts, "
    "anomalous anatomy, exaggerated features, unnatural proportions, "
    "mutated limbs, awkward angles, malformed hands, unrealistic joints, "
    "incorrect anatomy, incomplete limbs, broken fingers"
)
negative_prompt = """

intricate, complex, realistic, detailed, muted, dull, serious, dark, lifelike, 3D, ornate, shading, photorealistic
"""
randomize_seed=True
MAX_SEED = np.iinfo(np.int32).max
MAX_IMAGE_SIZE = 1344
input_image = Image.open(in_loc)
width, height = input_image.size
width = int(width/8)*8
height = int(height/8)*8 # int(1024*1.5)
#guidance_scale = 5.0  # Increased for more adherence to the prompt
#num_inference_steps = 100  # Increased for better quality
temp_dir = join('out',basename(tempfile.mktemp()))
os.makedirs(temp_dir)
print(f"Temporary directory created at: {temp_dir}")
for controlnet_conditioning_scale in [0.1, 0.2, 0.4, 0.6, 0.8]:
    for num_inference_steps in [25, 50,  150, 200]:
        for guidance_scale in [ 1.0,3.0, 5.0, 10.0]:
            # Generate the image

            if randomize_seed:
                seed = random.randint(0, MAX_SEED)
                
            generator = torch.Generator().manual_seed(seed)

            images = pipe(
                prompt=prompt, 
                control_image=canny_image,
                controlnet_conditioning_scale=controlnet_conditioning_scale,  # Adjusted for potentially better quality
                negative_prompt=negative_prompt,
                guidance_scale=guidance_scale, 
                num_inference_steps=num_inference_steps, 
                width=width, 
                height=height,
                generator=generator
            ).images

            # Save the image to a file

            for j, image in enumerate(images):


                tmp_name= basename(tempfile.mktemp(suffix='.png'))
                tmp_loc=join(temp_dir, f'{j}_{seed}_ccs{controlnet_conditioning_scale}_is{num_inference_steps}_gs{guidance_scale}_{tmp_name}'    )
                #image_path = "i2i_output_image.png"
                image.save(tmp_loc)
                print(f"Image saved at: {tmp_loc}")

                # Open the image with the default image viewer
                os.system(f'start {tmp_loc}')
