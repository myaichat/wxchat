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

    from pygments import highlight
    from pygments.lexers import PythonLexer, get_lexer_by_name
    from pygments.formatters import TerminalFormatter
    from colorama import init, Fore, Back, Style

    init()  # Initialize colorama for Windows

    buffer = ''
    in_code_block = False
    lexer = get_lexer_by_name("text")
    formatter = TerminalFormatter()

    for chunk in response:
        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            buffer += content

            # Check for Python code block start and end markers
            if '```python' in buffer:
                # Start of a Python code block
                in_code_block = True
                lexer = PythonLexer()
                buffer = buffer.replace('```python', '')
                sys.stdout.write('```python\n')
            elif '```' in buffer and in_code_block:
                # End of a Python code block
                in_code_block = False
                buffer = buffer.replace('```', '')

                # Find the last newline to determine the end of complete statements
                last_newline = buffer.rfind('\n')
                if last_newline != -1:
                    to_process = buffer[:last_newline + 1]  # Include the newline in processing
                    highlighted_code = highlight(to_process, lexer, formatter)
                    sys.stdout.write(highlighted_code)
                    sys.stdout.flush()
                    buffer = buffer[last_newline + 1:]  # Keep the remainder

                lexer = get_lexer_by_name("text")  # Switch back to text lexer after processing Python code
                sys.stdout.write('```\n')
            else:
                # Process as Markdown
                last_newline = buffer.rfind('\n')
                if last_newline != -1:
                    to_process = buffer[:last_newline + 1]  # Include the newline in processing
                    sys.stdout.write(to_process)
                    sys.stdout.flush()
                    buffer = buffer[last_newline + 1:]  # Keep the remainder

    # After the loop, process any remaining part of the buffer
    if buffer:
        if in_code_block:
            highlighted_code = highlight(buffer, lexer, formatter)
            sys.stdout.write(highlighted_code)
        else:
            sys.stdout.write(buffer)
        sys.stdout.flush()

if __name__ == "__main__":
    stream_response("Hey, what is the fastest way to sort in Python?")