from transformers import AutoModelForCausalLM, AutoProcessor
import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu") 

model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Florence-2-base-ft",
    trust_remote_code=True,
    revision='refs/pr/6'
).to(device) 
processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base-ft", 
    trust_remote_code=True, revision='refs/pr/6')

for param in model.vision_tower.parameters():
  param.is_trainable = False