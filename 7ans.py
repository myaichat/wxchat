import wx
import wxasync
import asyncio
from pprint import pprint as pp

from pubsub import pub

import textwrap

import wx.grid as gridlib


import openai
import os, re, time
from dotenv import load_dotenv
load_dotenv()

# Set your OpenAI API key here
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("API key is not loaded!")
else:
    print("API key loaded successfully.")
openai.api_key = api_key

class MainFrame(wx.Frame):
    def __init__(self, size=(800, 600)):
        super().__init__(None, title="OpenAI Question Asker", size=size)

        # Creating the main panel and sizer
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)  # Main sizer for the panel

        # Setup for question input
        question_label = wx.StaticText(panel, label="Question:")
        self.question_input = wx.TextCtrl(panel, value='Hey, what are new features of Apache Spark?', style=wx.TE_PROCESS_ENTER)
        input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_sizer.Add(question_label, 0, wx.ALL | wx.CENTER, 5)
        input_sizer.Add(self.question_input, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(input_sizer, 0, wx.EXPAND | wx.ALL, 5)  # Add to main sizer with expand flag
        self.start_time = time.time()
        self.client=None
        # Setup for output grid
        self.setup_output_grid(panel)
        main_sizer.Add(self.answer_output, 1, wx.EXPAND | wx.ALL, 5)  # Ensure grid expands

        # Setup for buttons
        self.setup_buttons(panel, main_sizer)

        panel.SetSizer(main_sizer)  # Set the main sizer to the panel

        self.Centre()  # Center the frame on screen
        self.Show()
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.question_input.SetInsertionPoint(0)
    def on_resize(self, event):
        # Layout the sizer
        self.Layout()

        # Skip the event
        event.Skip()        
    async def get_chat_completion_client(self, prompt):
        if not self.client:
            self.client = openai.ChatCompletion.create(
                model=self.model_selector.GetValue(),
                messages=[
                    {"role": "system", "content": "You are a chatbot that assists with Apache Spark queries."},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
        return self.client        
    def add_row(self, text):
        #print(123, text)
        #print('Adding row')
        elapsed_time = round(time.time() - self.start_time, 2)
        i = self.answer_output.GetNumberRows()
        self.answer_output.AppendRows(1)
        print('Adding row', i, text)
        self.answer_output.SetCellValue(i, 0, str(i+1))
        self.answer_output.SetCellValue(i, 1, str(elapsed_time))  # Convert elapsed_time to string
        self.answer_output.SetCellValue(i, 2, self.model_selector.GetValue())
        self.answer_output.SetCellValue(i, 3, text)
        #self.answer_output.AutoSizeColumns()  # Automatically adjust the width of columns to fit content
        self.answer_output.AutoSizeRows() 
        #print(1111)
        #pp( text)
        #if text.strip():
        print('Resetting time -------------------')
        pp(text)
        self.start_time = time.time()
    def append_text(self, text):
        if '\n' in text:
            text = re.sub('\n+', '\n', text)
            lines = text.split('\n')
            #pp(lines)
            self.append_to_row(lines[0])
            #self.add_row('')
            if 1:
                for line in lines[1:]:
                    if line:
                        self.add_row(line)
            self.add_row('')
        else:
            #row_count = self.answer_output.GetNumberRows()
            last_index = self.answer_output.GetNumberRows() - 1
            if last_index >= 0:
                self.append_to_row(text)
            else:
                self.add_row(text)
    def append_to_row(self, text):
        # Append the text to the row
        last_index = self.answer_output.GetNumberRows() - 1
        current_text = self.answer_output.GetCellValue(last_index, 3)
        new_text = current_text + text
        #print(last_index, new_text)
        # Wrap the new text
        wrapped_text = textwrap.fill(new_text, width=50)  # Adjust the width as needed

        # Set the cell value to the wrapped text
        self.answer_output.SetCellValue(last_index, 3, wrapped_text)

    async def stream_response(self, prompt, output_ctrl, frame):
        # Create a chat completion request with streaming enabled
        #out=[]
        try:

            #self.add_row(f'\n-->Start ({self.model_selector.GetValue()}).\n')
            #pub.sendMessage("append_text", text=f'\n-->Start ({self.model_selector.GetValue()}).\n')
            for chunk in await self.get_chat_completion_client(prompt):
                if frame.stop_output or frame.pause_output:
                    break            
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    #out.append(content)
                    #output_ctrl.AppendText(content)
                    #pub.sendMessage("append_text", text=content)
                    self.append_text(content)
                    await asyncio.sleep(0)

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:

            if not frame.pause_output:
                self.client = None
                print('--> Stopped')
                #self.answer_output.AppendText('\n-->Done.\n\n\n')
                if not frame.stop_output:
                    print('\n-->Done.\n\n\n')
                    #pub.sendMessage("append_text", text='\n-->Done.\n\n\n')
                else:
                    print('\n-->Done(Stop).\n\n\n')
                    #pub.sendMessage("append_text", text='\n-->Done(Stop).\n\n\n')
            else:
                print('--> Paused')
             


    async def on_ask(self, event):
        #self.statusbar.SetStatusText('Asking...')
        self.stop_output = False
        self.pause_output = False 
        question = self.question_input.GetValue()
        self.response_stream =  await self.stream_response(question, self.answer_output, self)
        #self.answer_output.AppendText('\n'*3)
        #self.client=None
                
    def on_stop(self, event):

        self.stop_output = True 
        self.pause_output = False
        
        pp(self.response_stream) 
        if self.response_stream :
            self.response_stream.cancel()
            self.response_stream = None
        self.client=None
        #pub.sendMessage("append_text", text='\n-->Done.\n\n\n')
        #self.statusbar.SetStatusText('Stopped')        
    def on_ask_wrapper(self, event):
        asyncio.create_task(self.on_ask(event))
    def setup_output_grid(self, panel):
        # Create and configure the grid for output
        self.answer_output = gridlib.Grid(panel)
        self.answer_output.CreateGrid(0, 4)  # Pre-creating some rows and columns
        col_labels = ["Num", "Sec", "Model", "Text"]
        for col, label in enumerate(col_labels):
            self.answer_output.SetColLabelValue(col, label)
        self.answer_output.SetColSize(3, 400)  # Set initial size for the 'Text' column
        #self.answer_output.AutoSizeColumns()  # Optional: auto-size columns based on content

    def setup_buttons(self, panel, sizer):
        # Create button sizer
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_names = ["gpt-3", "gpt-4", "gpt-4-turbo", "gpt-4-turbo-2024-04-09",
                       'gpt-4-turbo-preview', 'gpt-4-0125-preview', 'gpt-4-1106-preview',
                       'gpt-4-32k-0613', 'gpt-4-32k']
        self.model_selector = wx.ComboBox(panel, choices=model_names, style=wx.CB_READONLY)
        self.model_selector.SetValue("gpt-4")
        ask_button = wx.Button(panel, label="Ask Question")
        stop_button = wx.Button(panel, label="Stop")

        button_sizer.Add(self.model_selector, 0, wx.EXPAND | wx.ALL, 5)
        button_sizer.Add(ask_button, 1, wx.EXPAND | wx.ALL, 5)
        button_sizer.Add(stop_button, 0, wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Bind button events
        ask_button.Bind(wx.EVT_BUTTON, self.on_ask_wrapper)
        stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        self.question_input.Bind(wx.EVT_TEXT_ENTER, self.on_ask_wrapper)

if __name__ == "__main__":
    app = wxasync.WxAsyncApp()
    frame = MainFrame()
    frame.SetSize(800, 600)
    frame.Show()
    asyncio.get_event_loop().run_until_complete(app.MainLoop())
