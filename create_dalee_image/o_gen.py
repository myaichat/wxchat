import openai
import io
from PIL import Image

def generate_image(prompt):
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_data = response['data'][0]['data']
    image = Image.open(io.BytesIO(image_data))
    return image

if __name__ == "__main__":
    prompt = "A medium of a sunflower field at sunset, vibrant colors, dynamic composition with a soft breeze effect. Taken on a DSLR camera with a wide-angle lens, capturing the warm golden hour light."
    image = generate_image(prompt)
    image.show()