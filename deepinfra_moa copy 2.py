import os
import json
import yaml
import asyncio
import aiohttp
from aiohttp import ClientResponseError, TCPConnector
from include.common import get_final_system_prompt
from pprint import pprint as pp

api_key = os.getenv("DEEPINFRA_API_KEY")
base_url = "https://api.deepinfra.com/v1/openai"
aggregator_model = "Qwen/Qwen2-7B-Instruct"

user_prompt = """
Fuse this image prompt with new ideas. Be as creative and weird as possible. Return a 100-word paragraph:

ukrainian flag, SurrealArt, DoubleExposure, VisualSplitting, DynamicArt, EtherealBeauty, ArtisticMotion, WaterfallArt, CreativePhotography, ModernArt, ConceptualArt, VisualArt, PhotoManipulation, UniqueArt, VisualStorytelling, ArtisticExpression, MovementArt, DigitalArt, VisualEffects, SurrealMotion, InnovativeArt, DynamicVisuals, WomanInArt, VisualArtistry, ArtisticVision, ArtisticPortrait, CreativeConcepts, FutureArt, ArtisticBeauty, VisualMagic
"""

aggregator_system_prompt = """You have been provided with a set of responses from various open-source models to the latest user query. Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.

Responses from models:"""

class DeepInfraAPIError(Exception):
    """Custom exception for DeepInfra API errors"""
    def __init__(self, code, message, param=None, error_type=None):
        self.code = code
        self.message = message
        self.param = param
        self.error_type = error_type
        super().__init__(self.message)

class AsyncDeepinfra:
    def __init__(self, api_key, connector=None):
        self.api_key = api_key
        self.connector = connector
        self.session = None

    async def initialize(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(connector=self.connector)

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def create(self, model, messages, temperature, max_tokens, stream=False, retry=3):
        print(f"Creating completion for model {model}")
        await self.initialize()
        while retry:
            try:
                response = await self.session.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": stream,
                    },
                )
                response.raise_for_status()
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    json_response = await response.json()
                    if 'error' in json_response:
                        error = json_response['error']
                        raise DeepInfraAPIError(
                            code=error.get('code'),
                            message=error.get('message'),
                            param=error.get('param'),
                            error_type=error.get('type')
                        )
                    return json_response
                elif 'text/event-stream' in content_type:
                    return response
                else:
                    raise DeepInfraAPIError(
                        code='unexpected_content_type',
                        message=f"Unexpected content type: {content_type}",
                        error_type='unexpected_content_type'
                    )
            except (ClientResponseError, aiohttp.ClientError) as e:
                retry -= 1
                if not retry:
                    raise DeepInfraAPIError(
                        code='network_error',
                        message=str(e),
                        error_type='network_error'
                    )
                await asyncio.sleep(1)

async def get_final_stream(client, results):
    sys_prompt = get_final_system_prompt(aggregator_system_prompt, results)
    try:
        response = await client.create(
            model=aggregator_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=512,
            stream=True,
        )

        if isinstance(response, aiohttp.ClientResponse):
            async for chunk in response.content.iter_any():
                if chunk:
                    chunk = chunk.decode('utf-8').strip()
                    if chunk.startswith("data:"):
                        data = chunk[6:]  # Remove "data: " prefix
                        if data != "[DONE]":
                            try:
                                event = json.loads(data)
                                if 'choices' in event:
                                    if event['choices'][0].get('finish_reason'):
                                        if 0:
                                            print("\n\nMetadata:")
                                            print(f"Finish reason: {event['choices'][0]['finish_reason']}")
                                            print(f"Prompt tokens: {event.get('usage', {}).get('prompt_tokens')}")
                                            print(f"Completion tokens: {event.get('usage', {}).get('completion_tokens')}")
                                    elif 'content' in event['choices'][0].get('delta', {}):
                                        yield event['choices'][0]['delta']['content']
                            except json.JSONDecodeError:
                                print(f"Failed to parse JSON: {data}")
    finally:
        await client.close()

async def run_llm(client, layer, model, prev_response=None):
    """Run a single LLM call with a model while accounting for previous responses + rate limits."""
    print(f'\t{layer}: run_llm:', model)
    sys_prompt = None
    if prev_response:
        sys_prompt = get_final_system_prompt(aggregator_system_prompt, prev_response)
    out = []
    messages = (
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if prev_response
        else [{"role": "user", "content": user_prompt}]
    )
    response = await client.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=512,
    )
    if isinstance(response, dict):
        return response['choices'][0]['message']['content']
    else:
        raise DeepInfraAPIError(
            code='unexpected_response',
            message="Expected a JSON response but got a stream",
            error_type='unexpected_response'
        )

yaml_file_path = 'deepinfra_reference_models.yaml'

# Read the YAML file
with open(yaml_file_path, 'r') as file:
    data = yaml.safe_load(file)

reference_models = data['reference_models']
layers = 3

async def main():
    """Run the main loop of the MOA process."""
    print("Running main loop...")
    connector = TCPConnector(ssl=False)  # Disable SSL verification for testing
    client = AsyncDeepinfra(api_key, connector)
    await client.initialize()
    try:
        apis = [dict(run=run_llm, model=model['name']) for model in reference_models]

        results = await asyncio.gather(*[api['run'](client, 0, api['model']) for api in apis])
        print("Running layers...")

        for i in range(1, layers - 1):
            print(f"Layer {i}")
            results = await asyncio.gather(*[api['run'](client, 0, api['model'], prev_response=results) for api in apis])

        print("Final layer")
        async for chunk in get_final_stream(client, results):
            if chunk:
                print(chunk, end='', flush=True)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
