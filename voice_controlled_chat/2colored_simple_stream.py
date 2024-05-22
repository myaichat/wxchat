import openai
import os, sys
from dotenv import load_dotenv
load_dotenv()
from pprint import pprint as pp

from pygments import highlight
from pygments.lexers import MarkdownLexer, PythonLexer
from pygments.formatters import TerminalFormatter
from pygments.styles import get_style_by_name
from pygments.token import Token

# Set your OpenAI API key here
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the client
client = openai.OpenAI()

def stream_response(prompt):
    # Create a chat completion request with streaming enabled
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a chatbot that assists with Python interview."},
            {"role": "user", "content": prompt}
        ],
        stream=True
    )

    last_val = ''
    lexer = MarkdownLexer()  # Start with MarkdownLexer
    formatter = TerminalFormatter()

    # Print each response chunk as it arrives
    for chunk in response:
        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            text = last_val + content

            # Check for Python code block start and end markers
            if '```python' in text:
                # Start of a Python code block
                lexer = PythonLexer()
                text = text.replace('```python', '')
            elif '```' in text and isinstance(lexer, PythonLexer):
                # End of a Python code block
                lexer = MarkdownLexer()  # Switch back to MarkdownLexer after processing Python code
                text = text.replace('```', '')

            # Highlight and print each chunk as it arrives
            sys.stdout.write(highlight(text, lexer, formatter))
            last_val = content  # Update last_val with content

# Call the function with a prompt
stream_response("How to write a for loop in Python?")