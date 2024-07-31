import torch
from diffusers import StableDiffusionPipeline, DDIMScheduler, AutoencoderKL
from ip_adapter.ip_adapter_faceid import IPAdapterFaceIDPlus
from huggingface_hub import hf_hub_download
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from pprint import pprint as pp
import cv2

import os
from huggingface_hub import hf_hub_download

# Define the base directory where models will be downloaded
base_model_path = "SG161222/Realistic_Vision_V4.0_noVAE"
vae_model_path = "stabilityai/sd-vae-ft-mse"
image_encoder_path = "laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
destination_dir = "cache"  # Replace with your desired directory
if 0:
    # Download the IP Adapter FaceID Plus model to the specified directory
    ip_plus_ckpt = hf_hub_download(
        repo_id="h94/IP-Adapter-FaceID",
        filename="ip-adapter-faceid-plusv2_sd15.bin",
        repo_type="model",
        local_dir=destination_dir
    )

    print(f"Downloaded IP Adapter FaceID Plus model to: {ip_plus_ckpt}")
else:
    ip_plus_ckpt='cache\ip-adapter-faceid-plusv2_sd15.bin'
device = "cuda"

noise_scheduler = DDIMScheduler(
    num_train_timesteps=1000,
    beta_start=0.00085,
    beta_end=0.012,
    beta_schedule="scaled_linear",
    clip_sample=False,
    set_alpha_to_one=False,
    steps_offset=1,
)


if device == "cpu":
    __dtype = torch.float32
else:
    __dtype = torch.float16

vae = AutoencoderKL.from_pretrained(vae_model_path,cache_dir=destination_dir,).to(dtype=__dtype) 
pipe = StableDiffusionPipeline.from_pretrained(
    base_model_path,
    torch_dtype=__dtype, 
    scheduler=noise_scheduler,
    vae=vae,
    cache_dir=destination_dir,
).to(device)

ip_model_plus = IPAdapterFaceIDPlus(pipe, image_encoder_path, ip_plus_ckpt, device, torch_dtype=__dtype)

app = FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

def generate_image(images, prompt, photorealistic, negative_prompt = 'low-quality'):
    if photorealistic == True:
        face_strength=1.3
        likeness_strength = 1
    else:
        face_strength=0.1
        likeness_strength = 0.8
    print(face_strength, likeness_strength)
    
    faceid_all_embeds = []
    first_iteration = True
    for image in images:
        face = cv2.imread(image)
        faces = app.get(face)
        faceid_embed = torch.from_numpy(faces[0].normed_embedding).unsqueeze(0)
        faceid_all_embeds.append(faceid_embed)
        if(first_iteration):
            face_image = face_align.norm_crop(face, landmark=faces[0].kps, image_size=224) # you can also segment the face
            first_iteration = False
            
    average_embedding = torch.mean(torch.stack(faceid_all_embeds, dim=0), dim=0)
    width,height= 512, 512 + 512//2
    image = ip_model_plus.generate(
        prompt=prompt, negative_prompt=negative_prompt, faceid_embeds=average_embedding,
        scale=likeness_strength, face_image=face_image, shortcut=True, s_scale=face_strength, width=512, height=height, num_inference_steps=30, num_samples=2
    )

    return image  

my_imgs = ["selfie_1.jpg","selfie_2.jpg","selfie_3.jpg","selfie_4.jpg","selfie_5.jpg","selfie_6.jpg"]
#my_imgs = ["selfie_2.jpg","selfie_3.jpg"]
my_imgs = ["test_1.jpg","test_2.jpg","test_3.jpg"]
prompt="""
A close-up portrait of a woman with a vibrant orange asymmetrical bob haircut. Her light green eyes and well-defined eyebrows stand out against her smooth, glowing skin. She wears light pink lipstick and a white sleeveless top. The background features a warm-toned bokeh effect, creating a soft, dreamy atmosphere.

"""
prompt="""
A closeup of a Ukrainian girl with an icy blonde bob cut with bangs, wearing a black turtleneck. Her face is partially obscured by voluminous hair and a black Tryzub tattoo with blue and yellow flowers. Subtle pink lipstick adds romance. Soft lighting highlights the texture and shine of her hair against a blurred natural background.
"""
result = generate_image(my_imgs,prompt,photorealistic=False, negative_prompt='low quality')
pp(result)
for id,img in enumerate(result):
    img.save(f"watercolor_{id}.jpg")