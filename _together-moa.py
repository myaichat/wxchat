
import sys, yaml
import asyncio

import include.api.together as together 
#import run_llm, get_final_stream

from pprint import pprint as pp
e=sys.exit

'''
all_models = {
    'together': [
        {'name': "Qwen/Qwen2-72B-Instruct",}, 
        {'name': "Qwen/Qwen1.5-72B-Chat"},
        {'name': "mistralai/Mixtral-8x22B-Instruct-v0.1"},
        {'name': "databricks/dbrx-instruct"},
    ]
}


reference_models =  [
        {'name': "Qwen/Qwen2-72B-Instruct", 'api': 'together'}, 
        {'name': "Qwen/Qwen1.5-72B-Chat", 'api': 'together'},
        {'name': "mistralai/Mixtral-8x22B-Instruct-v0.1", 'api': 'together'},
        {'name': "databricks/dbrx-instruct", 'api': 'together'},
    ]
'''

yaml_file_path = 'reference_models.yaml'

# Read the YAML file
with open(yaml_file_path, 'r') as file:
    data = yaml.safe_load(file)

reference_models = data['reference_models']
layers = 3


async def main():
    """Run the main loop of the MOA process."""
    print("Running main loop...")
    apis=[]
    for model in reference_models:
        pp(model)
        api=getattr(globals()[model['api']], 'run_llm')
        apis.append(dict(run=api, model=model['name']))

    results = await asyncio.gather(*[api['run'](0, api['model']) for api in apis])
    print("Running layers...")
    for i in range(1, layers - 1):
        print(f"Layer {i}")
        
        results = await asyncio.gather(*[api['run'](0, api['model'], prev_response=results) for api in apis])

    print("Final layer")

    final_stream = await together.get_final_stream(results)
    async for chunk in final_stream:
        print(chunk.choices[0].delta.content or "", end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
