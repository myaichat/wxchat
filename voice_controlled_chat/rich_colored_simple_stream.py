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


    from pygments.lexers import PythonLexer, get_lexer_by_name
    from pygments.formatters import TerminalFormatter
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.syntax import Syntax

    buffer = ''
    lexer = get_lexer_by_name("text")
    formatter = TerminalFormatter()
    console = Console()
    code_lines = []

    for chunk in response:
        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            buffer += content

            # Check for Python code block start and end markers
            if '```python' in buffer:
                # Start of a Python code block
                lexer = PythonLexer()
                buffer = buffer.replace('```python', '')
            elif '```' in buffer and isinstance(lexer, PythonLexer):
                # End of a Python code block
                buffer = buffer.replace('```', '')
                # Find the last newline to determine the end of complete statements
                last_newline = buffer.rfind('\n')
                if last_newline != -1:
                    to_process = buffer[:last_newline + 1]  # Include the newline in processing
                    code_lines.append(to_process)
                    buffer = buffer[last_newline + 1:]  # Keep the remainder
                lexer = get_lexer_by_name("text")  # Switch back to text lexer after processing Python code
            else:
                # Process as Markdown
                last_newline = buffer.rfind('\n')
                if last_newline != -1:
                    to_process = buffer[:last_newline + 1]  # Include the newline in processing
                    markdown = Markdown(to_process)
                    console.print(markdown)
                    buffer = buffer[last_newline + 1:]  # Keep the remainder

    # After the loop, process any remaining part of the buffer
    if buffer:
        markdown = Markdown(buffer)
        console.print(markdown)

    # Print the Python code lines
    if code_lines:
        code = '\n'.join(code_lines)
        syntax = Syntax(code, "python")
        console.print(syntax)
                    
if __name__ == "__main__":
    stream_response("Hey, what is the fastes was to sort in python?")


