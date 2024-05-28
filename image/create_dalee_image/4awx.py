import wx
import os, sys
from io import BytesIO
from PIL import Image
import base64
from openai import OpenAI
import asyncio
import threading

from dotenv import load_dotenv
e=sys.exit

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY") 
#e()

class CustomStatusBar(wx.StatusBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetFieldsCount(3)
        self.SetStatusWidths([-1, -2, -2])
        self.progress_bar = []
        for id in range(2):
            gauge = wx.Gauge(self, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
            gauge.SetRange(100)
            self.progress_bar.append(gauge)
            self.PlaceProgressBar(id)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def on_size(self, event):
        for id in range(2):
            self.PlaceProgressBar(id)

    def PlaceProgressBar(self, id=0):
        rect = self.GetFieldRect(id + 1)
        self.progress_bar[id].SetPosition((rect.x, rect.y))
        self.progress_bar[id].SetSize((rect.width, rect.height))

    def SetProgress(self, value, id):
        self.progress_bar[id].SetValue(value)

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="DALL-E Image Generator", size=(800, 600))
        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        if 1:
            self.panel1 = wx.Panel(self.panel)
            self.panel2 = wx.Panel(self.panel)
            self.bitmap1 = None
            self.bitmap2 = None
            p_sizer = wx.BoxSizer(wx.HORIZONTAL)
            p_sizer.Add(self.panel1, 1, wx.EXPAND)
            p_sizer.Add(self.panel2, 1, wx.EXPAND)

            vbox.Add(p_sizer, 1, wx.EXPAND)

        if 0:
            left_sizer = wx.BoxSizer(wx.VERTICAL)
            #self.image_sizer = wx.GridSizer(cols=2)  # Adjust cols as needed
            self.grid_sizer = wx.GridSizer(rows=2, cols=2, vgap=5, hgap=5)
            left_sizer.Add(self.grid_sizer, 1, wx.EXPAND)

            load_image_btn = wx.Button(self.panel, label="Load Images")
            #load_image_btn.Bind(wx.EVT_BUTTON, self.on_load_image)
            left_sizer.Add(load_image_btn, 0, wx.ALL | wx.CENTER, 5)

            vbox.Add(left_sizer, 1, wx.EXPAND)


        
        #vbox.Add(self.grid_sizer, 1, flag=wx.EXPAND | wx.ALL, border=10)
        if 1:
            self.prompt_ctrl = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE )
            vbox.Add(self.prompt_ctrl, 0, flag=wx.EXPAND | wx.ALL, border=10)
            self.prompt_ctrl.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            self.prompt_ctrl.SetValue('''A richly colored image showcasing a strong Ukrainian woman, portrayed as a mother holding her child in a protective embrace.
            She wears a traditional Ukrainian skirt called a 'plakhta', embellished with the vibrant blue and yellow of the Ukraine flag. 
            Her hair, elaborately twined with ribbons, is a visual metaphor for her enduring spirit. Above them, ominous black figures, 
            suggestive of rockets, are descending, disturbing the peaceful scenery of their homeland.''')
        if 1:
            self.generate_button = wx.Button(self.panel, label='Generate 2 Images')
            vbox.Add(self.generate_button, flag=wx.EXPAND | wx.ALL, border=10)
            self.generate_button.Bind(wx.EVT_BUTTON, self.on_generate)

        self.panel.SetSizer(vbox)
        self.SetSize(1000, 1000)
        if 1:
            self.asyncio_thread = threading.Thread(target=self.start_asyncio_event_loop, daemon=True)
            self.asyncio_thread.start()

            self.status_bar = CustomStatusBar(self)
            self.SetStatusBar(self.status_bar)
            self.timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
            self.progress = [0 for _ in range(2)]
        self.Layout()
        self.clicked_bitmap = None

    def on_timer(self, event):
        for id in range(2):
            progress = self.progress[id]
            progress += 1  # This is just an example, replace it with your actual code
            if progress >= self.status_bar.progress_bar[id].GetRange() + 3:
                progress = 0
            self.status_bar.SetProgress(progress, id)
            self.progress[id] = progress

    def start_asyncio_event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def on_generate(self, event):
        self.generate_button.Disable()
        self.status_bar.SetStatusText("Generating image...", 0)
        prompt = self.prompt_ctrl.GetValue()
        for id in range(2):
            threading.Thread(target=self.generate_image_and_display, args=(prompt, id), daemon=True).start()
        self.timer.Start(100)

    def generate_image_and_display(self, prompt, id):
        future = asyncio.run_coroutine_threadsafe(self.generate_image(prompt), self.loop)
        try:
            image_data = future.result()
        except Exception as e:
            print(str(e))
            wx.CallAfter(wx.MessageBox, str(e), "Error in thread %d" % id, wx.ICON_ERROR)
            return
        finally:
            wx.CallAfter(self.generate_button.Enable)
            wx.CallAfter(self.status_bar.SetStatusText, "Image generation completed.", 0)
            self.timer.Stop()
            self.status_bar.SetProgress(100, id)

        image = self.data_to_image(image_data)
        wx.CallAfter(self.display_image, image, id)

    async def generate_image(self, prompt): 
        client = OpenAI(api_key=api_key)  # will use environment "OPENAI_API_KEY"
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
        return Image.open(BytesIO(image_data))

    def display_image(self, image, id):
        width, height = image.size
        image = image.resize((width // 2, height // 2))  # resize for display
        wx_image = wx.Image(image.size[0], image.size[1])
        wx_image.SetData(image.convert("RGB").tobytes())
        bitmap = wx_image.ConvertToBitmap()

        if id == 0:
            if self.bitmap1:
                self.bitmap1.Destroy()
            self.bitmap1 = wx.StaticBitmap(self.panel1, bitmap=bitmap)
            self.bitmap1.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        else:
            if self.bitmap2:
                self.bitmap2.Destroy()
            self.bitmap2 = wx.StaticBitmap(self.panel2, bitmap=bitmap)
            self.bitmap2.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)

        self.Layout()
    def on_context_menu(self, event):
        
        # Store the wx.StaticBitmap that was right-clicked
        self.clicked_bitmap = event.GetEventObject()
        self.popup_menu = wx.Menu()
        copy_item = self.popup_menu.Append(wx.ID_COPY, "Copy")
        self.Bind(wx.EVT_MENU, self.on_copy, id=copy_item.GetId())
        self.PopupMenu(self.popup_menu)



    def on_copy(self, event):
        # Use the stored wx.StaticBitmap
        #print(222, event.GetEventObject())
        clicked_bitmap=self.clicked_bitmap.GetBitmap()
        if 1:
            assert clicked_bitmap, self.clicked_bitmap
            #clicked_bitmap = self.clicked_bitmap.GetBitmap() if self.clicked_bitmap else None
            #assert clicked_bitmap

            if clicked_bitmap:
                # Convert the wx.Bitmap to a wx.Image
                image = clicked_bitmap.ConvertToImage()

                # Convert the wx.Image back to a wx.Bitmap
                bitmap = wx.Bitmap(image)

                # Create a wx.BitmapDataObject containing the wx.Bitmap
                data = wx.BitmapDataObject(bitmap)

                # Open the clipboard and set the data
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(data)
                    wx.TheClipboard.Close()
app = wx.App(False)
frame = MainFrame()
frame.Show(True)
app.MainLoop()
