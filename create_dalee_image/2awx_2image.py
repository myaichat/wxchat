import wx
from io import BytesIO
from PIL import Image
import base64
from openai import OpenAI
import asyncio
import threading
class CustomStatusBar(wx.StatusBar):
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent)

        self.SetFieldsCount(2)
        self.SetStatusWidths([-1, -2])

        self.progress_bar = wx.Gauge(self, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.progress_bar.SetRange(100)  # Set the range to 100

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.PlaceProgressBar()

    def on_size(self, event):
        self.PlaceProgressBar()

    def PlaceProgressBar(self):
        rect = self.GetFieldRect(1)
        self.progress_bar.SetPosition((rect.x, rect.y))
        self.progress_bar.SetSize((rect.width, rect.height))

    def SetProgress(self, value):
        self.progress_bar.SetValue(value)
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

        self.generate_button=generate_button = wx.Button(panel, label='Generate Image')
        generate_button.Bind(wx.EVT_BUTTON, self.on_generate)
        vbox.Add(generate_button, flag=wx.EXPAND|wx.ALL, border=10)

        self.image_ctrl = wx.StaticBitmap(panel)
        vbox.Add(self.image_ctrl, flag=wx.EXPAND|wx.ALL, border=10)

        panel.SetSizer(vbox)
        self.SetSize(1000, 1000)
        self.asyncio_thread = threading.Thread(target=self.start_asyncio_event_loop, daemon=True)
        self.asyncio_thread.start()
        self.status_bar = CustomStatusBar(self)
        self.SetStatusBar(self.status_bar)  
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)  
        self.progress=0          
    def on_timer(self, event):
        progress=self.progress 
        progress += 1  # This is just an example, replace it with your actual code
        self.status_bar.SetProgress(progress)
        
        if progress >= self.status_bar.progress_bar.GetRange()+5:
            progress = 0
        self.status_bar.SetProgress(progress)       
        self.progress=progress 
    def start_asyncio_event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()


    def on_generate(self, event):
        self.generate_button.Disable()
        self.status_bar.SetStatusText("Generating image...", 0)
        if 1:
            prompt = self.prompt_ctrl.GetValue()
            threading.Thread(target=self.generate_image_and_display, args=(prompt,), daemon=True).start()
            self.timer.Start(100)
    def generate_image_and_display(self, prompt):
        future = asyncio.run_coroutine_threadsafe(self.generate_image(prompt), self.loop)
        try:
            image_data = future.result()
        except Exception as e:
            wx.CallAfter(wx.MessageBox, str(e), "Error", wx.ICON_ERROR)
            return
        finally:
            wx.CallAfter(self.generate_button.Enable)
            wx.CallAfter(self.status_bar.SetStatusText, "Image generation completed.", 0)
            self.timer.Stop()
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