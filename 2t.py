import sys 

sys.path.append("/kaggle/working/gemma_pytorch/") 
from gemma.config import GemmaConfig, get_config_for_7b, get_config_for_2b
from gemma.model import GemmaForCausalLM
from gemma.tokenizer import Tokenizer
import contextlib
import os
import torch



# Load the model
VARIANT = "2b-it" 
MACHINE_TYPE = "cpu" 
weights_dir = 'input\\gemma\\pytorch\\2b-it\\2' 

@contextlib.contextmanager
def _set_default_tensor_type(dtype: torch.dtype):
  """Sets the default torch dtype to the given dtype."""
  torch.set_default_dtype(dtype)
  yield
  torch.set_default_dtype(torch.float)

model_config = get_config_for_2b() if "2b" in VARIANT else get_config_for_7b()
model_config.tokenizer = os.path.join(weights_dir, "tokenizer.model")

device = torch.device(MACHINE_TYPE)
with _set_default_tensor_type(model_config.get_dtype()):
  model = GemmaForCausalLM(model_config)
  ckpt_path = os.path.join(weights_dir, f'gemma-{VARIANT}.ckpt')
  model.load_weights(ckpt_path)
  model = model.to(device).eval()


# Use the model

USER_CHAT_TEMPLATE = "<start_of_turn>user\n{prompt}<end_of_turn>\n"
MODEL_CHAT_TEMPLATE = "<start_of_turn>model\n{prompt}<end_of_turn>\n"

prompt = (
    USER_CHAT_TEMPLATE.format(
        prompt="What is a good place for travel in the US?"
    )
    + MODEL_CHAT_TEMPLATE.format(prompt="California.")
    + USER_CHAT_TEMPLATE.format(prompt="What can I do in California?")
    + "<start_of_turn>model\n"
)

model.generate(
    prompt,
    device=device,
    output_len=100,
)