if 0:
    from transformers import AutoTokenizer, AutoModelForCausalLM

    # This works just fine (normal version but too big for my GPU)
    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-128k-instruct",trust_remote_code=True, force_download=True)
    model = AutoModelForCausalLM.from_pretrained("microsoft/Phi-3-mini-128k-instruct",trust_remote_code=True, force_download=True)

#import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

#torch.random.manual_seed(0)
model_id = "microsoft/Phi-3-medium-128k-instruct"
model_id = "microsoft/Phi-3-mini-128k-instruct"
model_id = "microsoft/Phi-3-mini-4k-instruct"

#model_id = "microsoft/Phi-3-small-128k-instruct"


#model_id = "microsoft/Phi-3-small-8k-instruct"
#model_id = "microsoft/Phi-3-small-8k-instruct"

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="cuda", 
    torch_dtype="auto", 
    trust_remote_code=True, 
)
tokenizer = AutoTokenizer.from_pretrained(model_id)

messages = [
    {"role": "user", "content": "Can you provide ways to eat combinations of bananas and dragonfruits?"},
    {"role": "assistant", "content": "Sure! Here are some ways to eat bananas and dragonfruits together: 1. Banana and dragonfruit smoothie: Blend bananas and dragonfruits together with some milk and honey. 2. Banana and dragonfruit salad: Mix sliced bananas and dragonfruits together with some lemon juice and honey."},
    {"role": "user", "content": "What about solving an 2x + 3 = 7 equation?"},
]

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
)

generation_args = {
    "max_new_tokens": 500,
    "return_full_text": False,
    "temperature": 0.0,
    "do_sample": False,
}

output = pipe(messages, **generation_args)
print(output[0]['generated_text'])

