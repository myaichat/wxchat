import os, time
import asyncio
import groq
from groq import AsyncGroq, Groq
from include.common import get_final_system_prompt
from pprint import pprint as pp

aggregator_model = "llama3-70b-8192"

user_prompt = """
Fuse this image prompt with new ideas. Be as creative and weird as possible. Return a 100-word paragraph:

ukrainian flag, SurrealArt, DoubleExposure, VisualSplitting, DynamicArt, EtherealBeauty, ArtisticMotion, WaterfallArt, CreativePhotography, ModernArt, ConceptualArt, VisualArt, PhotoManipulation, UniqueArt, VisualStorytelling, ArtisticExpression, MovementArt, DigitalArt, VisualEffects, SurrealMotion, InnovativeArt, DynamicVisuals, WomanInArt, VisualArtistry, ArtisticVision, ArtisticPortrait, CreativeConcepts, FutureArt, ArtisticBeauty, VisualMagic
"""


aggregator_system_prompt = """You have been provided with a set of responses from various open-source models to the latest user query. Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.

Responses from models:"""
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))

async def get_final_stream(results):
    sys_prompt = get_final_system_prompt(aggregator_system_prompt, results)
    
    final_stream = await client.chat.completions.create(
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
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=512,
            )
            print(f"\t\t{layer}: {sleep_time}: Model: ", model)
            break
        except groq.RateLimitError as e:
            print(e)
            await asyncio.sleep(sleep_time)
    assert response.choices[0].message.content
    return response.choices[0].message.content