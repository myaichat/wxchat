import wx
import base64
import requests
from io import BytesIO
from PIL import Image

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Image Describer", size=(800, 600))

        panel = wx.Panel(self)
        self.panel = panel  # Store panel for later use

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        if 1:
            left_sizer = wx.BoxSizer(wx.VERTICAL)
            self.image_sizer = wx.GridSizer(cols=2)  # Adjust cols as needed
            left_sizer.Add(self.image_sizer, 1, wx.EXPAND)

            load_image_btn = wx.Button(self.panel, label="Load Images")
            load_image_btn.Bind(wx.EVT_BUTTON, self.on_load_image)
            left_sizer.Add(load_image_btn, 0, wx.ALL | wx.CENTER, 5)

            main_sizer.Add(left_sizer, 1, wx.EXPAND)

        text_sizer = wx.BoxSizer(wx.HORIZONTAL)
        question_sizer = wx.BoxSizer(wx.VERTICAL)

        self.question_input = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1, 100))
        question_sizer.Add(self.question_input, 1, wx.ALL | wx.EXPAND, 5)
        describe_image_btn = wx.Button(panel, label="Describe Images")
        describe_image_btn.Bind(wx.EVT_BUTTON, self.on_describe_image)
        question_sizer.Add(describe_image_btn, 0, wx.ALL | wx.CENTER, 5)
        self.question_input.SetValue("What’s in this image?  give detailed description.")
        text_sizer.Add(question_sizer, 0, wx.EXPAND)
        self.answer_output = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 100))
        font = wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL)  # Adjust size as needed
        self.answer_output.SetFont(font)
        text_sizer.Add(self.answer_output, 1, wx.ALL | wx.EXPAND, 5)


        main_sizer.Add(text_sizer, 1, wx.EXPAND)

        panel.SetSizer(main_sizer)
        self.base64_image={}

    def on_load_image(self, event):
        with wx.FileDialog(self, "Open Image", wildcard="Image files (*.jpg;*.png)|*.jpg;*.png",
                        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            image_paths = fileDialog.GetPaths()
            for image_path in image_paths:
                with open(image_path, "rb") as image_file:
                    self.base64_image[image_path] = base64.b64encode(image_file.read()).decode('utf-8')
                    self.display_image(image_path)

            self.panel.Layout() 

    def display_image(self, image_path):
        image = wx.Image(image_path, wx.BITMAP_TYPE_ANY).Scale(300, 300)  # Adjust size as needed
        bitmap = wx.StaticBitmap(self.panel, -1, wx.Bitmap(image))
        self.image_sizer.Add(bitmap, 0, wx.ALL, 5)
        self.Layout()

    def on_describe_image(self, event):
        if hasattr(self, 'base64_image') and len(self.base64_image)==2:
            dialog = wx.ProgressDialog("Progress", "Processing image... Please wait.", 
                                    style=wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_AUTO_HIDE)

            try:
                if 1:
                    for i in range(10):  # This is just an example, replace it with your actual task
                        wx.MilliSleep(50)  # Simulate long operation
                        dialog.Update(i)  # Update progress dialog
                self.describe_image(self.base64_image)
                
                
            finally:
                dialog.Destroy()
        else:
            wx.MessageBox("Please load 2 images first", "Error", wx.OK | wx.ICON_ERROR)                
    def describe_image(self, base64_image):
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
            "model": "gpt-4-turbo",
            "messages": [
                {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": "What are in these images? Is there any difference between them?",
                    #"text": "mix descriptions of these images into one creative description. add depth and emotions.",
                    },
                    {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{list(base64_image.values())[0]}",
                        "detail": "high"
                    }
                    },
                    {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{list(base64_image.values())[1]}",
                        "detail": "high"
                    }
                    },
                ],
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
            self.answer_output.SetValue(ret['choices'][0]['message']['content'])
        except Exception as e:
            print("Error in response")
            pp(ret)
            self.answer_output.SetValue(str(e)+str(ret))
            raise
   

if __name__ == "__main__":
    app = wx.App(False)
    frame = MainFrame()
    frame.Show()
    app.MainLoop()