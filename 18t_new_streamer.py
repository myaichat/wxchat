from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import TextIteratorStreamer
import torch
import time
from threading import Thread, Event

class CustomTextStreamer(TextIteratorStreamer):
    def __init__(self, tokenizer, skip_special_tokens=True):
        super().__init__(tokenizer, skip_special_tokens)
        self.generated_text = ""
        print("CustomTextStreamer initialized")

    def on_finalized_text(self, text: str, stream_end: bool = False):
        print("CustomTextStreamer on_finalized_text invoked")
        text = text.replace("<end_of_turn>", "").replace("<eos>", "").strip()
        if text:
            self.generated_text += text
            print(text, end='', flush=True)

# Start the timer
start = time.time()

# Model ID
model_id = "google/gemma-2-9b-it"

print("Loading tokenizer and model")
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    cache_dir="./cache",
    trust_remote_code=True,
    low_cpu_mem_usage=True
)
print("Tokenizer and model loaded")

input_text = "Write me a poem about Machine Learning."
inputs = tokenizer(input_text, return_tensors="pt", padding=True)
attention_mask = torch.ones_like(inputs['input_ids'])
inputs = {k: v.to("cuda") for k, v in inputs.items()}
attention_mask = attention_mask.to("cuda")

streamer = CustomTextStreamer(tokenizer, skip_special_tokens=True)

print("Starting generation")
generation_kwargs = dict(
    input_ids=inputs['input_ids'],
    attention_mask=attention_mask,
    max_new_tokens=100,
    do_sample=True,
    temperature=1.0,
    top_p=0.95,
    top_k=50,
    streamer=streamer
)

stop_event = Event()

def generate_with_timeout():
    try:
        model.generate(**generation_kwargs)
    except Exception as e:
        print(f"Exception in generate: {e}")
    finally:
        stop_event.set()

thread = Thread(target=generate_with_timeout)
thread.start()

# Wait for generation to complete or timeout
timeout = 300  # 5 minutes
start_time = time.time()
while not stop_event.is_set() and time.time() - start_time < timeout:
    time.sleep(1)
    print(".", end='', flush=True)

if not stop_event.is_set():
    print("\nGeneration timed out after {} seconds".format(timeout))
else:
    print("\nGeneration finished")

final_text = streamer.generated_text.replace("<end_of_turn>", "").replace("<eos>", "").strip()
print("\n\nGenerated Text:", final_text)
print("\nTime:", time.time() - start)

# Force stop the thread if it's still running
if thread.is_alive():
    print("Forcing thread to stop")
    # This is a bit drastic, but it will stop the thread
    import os
    import signal
    os.kill(os.getpid(), signal.SIGINT)