import asyncio
import os
from dotenv import load_dotenv
import openai

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("API key is not loaded!")
else:
    print("API key loaded successfully.")
openai.api_key = api_key

async def stop_on_keypress(task):
    try:
        # Await a specific key press; in this case, using a simple asyncio sleep to simulate.
        await asyncio.sleep(10)  # Here you would integrate your actual keypress detection.
    except asyncio.CancelledError:
        print('Keypress wait was cancelled.')
    finally:
        task.cancel()

async def async_chat_completion(question):
    def fetch_stream():
        return openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question}
            ],
            stream=True
        )

    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(None, fetch_stream)
    
    # Create a task for cancelling this future on a keypress
    stop_task = asyncio.create_task(stop_on_keypress(future))

    try:
        response = await future
        return response
    except asyncio.CancelledError:
        print('The fetch_stream operation was cancelled.')
        return None
    finally:
        if not stop_task.done():
            stop_task.cancel()

async def main():
    response_stream = await async_chat_completion("What are new features of Apache Spark?")
    if response_stream:
        print("Response from GPT-4:")
        try:
            for chunk in response_stream:
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
        except Exception as e:
            print(f"Error handling stream: {e}")


import wx
import asyncio
import threading

class Mywin(wx.Frame): 
    def __init__(self, parent, title): 
        super(Mywin, self).__init__(parent, title = title, size = (250,150)) 
        self.InitUI() 
        self.cancelled = False

    def InitUI(self): 
        panel = wx.Panel(self) 
        vbox = wx.BoxSizer(wx.VERTICAL) 

        self.stop_button = wx.Button(panel, label='Stop')
        self.stop_button.Bind(wx.EVT_BUTTON, self.OnStop)

        self.text = wx.TextCtrl(panel, style = wx.TE_MULTILINE) 

        vbox.Add(self.stop_button, 0, flag = wx.EXPAND|wx.ALL, border = 5)
        vbox.Add(self.text, 1, flag = wx.EXPAND|wx.ALL, border = 5) 

        panel.SetSizer(vbox) 

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.Show(True) 

    def OnClose(self, event):
        self.Destroy()

    def OnStop(self, event):
        # Signal the chat completion task to stop
        self.cancelled = True

    def append_text(self, text):
        self.text.AppendText(text + '\n')

    def run_chat_completion(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def wrapped_chat_completion():
            response_stream = await async_chat_completion("What are new features of apache spark?")
            for chunk in response_stream:
                if self.cancelled:
                    break
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    wx.CallAfter(self.append_text, content)

        loop.run_until_complete(wrapped_chat_completion())

app = wx.App() 
win = Mywin(None, 'Chat with GPT-4') 

thread = threading.Thread(target=win.run_chat_completion)
thread.start()

app.MainLoop()
