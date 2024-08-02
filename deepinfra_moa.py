import os, json
import asyncio
import aiohttp

api_key = os.getenv("DEEPINFRA_API_KEY")
base_url = "https://api.deepinfra.com/v1/openai"

async def fetch_completion():
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
            print("Response:")
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
                                        print("\n\nMetadata:")
                                        print(f"Finish reason: {event['choices'][0]['finish_reason']}")
                                        print(f"Prompt tokens: {event.get('usage', {}).get('prompt_tokens')}")
                                        print(f"Completion tokens: {event.get('usage', {}).get('completion_tokens')}")
                                    elif 'content' in event['choices'][0].get('delta', {}):
                                        print(event['choices'][0]['delta']['content'], end='', flush=True)
                            except json.JSONDecodeError:
                                print(f"Failed to parse JSON: {data}")

async def main():
    await fetch_completion()

if __name__ == "__main__":
    asyncio.run(main())