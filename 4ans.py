import wx
import wxasync
import asyncio
from pprint import pprint as pp

from pubsub import pub

import textwrap

import openai
import os, time
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
        super().__init__(None, title="OpenAI Question Asker")




        panel = wx.Panel(self)
        question_label = wx.StaticText(panel, label="Question:")
        self.question_input = wx.TextCtrl(panel, value='Hey, what are new features of Apache Spark?', style=wx.TE_PROCESS_ENTER)

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(question_label, 0, wx.ALL|wx.CENTER, 5)
        h_sizer.Add(self.question_input, 1, wx.ALL|wx.EXPAND, 5)


        #self.answer_output = wx.TextCtrl(panel, style=wx.TE_MULTILINE|wx.TE_RICH2)
        if 1:
            self.answer_output = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_HRULES)
            self.answer_output.InsertColumn(0, 'Line Num', width=70)
            self.answer_output.InsertColumn(1, 'Elapsed Sec', width=100)
            self.answer_output.InsertColumn(2, 'Model Name', width=100)
            self.answer_output.InsertColumn(3, 'Text', width=500)
            self.start_time = time.time()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(h_sizer, 0, wx.EXPAND | wx.ALL, 1)

        if 1:

            # Create a horizontal box sizer
            button_sizer = wx.BoxSizer(wx.HORIZONTAL)            
            if 1:
                model_names = ["gpt-3", "gpt-4", "gpt-4-turbo", "gpt-4-turbo-2024-04-09",'gpt-4-turbo-preview','gpt-4-0125-preview',
                               'gpt-4-1106-preview','gpt-4-32k-0613','gpt-4-32k']
                self.model_selector = wx.ComboBox(panel, choices=model_names, style=wx.CB_READONLY)  
                self.model_selector.SetValue("gpt-4")
                button_sizer.Add(self.model_selector, 0, wx.EXPAND | wx.ALL, 5)          

            ask_button = wx.Button(panel, label="Ask Question")
            stop_button = wx.Button(panel, label="Stop")


            # Add the ask button to the sizer
            button_sizer.Add(ask_button, 1, wx.EXPAND | wx.ALL, 5)
            if 1:
                self.pause_output = False
                pause_button = wx.Button(panel, label="Pause")
                button_sizer.Add(pause_button, 0, wx.ALL, 5)
                pause_button.Bind(wx.EVT_BUTTON, self.on_pause)

            # Add the stop button to the sizer
            button_sizer.Add(stop_button, 0,  wx.ALL, 5)

            # Add the button sizer to the main sizer
            sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 1)

        sizer.Add(self.answer_output, 1, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)
        self.Layout()
        self.question_input.SetInsertionPoint(0)
        self.Show()

        ask_button.Bind(wx.EVT_BUTTON, self.on_ask_wrapper)
        self.question_input.Bind(wx.EVT_TEXT_ENTER, self.on_ask_wrapper)

        # Create an accelerator table
        copy_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_copy, id=copy_id)
        self.stop_output = False
        self.response_stream = None
        self.client=None
        stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('Q'), copy_id)])
        self.SetAcceleratorTable(accel_tbl)
        self.statusbar = self.CreateStatusBar()  # Add this line to create a status bar
        self.statusbar.SetStatusText('Ready')    
        pub.subscribe(self.append_text, "append_text") 
        self.CenterOnScreen() 
        self.Bind(wx.EVT_SIZE, self.on_resize)
    def on_resize(self, event):
        # Update the size of the ListCtrl to match the size of the frame
        self.answer_output.SetSize(self.GetSize())

        # Calculate the total width of the other columns
        total_width = sum(self.answer_output.GetColumnWidth(i) for i in range(self.answer_output.GetColumnCount() - 1))

        # Set the width of the last column to the remaining width of the ListCtrl
        self.answer_output.SetColumnWidth(self.answer_output.GetColumnCount() - 1, self.answer_output.GetSize()[0] - total_width)

        # Call Skip to ensure the event is processed by other handlers
        event.Skip()      
    def add_row(self, text):
        pp(text)
        elapsed_time = time.time() - self.start_time
        i = self.answer_output.GetItemCount()
        index = self.answer_output.InsertItem(i, str(i+1))
        self.answer_output.SetItem(index, 1, str(elapsed_time))  # Convert elapsed_time to string
        self.answer_output.SetItem(index, 2, self.model_selector.GetValue())
        self.answer_output.SetItem(index, 3, text) 


    def append_to_row(self, text):
        # Append the text to the row
        last_index = self.answer_output.GetItemCount() - 1
        current_text = self.answer_output.GetItemText(last_index, 3)
        new_text = current_text + text

        # Wrap the new text
        wrapped_text = textwrap.fill(new_text, width=50)  # Adjust the width as needed

        # Set the item text to the wrapped text
        self.answer_output.SetItem(last_index, 3, wrapped_text)
    def append_text(self, text):
        if '\n' in text:
            lines = text.split('\n')
            #pp(lines)
            self.append_to_row(lines[0])
            for line in lines[1:]:
                self.add_row(line)
        else:
            last_index = self.answer_output.GetItemCount() - 1
            if last_index >= 0:
                self.append_to_row(text)
            else:
                self.add_row(text)
    def __append_text(self, text):
        model_name = self.model_selector.GetValue()
        lines = text.split('\n')
        for i, line in enumerate(lines, start=1):
            if line:
                self.add_row(line)

    def _append_text(self, text):
        model_name = self.model_selector.GetValue()
        if '\n' in text:
            
            lines = text.split('\n')
            
            
            text = text.replace('\n',f'\n[{model_name}]: ')
        self.add_row(text)       
    def on_pause(self, event):
        if event.GetEventObject().GetLabel() == 'Pause':
            self.pause_output = True 
            if self.response_stream :
                self.response_stream.cancel()
                self.response_stream = None   
            if self.pause_output:
                self.statusbar.SetStatusText('Paused')
                event.GetEventObject().SetLabel('Resume')

        else:    
            self.pause_output = False
            self.statusbar.SetStatusText('Resumed')
            event.GetEventObject().SetLabel('Pause')
            if not self.stop_output:
                asyncio.create_task(self.on_ask(event))

    def on_stop(self, event):

        self.stop_output = True 
        self.pause_output = False
        
        pp(self.response_stream) 
        if self.response_stream :
            self.response_stream.cancel()
            self.response_stream = None
        self.client=None
        #pub.sendMessage("append_text", text='\n-->Done.\n\n\n')
        self.statusbar.SetStatusText('Stopped')
    def on_copy(self, event):
        selected_text = self.answer_output.GetStringSelection()
        self.question_input.SetValue(selected_text)
        self.question_input.SetFocus()
        self.client=None
        event.Skip()  # allow the event to be processed by other handlers      
    def on_ask_wrapper(self, event):
        asyncio.create_task(self.on_ask(event))
    async def on_ask(self, event):
        self.statusbar.SetStatusText('Asking...')
        self.stop_output = False
        self.pause_output = False 
        question = self.question_input.GetValue()
        self.response_stream =  await self.stream_response(question, self.answer_output, self)
        #self.answer_output.AppendText('\n'*3)
        #self.client=None
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
    async def stream_response(self, prompt, output_ctrl, frame):
        # Create a chat completion request with streaming enabled
        #out=[]
        try:

            self.add_row(f'\n-->Start ({self.model_selector.GetValue()}).\n')
            #pub.sendMessage("append_text", text=f'\n-->Start ({self.model_selector.GetValue()}).\n')
            for chunk in await self.get_chat_completion_client(prompt):
                if frame.stop_output or frame.pause_output:
                    break            
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    #out.append(content)
                    #output_ctrl.AppendText(content)
                    pub.sendMessage("append_text", text=content)
                    await asyncio.sleep(0)

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:

            if not frame.pause_output:
                self.client = None
                print('--> Stopped')
                #self.answer_output.AppendText('\n-->Done.\n\n\n')
                if not frame.stop_output:
                    self.add_row('\n-->Done.\n\n\n')
                    #pub.sendMessage("append_text", text='\n-->Done.\n\n\n')
                else:
                    self.add_row('\n-->Done(Stop).\n\n\n')
                    #pub.sendMessage("append_text", text='\n-->Done(Stop).\n\n\n')
            else:
                print('--> Paused')
             


    async def _stream_response(self, prompt, output_ctrl, frame):
        # Create a chat completion request with streaming enabled
        #out=[]
        try:
            response = await self.get_chat_completion_client(prompt)

            # Print each response chunk as it arrives
            print("Streaming response:")

            for chunk in response:
                if frame.stop_output or frame.pause_output:


                    break            
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    #out.append(content)
                    #output_ctrl.AppendText(content)
                    pub.sendMessage("append_text", text=content)
                    await asyncio.sleep(0)

        except Exception as e:
            print(f"An error occurred: {e}")
        #self.client=None
        #return ''.join(out)

if __name__ == "__main__":
    app = wxasync.WxAsyncApp()
    frame = MainFrame()
    frame.SetSize(800, 600)
    frame.Show()
    asyncio.get_event_loop().run_until_complete(app.MainLoop())