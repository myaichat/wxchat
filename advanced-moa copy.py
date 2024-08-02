# Advanced Mixture-of-Agents example – 3 layers
import asyncio
import os
import together
from together import AsyncTogether, Together
from pprint import pprint   as pp

client = Together(api_key=os.environ.get("TOGETHER_API_KEY"))
async_client = AsyncTogether(api_key=os.environ.get("TOGETHER_API_KEY"))

user_prompt = """
Fuse this image prompt with new ideas.be as creative and wierd as possible return 100 word paragraph:

ukrainian flag, SurrealArt, DoubleExposure, VisualSplitting, DynamicArt, EtherealBeauty, ArtisticMotion, WaterfallArt, CreativePhotography, ModernArt, ConceptualArt, VisualArt, PhotoManipulation, UniqueArt, VisualStorytelling, ArtisticExpression, MovementArt, DigitalArt, VisualEffects, SurrealMotion, InnovativeArt, DynamicVisuals, WomanInArt, VisualArtistry, ArtisticVision, ArtisticPortrait, CreativeConcepts, FutureArt, ArtisticBeauty, VisualMagic
"""
reference_models = [
    "Qwen/Qwen2-72B-Instruct",
    "Qwen/Qwen1.5-72B-Chat",
    "mistralai/Mixtral-8x22B-Instruct-v0.1",
    "databricks/dbrx-instruct",
]
aggregator_model = "mistralai/Mixtral-8x22B-Instruct-v0.1"
aggreagator_system_prompt = """You have been provided with a set of responses from various open-source models to the latest user query. Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.

Responses from models:"""
layers = 3


def getFinalSystemPrompt(system_prompt, results):
    """Construct a system prompt for layers 2+ that includes the previous responses to synthesize."""
    return (
        system_prompt
        + "\n"
        + "\n".join([f"{i+1}. {str(element)}" for i, element in enumerate(results)])
    )


async def run_llm(layer, model, prev_response=None):
    """Run a single LLM call with a model while accounting for previous responses + rate limits."""
    print(f'\t{layer}: run_llm:', model)
    if prev_response:
        sys_prompt=getFinalSystemPrompt(
                                aggreagator_system_prompt, prev_response
                            )
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
            if 1:
                response = await async_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=512,
                )
            print(f"\t\t{layer}: {sleep_time}: Model: ", model)
            break
        except together.error.RateLimitError as e:
            print(e)
            await asyncio.sleep(sleep_time)
    #return f'\t{layer}: response: {model}, "{user_prompt}"' 
    assert response.choices[0].message.content
    return response.choices[0].message.content


async def main():
    """Run the main loop of the MOA process."""
    print("Running main loop...")
    results = await asyncio.gather(*[run_llm(0, model) for model in reference_models])
    print("Running layers...")
    for i in range(1, layers - 1):
        print(f"Layer {i}")
        results = await asyncio.gather(
            *[run_llm(i, model, prev_response=results) for model in reference_models]
        )
    print("Final layer")
    sys_prompt=getFinalSystemPrompt(aggreagator_system_prompt, results)
    pp(sys_prompt)
    finalStream = client.chat.completions.create(
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
    for chunk in finalStream:
        print(chunk.choices[0].delta.content or "", end="", flush=True)


asyncio.run(main())
