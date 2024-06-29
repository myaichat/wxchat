from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch
import time

start = time.time()
model_id = "google/gemma-2-9b-it"
dtype = torch.bfloat16

tokenizer = AutoTokenizer.from_pretrained(model_id)
print("tokenizer:", time.time() - start)

quantization_config = BitsAndBytesConfig(load_in_4bit=True)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=quantization_config,
    device_map="auto",  # Change this to "auto"
    cache_dir="./cache",
    torch_dtype=dtype,
    attn_implementation="flash_attention_2"
)
print("model:", time.time() - start)

chat = [
    {"role": "user", "content":"""
Can you as chatbot that assists with anwering questions about 
        code included or adding new features
        and debugging scripts written using wxPython.
        Give short description for each change the code required for change.
        Numerate each change by index
        Present changes in form:
        #Description
        [CHANGE DESCRIPTION]
        #Change To:
        [NEW CODE LINES]
     """},
    {"role": "assistant", "content": """Okay, I'm ready to help with your wxPython code!  I'll understand the context of each change.

Provide me with the code snippet and tell me what you want to change.

I'll number the changes and make a numbered list to keep track of what is updated.



Let's get coding!"""},   
 {"role": "user", "content": """
How can I improve this code?:
import wx
import wx.stc as stc
import wx.lib.agw.aui as aui
import time, glob,threading, traceback
import os
from pubsub import pub
from pprint import pprint as pp
from include.Common import *
from include.fmt import fmt
from include.Copilot.Base.Base_InputPanel_Google_Gemma import Base_InputPanel_Google_Gemma
import include.config.init_config as init_config
apc = init_config.apc
default_chat_template='SYSTEM'
default_copilot_template='SYSTEM_CHATTY'
#DEFAULT_MODEL  = 'gpt-4o'


DEFAULT_MODEL='google/gemma-2-9b-it'

model_list=[DEFAULT_MODEL,'google/gemma-2-27b-it']
dir_path = 'template'

chatHistory,  currentQuestion, currentModel = apc.chatHistory,  apc.currentQuestion, apc.currentModel
questionHistory= apc.questionHistory
all_templates, all_chats, all_system_templates = apc.all_templates, apc.all_chats, apc.all_system_templates
panels     = AttrDict(dict(workspace='WorkspacePanel', vendor='ChatDisplayNotebookPanel',chat='DisplayPanel', input='InputPanel'))

from transformers import AutoTokenizer, AutoModelForCausalLM, LogitsProcessorList, LogitsProcessor
import torch
import time
from transformers import TextStreamer
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TextStreamer
import torch
import time

"""}, 
]

prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

# Ensure the inputs are moved to the same device as the model
inputs = inputs.to(model.device)

outputs = model.generate(input_ids=inputs, max_new_tokens=1500)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
print("Total:", time.time() - start)
