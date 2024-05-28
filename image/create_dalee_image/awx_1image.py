import wx
from io import BytesIO
from PIL import Image
import base64
from openai import OpenAI
import asyncio
import threading
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
        self.asyncio_thread = threading.Thread(target=self.start_asyncio_event_loop, daemon=True)
        self.asyncio_thread.start()

    def start_asyncio_event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()


    def on_generate(self, event):
        prompt = self.prompt_ctrl.GetValue()
        threading.Thread(target=self.generate_image_and_display, args=(prompt,), daemon=True).start()
    def generate_image_and_display(self, prompt):
        future = asyncio.run_coroutine_threadsafe(self.generate_image(prompt), self.loop)
        try:
            image_data = future.result()
        except Exception as e:
            wx.CallAfter(wx.MessageBox, str(e), "Error", wx.ICON_ERROR)
            return
        image = self.data_to_image(image_data)
        wx.CallAfter(self.display_image, image)
    def test(self, prompt):
        #busy_info = wx.BusyInfo("Generating image...")
        try:
            future = asyncio.run_coroutine_threadsafe(self.generate_image(prompt), self.loop)
            image_data = future.result()
        finally:
            #del busy_info
            pass
        image = self.data_to_image(image_data)
        self.display_image(image)

    async def generate_image(self, prompt):
        client = OpenAI()  # will use environment "OPENAI_API_KEY"
        image_params = {
            "model": "dall-e-3",
            "n": 1,
            "size": "1024x1024",
            "prompt": prompt,
            "user": "myName",
            "response_format": "b64_json"
        }
        images_response = await self.loop.run_in_executor(None, lambda: client.images.generate(**image_params))
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