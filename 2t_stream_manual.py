
import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer
device = "cuda" # the device to load the model onto
if 0:
    
    print('CUDA available:', torch.cuda.is_available())
    print('Device name:', torch.cuda.get_device_properties('cuda').name)
    print('FlashAttention available:', torch.backends.cuda.flash_sdp_enabled())

class ManualTextStreamer:
    def __init__(self, tokenizer, delay=0.1, skip_special_tokens=True):
        self.tokenizer = tokenizer
        self.delay = delay
        self.skip_special_tokens = skip_special_tokens
        self.model = None

    def put(self, input_ids):
        decoded_output = self.tokenizer.decode(input_ids, skip_special_tokens=self.skip_special_tokens)
        print(decoded_output, end='', flush=True)
        time.sleep(self.delay)

    def __call__(self, model, input_ids, logits_processor=None, stopping_criteria=None, **generate_kwargs):
        self.model = model
        logits_processor = logits_processor if logits_processor is not None else LogitsProcessorList()
        stopping_criteria = stopping_criteria if stopping_criteria is not None else StoppingCriteriaList()

        unfinished_sequences = torch.ones(input_ids.shape[0], device=input_ids.device)
        scores = None

        for _ in range(generate_kwargs['max_new_tokens']):
            model_inputs = self.model.prepare_inputs_for_generation(input_ids, **generate_kwargs)
            outputs = self.model(**model_inputs, return_dict=True, output_attentions=False, output_hidden_states=False)
            next_token_logits = outputs.logits[:, -1, :]

            # Apply logits processors
            next_token_scores = logits_processor(input_ids, next_token_logits)
            next_tokens = torch.argmax(next_token_scores, dim=-1)

            # Update input_ids
            input_ids = torch.cat([input_ids, next_tokens.unsqueeze(-1)], dim=-1)

            # Stream the current chunk
            self.put(next_tokens)

            # Stop if all sequences are finished
            if unfinished_sequences.max() == 0:
                break

        return input_ids
    
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2-7B-Instruct",
    torch_dtype="auto",
    device_map="auto",
    cache_dir="./cache",
    #flashattention=True,    
    #use_cuda=True,
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-7B-Instruct")

prompt = "Give me a short introduction to large language model."
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": prompt}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(device)

# Setting up the streamer for streaming output
#streamer = TextStreamer(tokenizer, skip_special_tokens=True)
streamer = ManualTextStreamer(tokenizer)
# Generating the response with streaming enabled
model.generate(
    model_inputs.input_ids,
    max_new_tokens=512,
    streamer=streamer
)

