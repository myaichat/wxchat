import os
import asyncio
import yaml 

from os.path import join
from  include.api.together import AsyncTogether, get_final_stream
#from together import AsyncTogether
import include.api.together as together

api_key = os.getenv("TOGETHER_API_KEY")

yaml_file_path = join('config','together_reference_models.yaml')

# Read the YAML file
with open(yaml_file_path, 'r') as file:
    data = yaml.safe_load(file)

reference_models = data['reference_models']
layers = 3

aggregator_model = next((model['name'] for model in data['reference_models'] if model.get('aggregator')), None)

print(f"Aggregator model: {aggregator_model}")

async def main():
    """Run the main loop of the MOA process."""
    print("Running main loop...")
    async with AsyncTogether(api_key=api_key) as client:
    
        apis = [dict(run=getattr(globals()[model['api']], 'run_llm'), model=model['name']) for model in reference_models]



        results = await asyncio.gather(*[api['run'](client, 0, api['model']) for api in apis])
        print("Running layers...")

        for i in range(1, layers - 1):
            print(f"Layer {i}")
            results = await asyncio.gather(*[api['run'](client, 0, api['model'], prev_response=results) for api in apis])

        print("Final layer")
        async for chunk in get_final_stream(client, aggregator_model,results):
            if chunk:
                print(chunk, end='', flush=True)


if __name__ == "__main__":
    asyncio.run(main())
