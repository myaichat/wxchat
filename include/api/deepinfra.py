import os, time, json
import asyncio
import asyncio
import aiohttp
#import groq
#from groq import AsyncGroq, Groq
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


class AsyncDeepinfra:
    def __init__(self, api_key):
        self.api_key = api_key
    async def create(self, model, messages, temperature, max_tokens, stream=False):
        
        return self
    
    async def create(self, model, messages, temperature, max_tokens, stream=False):
        print(f"Creating completion for model {model}")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "Qwen/Qwen2-7B-Instruct",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": True,
                },
            ) as response:
                return response

                                            
client = AsyncDeepinfra(api_key=os.environ.get("DEEPINFRA_API_KEY"))

async def get_final_stream(results):
    sys_prompt = get_final_system_prompt(aggregator_system_prompt, results)
    
    final_stream = await client.create(
        model=aggregator_model,
        messages=[
            {
                "role": "system",
                "content": sys_prompt,
            },
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
    )

    return final_stream

async def run_llm(layer, model, prev_response=None):
    """Run a single LLM call with a model while accounting for previous responses + rate limits."""
    print(f'\t{layer}: run_llm:', model)
    sys_prompt = None
    if prev_response:
        sys_prompt = get_final_system_prompt(aggregator_system_prompt, prev_response)
        pp(sys_prompt)

    for sleep_time in [1, 2, 4]:
        try:
            messages = (
                [
                    {
                        "role": "system",
                        "content": sys_prompt,
                    },
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
            print(f"\t\t{layer}: {sleep_time}: Model: ", model)
            break
        except Exception as e:
            print(e)
            raise
            #await asyncio.sleep(sleep_time)

    out=[]
    async for line in response.content:
        if line:
            line = line.decode('utf-8').strip()
            if line.startswith("data: "):
                data = line[6:]  # Remove "data: " prefix
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
                                out.append(event['choices'][0]['delta']['content'])
                                #print(event['choices'][0]['delta']['content'], end='', flush=True)
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON: {data}")
                            
    return out