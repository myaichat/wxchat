import time
import torch
from diffusers import StableDiffusionPipeline, DDIMScheduler, AutoencoderKL
from ip_adapter.ip_adapter_faceid import IPAdapterFaceIDPlus
from huggingface_hub import hf_hub_download
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from pprint import pprint as pp
import cv2
from os.path import isfile
from pubsub import pub
from pprint import pprint as pp 
from include.Common import log, format_stacktrace, fmt, split_text_into_chunks  
import os
from huggingface_hub import hf_hub_download
import include.config.init_config as init_config 
apc = init_config.apc


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

if device == "cpu":
    dtype = torch.float32
else:
    dtype = torch.float16

class Fuser_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.pipe={}
        self.tokenizer={}
        self.chat_history={}

    def get_pipe(self, model_id):
        #device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if model_id not in self.pipe:

            noise_scheduler = DDIMScheduler(
                num_train_timesteps=1000,
                beta_start=0.00085,
                beta_end=0.012,
                beta_schedule="scaled_linear",
                clip_sample=False,
                set_alpha_to_one=False,
                steps_offset=1,
            )


    
            vae = AutoencoderKL.from_pretrained(vae_model_path,cache_dir=destination_dir,).to(dtype=dtype) 
            pipe = StableDiffusionPipeline.from_pretrained(
                base_model_path,
                torch_dtype=dtype, 
                scheduler=noise_scheduler,
                vae=vae,
                cache_dir=destination_dir,
            ).to(device)
            self.pipe[model_id]=pipe        
            
         
            
        else:
            print("Model already loaded")
        return self.pipe[model_id] 
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  tokenizer= AutoTokenizer.from_pretrained("gpt2", cache_dir="cache")
            tokenizer.pad_token = tokenizer.eos_token
            tokenizer.padding_side = "left"

        else:
            print("Tokenizer already loaded")
        return self.tokenizer[model_id]
    def get_image_paths(self, tab_id)  :
        # get prompt text from all prompt panels
        images = []
        pp(apc.canvas[tab_id])
        for canvasCtrl in apc.canvas[tab_id]:
            assert canvasCtrl.image_path, f"No image path found {canvasCtrl.image_path}"
            images.append(canvasCtrl.image_path)
        assert images, "No images found"
        return images

    def generate_image(self,chat, images, prompt, ip_model_plus,app, photorealistic, negative_prompt = 'low-quality'):
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
            print(image)
            assert isfile(image), f"File not found: {image}"    
            face = cv2.imread(image)
            faces = app.get(face)
            faceid_embed = torch.from_numpy(faces[0].normed_embedding).unsqueeze(0)
            faceid_all_embeds.append(faceid_embed)
            if(first_iteration):
                face_image = face_align.norm_crop(face, landmark=faces[0].kps, image_size=224) # you can also segment the face
                first_iteration = False
                
        average_embedding = torch.mean(torch.stack(faceid_all_embeds, dim=0), dim=0)
        #width,height= 512, 512 + 512
        #width,height=  512 + 512, 512
        pp(chat.img_size)
        width,height= chat.img_size
        image = ip_model_plus.generate(
            prompt=prompt, negative_prompt=negative_prompt, faceid_embeds=average_embedding,
            scale=likeness_strength, face_image=face_image, shortcut=True, s_scale=face_strength, width=width, height=height, num_inference_steps=30, num_samples=2
        )

        return image  
    
    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id, image_path):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        #txt='\n'.join(split_text_into_chunks(text_prompt,80))
        # header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        start = time.time()
        try:

            start = time.time()
            
   

            

            images=self.get_image_paths(receiveing_tab_id)
            

            txt='\n'.join(split_text_into_chunks(text_prompt,80))
            header = fmt([[f'{txt}\nAnswer:\n']],['Prompt | '+chat.model])
            pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)            
            gen_start=time.time()

            

            pipe = self.get_pipe(base_model_path, )
            ip_model_plus = IPAdapterFaceIDPlus(pipe, image_encoder_path, ip_plus_ckpt, device, torch_dtype= dtype)


            

            app = FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
            app.prepare(ctx_id=0, det_size=(640, 640))

            
            result = self.generate_image(chat, images,text_prompt,ip_model_plus, app, photorealistic=False, negative_prompt='low quality')
            
            import uuid
            for id,img in enumerate(result):
             
                img.save(f"watercolor_{id}_{uuid.uuid4()}.jpg")
                img.show()



            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')

        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)
