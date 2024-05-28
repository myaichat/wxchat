import wx
from io import BytesIO
from PIL import Image
import base64
from openai import OpenAI
class BusyDialog(wx.Dialog):
    def __init__(self, parent, message):
        super().__init__(parent, style=wx.STAY_ON_TOP)
        self.CenterOnParent()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=message), flag=wx.ALL, border=10)
        self.SetSizerAndFit(sizer)
class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title="DALL-E Image Generator", size=(800,600))

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.prompt_ctrl = wx.TextCtrl(panel, size=(-1,200), style=wx.TE_MULTILINE | wx.TE_WORDWRAP)
        font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.prompt_ctrl.SetFont(font)
        self.prompt_ctrl.SetValue('''A richly colored image showcasing a strong Ukrainian woman, portrayed as a mother holding her child in a protective embrace.
          She wears a traditional Ukrainian skirt called a 'plakhta', embellished with the vibrant blue and yellow of the Ukraine flag. 
          Her hair, elaborately twined with ribbons, is a visual metaphor for her enduring spirit. Above them, ominous black figures, 
          suggestive of rockets, are descending, disturbing the peaceful scenery of their homeland.''')
        vbox.Add(self.prompt_ctrl, flag=wx.EXPAND|wx.ALL, border=10)

        generate_button = wx.Button(panel, label='Generate Image')
        generate_button.Bind(wx.EVT_BUTTON, self.on_generate)
        vbox.Add(generate_button, flag=wx.EXPAND|wx.ALL, border=10)

        self.image_ctrl = wx.StaticBitmap(panel)
        vbox.Add(self.image_ctrl, flag=wx.EXPAND|wx.ALL, border=10)

        panel.SetSizer(vbox)
        self.SetSize(1000, 1000)

    def on_generate(self, event):
        prompt = self.prompt_ctrl.GetValue()
        busy_info = wx.BusyInfo("Generating image...")

        try:
            image_data = self.generate_image(prompt)
        finally:
            del busy_info
            pass
        image = self.data_to_image(image_data)
        self.display_image(image)

    def generate_image(self, prompt):
        # Your OpenAI image generation code here
        # For example:
        client = OpenAI()  # will use environment variable "OPENAI_API_KEY"
        image_params = {
            "model": "dall-e-3",
            "n": 1,
            "size": "1024x1024",
            "prompt": prompt,
            "user": "myName",
            "response_format": "b64_json"
        }
        images_response = client.images.generate(**image_params)
        return images_response.data[0].model_dump()["b64_json"]

    def data_to_image(self, data):
        image_data = base64.b64decode(data)
        image = Image.open(BytesIO(image_data))
        return image

    def display_image(self, image):
        width, height = image.size
        image = image.resize((width//2, height//2))  # resize for display
        wx_image = wx.Image(image.size[0], image.size[1])
        wx_image.SetData(image.convert("RGB").tobytes())
        self.image_ctrl.SetBitmap(wx_image.ConvertToBitmap())
        self.Layout()

app = wx.App(False)
frame = MainFrame()
frame.Show(True)
app.MainLoop()