from pprint import pprint
import sys, json
def get_temperature(city):
    # This is a mock function. Replace with your actual implementation
    # For demonstration purposes, we'll return a random temperature
    import random
    return f"{random.randint(0, 40)} C"


from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model_id = "Groq/Llama-3-Groq-8B-Tool-Use"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    cache_dir="./cache",
)


functions_metadata = [
    {
    "type": "function",
    "function": {
        "name": "get_temperature",
        "description": "get temperature of a city",
        "parameters": {
        "type": "object",
        "properties": {
            "city": {
            "type": "string",
            "description": "name"
            }
        },
        "required": [
            "city"
        ]
        }
    }
    }
]

messages = [
    { "role": "system", "content": '''

You are a function calling AI model. You are provided with function signatures within <tools></tools> XML tags.
    You may call one or more functions to assist with the user query. Don't make assumptions about what values
    to plug into functions. For each function call return a json object with function name and arguments within
    <tool_call></tool_call> XML tags as follows:

<tool_call>{"type":"tool_call", "name": <function-name>,"arguments": <args-dict>}</tool_call>

Here are the available tools:
<tools> {
    "name": "get_temperature",
    "description": "get temperature of a city",
    "parameters": {
        "type": "object",
        "properties": {
        "city": {
            "type": "string",
            "description": "name"
        }
        },
        "required": [
        "city"
        ]
    }
} </tools>

'''},
    { "role": "user", "content": "What is the temperature in Paris right now? <|eot_id|><|start_header_id|>assistant<|end_header_id|>"},
]

input_ids = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    return_tensors="pt"
).to(model.device)

terminators = [
    tokenizer.eos_token_id,
    tokenizer.convert_tokens_to_ids("<|eot_id|>")
]

outputs = model.generate(
    input_ids,
    max_new_tokens=256,
    eos_token_id=terminators,
    do_sample=True,
    temperature=0.6,
    top_p=0.9,
)
assistant_response = outputs[0][input_ids.shape[-1]:]
tool_call=tokenizer.decode(assistant_response, skip_special_tokens=True)
pprint(tool_call)

def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True

if 1:
    #messages = []


    #assistant_response='''{"id": 0, "name": "get_temperature", "arguments": {"city": "Tokyo"}}'''
    if is_json(tool_call):
        function_call = tool_call.strip()
        function_data = json.loads(function_call)
        pprint(function_data)
        if function_data["name"] == "get_temperature":
            
            city = function_data["arguments"]["city"]
            temperature = get_temperature(city)
            
            function_response = f"<function_response> {{\"temperature\":\"{temperature}\"}} </function_response>"
            
            messages.append({
                "role": "assistant",
                "content": tool_call
            })
            messages.append({
                "role": "user",
                "content": function_response
            })

            if 1:
                # Generate a new response based on the function result
                input_ids = tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True, return_tensors="pt"
                ).to(model.device)
                
                outputs = model.generate(
                    input_ids,
                    max_new_tokens=256,
                    eos_token_id=terminators,
                    do_sample=True,
                    temperature=0.6,
                    top_p=0.9,
                )
                
                response = outputs[0][input_ids.shape[-1]:]
                final_response = tokenizer.decode(response, skip_special_tokens=True)
                print("Final response:", final_response)
