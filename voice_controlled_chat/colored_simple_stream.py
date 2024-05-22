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
    if 0:
        last_val = ''
        lexer = PythonLexer()
        formatter = TerminalFormatter()
        # Print each response chunk as it arrives
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                text = last_val + content
                for index, token, value in lexer.get_tokens_unprocessed(text):
                    last_val = value
                highlighted = highlight(last_val, lexer, formatter)
                #highlighted_content = highlight(content, PythonLexer(), TerminalFormatter(style=get_style_by_name('monokai')))
                #pp(content)
                #pp(highlighted_content)
                if content.endswith('\n'):
                    #highlighted_content = highlighted_content[:-1]
                    pass
                else:
                    highlighted = highlighted.rstrip('\n')
                    pass
                #print(highlighted, end='', flush=True)
                sys.stdout.write(highlighted)
                sys.stdout.flush()            
                last_val = ''

    buffer = ''
    lexer = MarkdownLexer()
    formatter = TerminalFormatter()

    for chunk in response:
        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            buffer += content

            # Find the last newline to determine the end of complete statements
            last_newline = buffer.rfind('\n')
            if last_newline != -1:
                to_process = buffer[:last_newline + 1]  # Include the newline in processing
                highlighted = highlight(to_process, lexer, formatter)
                sys.stdout.write(highlighted)
                sys.stdout.flush()
                buffer = buffer[last_newline + 1:]  # Keep the remainder

    # After the loop, process any remaining part of the buffer
    if buffer:
        highlighted = highlight(buffer, lexer, formatter)
        sys.stdout.write(highlighted)
        sys.stdout.flush()
                    
if __name__ == "__main__":
    stream_response("Hey, what is the fastes was to sort in python?")


