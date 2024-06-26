from anthropic import Anthropic

client = Anthropic()
MODEL_NAME = "claude-3-sonnet-20240229"

def image_fusion_description(image_descriptions, chat_history=[]):
    descriptions_text = "\n\n".join([f"Image {i+1}: {desc}" for i, desc in enumerate(image_descriptions)])
    
    prompt = f"""I want you to imagine and describe in detail a single image that fuses elements from multiple image descriptions. 
    Here are the descriptions of the input images:

    {descriptions_text}

    Please create a vivid, detailed description of a single imaginary image that combines elements from all of these descriptions. 
    Focus on how the elements from each description interact and blend together. 
    Be specific about colors, shapes, textures, and composition. 
    Your description should be cohesive, as if describing a real painting or photograph that fuses these elements.

    Before providing the final description in <fused_image> tags, think through your process step-by-step in <thinking> tags."""

    message_list = chat_history + [
        {
            "role": 'user',
            "content": prompt
        }
    ]

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2048,
        messages=message_list
    )
    
    assistant_message = {
        "role": "assistant",
        "content": response.content[0].text
    }
    
    chat_history.append(message_list[-1])  # Add user's message to history
    chat_history.append(assistant_message)  # Add assistant's response to history
    
    return response.content[0].text, chat_history

# Example usage
chat_history = []

image_descriptions = [
    "A serene beach at sunset with golden sand and calm, turquoise waters. Palm trees line the shore, their leaves silhouetted against the orange and pink sky.",
    "A bustling city street at night, with neon signs illuminating the sidewalks. Skyscrapers tower overhead, their windows twinkling like stars. Cars and taxis rush by, leaving streaks of light in their wake.",
    "A lush green forest with a winding river cutting through it. Sunlight filters through the canopy, creating dappled patterns on the forest floor. A majestic waterfall cascades over moss-covered rocks in the distance."
]

fused_description, chat_history = image_fusion_description(image_descriptions, chat_history)
print("Fused Image Description:")
print(fused_description)

# If you want to continue the conversation or get more details about the fused image
follow_up_prompt = "Can you elaborate on how the urban elements blend with the natural landscapes in this fused image?"
response, chat_history = image_fusion_description([follow_up_prompt], chat_history)
print("\nFollow-up Response:")
print(response)