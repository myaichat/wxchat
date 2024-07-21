import sys
from pprint import pprint as pp
import json
e=sys.exit
def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True
def get_current_weather(location: str, unit: str = "celsius"):
    print("EXECUTING get_current_weather: Location:", location, "Unit:", unit)
    if location == "Madrid":
        temperature = 35
    elif location == "San Francisco":
        temperature = 18
    elif location.startswith("Paris"):
        temperature = 20
    else:
        temperature = 15
    if unit == "fahrenheit":
        temperature =  temperature  * 9/5 + 32
    return temperature


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
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "default": "celsius",  # Default value for unit
                        "description": "The unit of temperature. Defaults to 'celsius'."
                    }
                },
                "required": ["location"]
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
    "type": "function"
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "properties": {
                "location": {
                    "description": "The city and state, e.g. San Francisco",
                    "type": "string"
                },
                "unit": {
                    "enum": [
                        "celsius",
                        "fahrenheit"
                    ],
                    "type": "string"
                }
            },
            "required": [
                "location"
            ],
            "type": "object"
        }
    } 
}</tools>

'''},
    { "role": "user", "content": "What is the temperature in Paris right now in celcius?"},

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
print(tool_call)



if is_json(tool_call):
    function_call = tool_call.strip()
    function_data = json.loads(function_call)
    pp(function_data)
    if function_data["name"] == "get_current_weather":
        
        location = function_data["arguments"]["location"]
        unit = function_data["arguments"]["unit"]
        temperature = get_current_weather(location,unit)
        
        function_response = f"<tool_response> {{\"location\":\"{location}\", \"temperature\":\"{temperature}\", \"unit\":\"{unit}\",}} </tool_response>"
        
        messages.append({
            "role": "assistant",
            "content": tool_call
        })
        messages.append({
            "role": "user",
            "content": function_response
        })

        #pp(messages)
        
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
