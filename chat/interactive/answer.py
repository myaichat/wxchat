import wx
import wxasync
import asyncio


import openai
import os
from dotenv import load_dotenv
load_dotenv()

# Set your OpenAI API key here
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("API key is not loaded!")
else:
    print("API key loaded successfully.")
openai.api_key = api_key

async def stream_response(prompt, output_ctrl):
    # Create a chat completion request with streaming enabled
    out=[]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a chatbot that assists with Apache Spark queries."},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )

        # Print each response chunk as it arrives
        print("Streaming response:")

        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)
                #out.append(content)
                output_ctrl.AppendText(content)
                await asyncio.sleep(0)

    except Exception as e:
        print(f"An error occurred: {e}")
    return ''.join(out)

class MainFrame(wx.Frame):
    def __init__(self, size=(800, 600)):
        super().__init__(None, title="OpenAI Question Asker")




        panel = wx.Panel(self)

        self.question_input = wx.TextCtrl(panel, value='Hey, what are new features of Apache Spark?', style=wx.TE_PROCESS_ENTER)

        self.answer_output = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.question_input, 0, wx.EXPAND | wx.ALL, 5)

        if 1:

            ask_button = wx.Button(panel, label="Ask Question")
            #stop_button = wx.Button(panel, label="Stop")

            # Create a horizontal box sizer
            button_sizer = wx.BoxSizer(wx.HORIZONTAL)

            # Add the ask button to the sizer
            button_sizer.Add(ask_button, 1, wx.EXPAND | wx.ALL, 5)

            # Add the stop button to the sizer
           # button_sizer.Add(stop_button, 0,  wx.ALL, 5)

            # Add the button sizer to the main sizer
            sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)

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
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('Q'), copy_id)])
        self.SetAcceleratorTable(accel_tbl)
    def on_copy(self, event):
        selected_text = self.answer_output.GetStringSelection()
        self.question_input.SetValue(selected_text)
        self.question_input.SetFocus()
        event.Skip()  # allow the event to be processed by other handlers      
    def on_ask_wrapper(self, event):
        asyncio.create_task(self.on_ask(event))
    async def on_ask(self, event):
        question = self.question_input.GetValue()
        await stream_response(question, self.answer_output)
        self.answer_output.AppendText('\n'+'*'*120 + '\n'+ '\n')

        #self.answer_output.SetValue(answer)

if __name__ == "__main__":
    app = wxasync.WxAsyncApp()
    frame = MainFrame()
    frame.SetSize(800, 600)
    frame.Show()
    asyncio.get_event_loop().run_until_complete(app.MainLoop())