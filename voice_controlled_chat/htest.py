import sys
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter
from pygments.token import Token

def highlight_stream(stream):
    lexer = PythonLexer()
    formatter = TerminalFormatter()

    # Store incomplete lines between chunks
    buffer = ''

    while True:
        chunk = stream.read(10)  # Adjust chunk size as needed
        if not chunk:
            break

        # Accumulate the chunk to the buffer
        buffer += chunk
        tokens = list(lexer.get_tokens_unprocessed(buffer))

        # Only process up to the last complete token
        last_end = 0
        for index, token, value in tokens:
            if token in Token.Text.Whitespace and '\n' in value:
                # Output up to the last complete line
                last_end = value.rfind('\n') + index + 1
                break

        # Highlight and print the complete part of the buffer
        to_highlight = buffer[:last_end]
        if to_highlight:
            highlighted = highlight(to_highlight, lexer, formatter)
            sys.stdout.write(highlighted)
            sys.stdout.flush()
        
        # Keep only the incomplete part in the buffer
        buffer = buffer[last_end:]

    # After the loop, print any remaining part of the buffer
    if buffer:
        highlighted = highlight(buffer, lexer, formatter)
        sys.stdout.write(highlighted)
        sys.stdout.flush()

# For demonstration, let's use a simulated stream using StringIO
import io
code_stream = io.StringIO("""
The fastest built-in way to sort in Python is by using the `sorted()` function or the `list.sort()` method. Both of these use Timsort, a hybrid sorting algorithm derived from merge sort and insertion sort, which has an average and worst-case time complexity of O(n log n).

Here's a quick overview of how to use each method:

1. **Using `sorted()` function:**
   The `sorted()` function returns a new sorted list from the elements of any iterable (like a list, tuple, dictionary, etc.), without modifying the original one.

   ```python
   my_list = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
   sorted_list = sorted(my_list)
   print(sorted_list)
   # Output: [1, 1, 2, 3, 3, 4, 5, 5, 5, 6, 9]
   ```

2. **Using `list.sort()` method:**
   The `list.sort()` method sorts the list in place and does not return a new list. It modifies the original list directly.

   ```python
   my_list = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
   my_list.sort()
   print(my_list)
   # Output: [1, 1, 2, 3, 3, 4, 5, 5, 5, 6, 9]
   ```

Both approaches are optimized and very fast for general-purpose sorting and should be sufficient for most use cases. If you need to sort more complex data structures or require custom sorting behavior, you can make use of the `key` parameter to provide a custom sorting function.

Here are a couple more custom sorting examples:

3. **Custom sorting using the `sorted()` function with `key` parameter:**

   ```python
   my_list = [('apple', 2), ('banana', 1), ('cherry', 3)]
   sorted_list = sorted(my_list, key=lambda x: x[1])
   print(sorted_list)
   # Output: [('banana', 1), ('apple', 2), ('cherry', 3)]
   ```

4. **Custom sorting using the `list.sort()` method with `key` parameter:**

   ```python
   my_list = [('apple', 2), ('banana', 1), ('cherry', 3)]
   my_list.sort(key=lambda x: x[1])
   print(my_list)
   # Output: [('banana', 1), ('apple', 2), ('cherry', 3)]
   ```

In summary, for in-place sorting you can use the `list.sort()` method, and for creating a new sorted list from an iterable, the `sorted()` function is appropriate. Both are optimized and utilize Timsort, making them the fastest built-in options for sorting in Python.None
""")
highlight_stream(code_stream)
