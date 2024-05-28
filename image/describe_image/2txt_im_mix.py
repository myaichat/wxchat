import wx
import base64
import requests
from io import BytesIO
from PIL import Image
import threading
class BusyDialog(wx.Dialog):
    def __init__(self, parent, id, title):
        super(BusyDialog, self).__init__(parent, id, title, size=(300, 200))
        self.label = wx.StaticText(self, label="Please wait...")
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.label, 0, wx.ALL, 10)
        self.SetSizer(self.sizer)

class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title="Image Description", size=(800, 600))

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        image_sizer = wx.BoxSizer(wx.VERTICAL)

        self.prompt_ctrl = wx.TextCtrl(panel, -1, "Your prompt here", size=(200, 200), style=wx.TE_MULTILINE)
        image_sizer.Add(self.prompt_ctrl, 0, wx.EXPAND)

        self.image_ctrl = wx.StaticBitmap(panel)
        #self.image_ctrl.SetBackgroundColour(wx.WHITE)
        image_sizer.Add(self.image_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        load_image_btn = wx.Button(panel, label="Load Image")
        load_image_btn.Bind(wx.EVT_BUTTON, self.on_load_image)
        image_sizer.Add(load_image_btn, 0, wx.ALL | wx.CENTER, 5)
        main_sizer.Add(image_sizer, 1, wx.EXPAND)

        text_sizer = wx.BoxSizer(wx.VERTICAL)
        self.text_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.text_ctrl.SetFont(font)
        text_sizer.Add(self.text_ctrl, 1, wx.ALL | wx.EXPAND, 5)

        question_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.question_input = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1, 100))
        question_sizer.Add(self.question_input, 1, wx.ALL | wx.EXPAND, 5)
        describe_image_btn = wx.Button(panel, label="Merge P+I")
        describe_image_btn.Bind(wx.EVT_BUTTON, self.on_describe_image)
        question_sizer.Add(describe_image_btn, 0, wx.ALL | wx.CENTER, 5)
        self.question_input.SetValue("Describe image and TEXT_PROMPT into one creative description with depth and emotions. Add Ukrainian essence. Add blue and yellow theme.")
        text_sizer.Add(question_sizer, 0, wx.EXPAND)
        main_sizer.Add(text_sizer, 1, wx.EXPAND)

        panel.SetSizer(main_sizer)



    def display_image(self, image_path):
        image = wx.Image(image_path, wx.BITMAP_TYPE_ANY)
        scaled_image = image.Scale(400, 300, wx.IMAGE_QUALITY_HIGH)
        bitmap = wx.Bitmap(scaled_image)
        self.image_ctrl.SetBitmap(bitmap)

    def on_load_image(self, event):
        with wx.FileDialog(self, "Open Image", wildcard="Image files (*.jpg;*.png)|*.jpg;*.png") as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            image_path = fileDialog.GetPath()
            with open(image_path, "rb") as image_file:
                self.base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            self.display_image(image_path)

    def on_describe_image(self, event):
        if hasattr(self, 'base64_image'):
            self.busy_dialog = BusyDialog(self, -1, "Busy")
            self.busy_dialog.Show()
            threading.Thread(target=self.describe_image).start()


            
        else:
            wx.MessageBox("Please load an image first", "Error", wx.OK | wx.ICON_ERROR)

    def describe_image(self):
        import os
        import base64
        import requests
        from os.path import isfile
        from pprint import pprint as pp
        from dotenv import load_dotenv
        load_dotenv()

        # Set your OpenAI API key here
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("API key is not loaded!")
        else:
            print("API key loaded successfully.")


        headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
        }

        payload = {
        "model": "gpt-4o",
        "messages": [
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": f'{self.question_input.GetValue()}.TEXT_PROMPT: "{self.prompt_ctrl.GetValue()}"'
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{self.base64_image}"
                }
                }
            ]
            }
        ],
        "max_tokens": 300
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        #pp(dir(response))
        assert (response.status_code==200)
        ret=response.json()
        #pp(ret)
        try:
            assert 'choices' in ret
            assert  ret['choices'][0]
            assert 'message' in ret['choices'][0]
            assert 'content' in ret['choices'][0]['message']
            #print(ret['choices'][0]['message']['content'])
            self.text_ctrl.SetValue(ret['choices'][0]['message']['content'])
        except Exception as e:
            print("Error in response")
            pp(ret)
            self.text_ctrl.SetValue(str(e)+str(ret))
            raise
        finally:
            wx.CallAfter(self.busy_dialog.Destroy)

if __name__ == "__main__":
    app = wx.App(False)
    frame = MainFrame()
    frame.Show()
    app.MainLoop()