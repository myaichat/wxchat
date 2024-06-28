import os, sys
import kagglehub
import torch
from pprint import pprint as pp
e=sys.exit
import time
start = time.time()
VARIANT = '2b-it' #@param ['2b', '2b-it', '7b', '7b-it', '7b-quant', '7b-it-quant']
#VARIANT = '9b-it' #@param ['2b', '2b-it', '7b', '7b-it', '7b-quant', '7b-it-quant']
MACHINE_TYPE = 'cuda' #@param ['cuda', 'cpu']

import sys 
sys.path.append("gemma_pytorch") 
from gemma.config import GemmaConfig, get_model_config
from gemma.model import GemmaForCausalLM
from gemma.tokenizer import Tokenizer
import contextlib
import os
import torch

# Load the model
VARIANT = "9b" 
MACHINE_TYPE = "cuda" 
#weights_dir = '/kaggle/input/gemma-2/pytorch/gemma-2-9b-it/1' 

weights_dir = r'C:\Users\alex_\.cache\kagglehub\models\google\gemma-2\pyTorch\gemma-2-9b-it\1' 

@contextlib.contextmanager
def _set_default_tensor_type(dtype: torch.dtype):
  """Sets the default torch dtype to the given dtype."""
  torch.set_default_dtype(dtype)
  yield
  torch.set_default_dtype(torch.float)

model_config = get_model_config(VARIANT)
model_config.tokenizer = os.path.join(weights_dir, "tokenizer.model")

device = torch.device(MACHINE_TYPE)
with _set_default_tensor_type(model_config.get_dtype()):
  model = GemmaForCausalLM(model_config)
  model.load_weights(weights_dir)
  model = model.to(device).eval()



USER_CHAT_TEMPLATE = "<start_of_turn>user\n{prompt}<end_of_turn><eos>\n"
MODEL_CHAT_TEMPLATE = "<start_of_turn>model\n{prompt}<end_of_turn><eos>\n"

prompt = (
    USER_CHAT_TEMPLATE.format(
        prompt='Write me a poem about Machine Learning.'
    )
    + '<start_of_turn>model\n'
)
print('Elapsed time:', time.time()-start)
#calculate elapsed time
import time
start = time.time()
result=model.generate(
    USER_CHAT_TEMPLATE.format(prompt=prompt),
    device=device,
    output_len=100,
)
for token in result:
    print(token, end='', flush=True)
#in seconds
print('Elapsed time:', time.time()-start)
e()

if 0:
    USER_CHAT_TEMPLATE = '<start_of_turn>user\n{prompt}<end_of_turn>\n'
    MODEL_CHAT_TEMPLATE = '<start_of_turn>model\n{prompt}<end_of_turn>\n'

    # Sample formatted prompt
    prompt = (
        USER_CHAT_TEMPLATE.format(
            prompt='Do you code wxPython?'
        )
        + '<start_of_turn>model\n'
    )
    print('Chat prompt:\n', prompt)

    result = model.generate(
        USER_CHAT_TEMPLATE.format(prompt=prompt),
        device=device,
        output_len=100
    )
    print(result)
    for token in result:
        print(token, end='', flush=True)

if 0:

    # Load model weights
    #weights_dir = kagglehub.model_download(f'google/gemma/pyTorch/{VARIANT}')
    path = kagglehub.model_download(f"google/gemma-2/pyTorch/gemma-2-{VARIANT}")  
    print (path)  

    e()
if 0:
    #weights_dir = kagglehub.model_download(f'google/gemma/pyTorch/{VARIANT}')
    #print (weights_dir)
    #e()
    sys.path.append('gemma_pytorch')

    from gemma.config import get_config_for_7b, get_config_for_2b
    from gemma.model import GemmaForCausalLM

    # Ensure that the tokenizer is present
    tokenizer_path = os.path.join(weights_dir, 'tokenizer.model')
    assert os.path.isfile(tokenizer_path), 'Tokenizer not found!'

    # Ensure that the checkpoint is present
    ckpt_path = os.path.join(weights_dir, f'gemma-{VARIANT}.ckpt')
    assert os.path.isfile(ckpt_path), 'PyTorch checkpoint not found!'


if 0:   

    # Set up model config.
    model_config = get_config_for_2b() if "2b" in VARIANT else get_config_for_7b()
    model_config.tokenizer = tokenizer_path
    model_config.quant = 'quant' in VARIANT

    # Instantiate the model and load the weights.
    torch.set_default_dtype(model_config.get_dtype())
    device = torch.device(MACHINE_TYPE)
    model = GemmaForCausalLM(model_config)
    model.load_weights(ckpt_path)
    model = model.to(device).eval()



    USER_CHAT_TEMPLATE = '<start_of_turn>user\n{prompt}<end_of_turn>\n'
    MODEL_CHAT_TEMPLATE = '<start_of_turn>model\n{prompt}<end_of_turn>\n'

    # Sample formatted prompt
    prompt = (
        USER_CHAT_TEMPLATE.format(
            prompt='Do you code wxPython?'
        )
        + '<start_of_turn>model\n'
    )
    print('Chat prompt:\n', prompt)

    result = model.generate(
        USER_CHAT_TEMPLATE.format(prompt=prompt),
        device=device,
        output_len=100,        
        temperature= 0.95,
        top_p= 1.0,
        top_k = 100    
    )
    for token in result:
        print(token, end='', flush=True)



