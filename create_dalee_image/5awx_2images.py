import wx
import os, sys
from os.path import isdir, join
from io import BytesIO
from PIL import Image
import base64
from openai import OpenAI
import asyncio
import threading

from datetime import datetime

from dotenv import load_dotenv
e=sys.exit
from pubsub import pub
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY") 
#e()

class CustomStatusBar(wx.StatusBar):
    def __init__(self, parent, rows, cols):
        super().__init__(parent)
        self.num_images=num_images=rows*cols
        self.SetFieldsCount(num_images+1)
        self.SetStatusWidths([-1]+ [-2] * num_images)
        self.rows=rows
        self.cols=cols
        self.progress_bar = {}
        for row in range(rows):
            for col in range(cols):
                pos=(row, col)
                id=row*cols+col
                gauge = wx.Gauge(self, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
                gauge.SetRange(100)
                self.progress_bar[pos]=gauge
                self.PlaceProgressBar(pos)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def on_size(self, event):
        for row in range(self.rows):
            for col in range(self.cols):
                self.PlaceProgressBar((row,col))

    def PlaceProgressBar(self, pos):
        row, col=pos
        id=row*self.cols+col
        rect = self.GetFieldRect(id + 1)
        self.progress_bar[pos].SetPosition((rect.x, rect.y))
        self.progress_bar[pos].SetSize((rect.width, rect.height))

    def SetProgress(self, value, pos):
        self.progress_bar[pos].SetValue(value)

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="DALL-E Image Generator",pos=(300,50))
        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.rows=rows = 1
        self.cols=cols = 2
        self.num_of_images=rows*cols
        self.panels=panels={}
        self.bitmaps=bitmaps={}
        h_sizers = {}
        self.completed_cnt=0
        for row in range(rows):
            panels[row]={}
            bitmaps[row]={}
            h_sizers[row] = wx.BoxSizer(wx.HORIZONTAL)
            for col in range(cols):
                panels[row][col]=panel = wx.Panel(self.panel)
                bitmaps[row][col]=None
                
                h_sizers[row].Add(panel, 1, wx.EXPAND)


            vbox.Add(h_sizers[row], 1, wx.EXPAND)

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
        
        self.last_generation_time = datetime.now()
        self.elapsed_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_label, self.elapsed_timer)
        #self.elapsed_timer.Start(1000)  # 1000 milliseconds = 1 second

        
        if 1:
            h_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.elapsed_time_label = wx.StaticText(self.panel, label="0 sec")
            h_sizer.Add(self.elapsed_time_label, flag=wx.EXPAND | wx.ALL, border=3)

            self.models = ["dall-e-2", "dall-e-3"]  # Replace with your model names
            self.model_name = wx.ComboBox(self.panel, choices=self.models)
            self.model_name.SetValue("dall-e-3")
            h_sizer.Add(self.model_name, 0, flag=wx.EXPAND | wx.ALL, border=3)

            self.generate_button = wx.Button(self.panel, label=f'Generate {rows*cols} Images')
            h_sizer.Add(self.generate_button, 1, flag=wx.EXPAND | wx.ALL, border=3)
            self.generate_button.Bind(wx.EVT_BUTTON, self.on_generate)
            vbox.Add(h_sizer, flag=wx.EXPAND | wx.ALL, border=10)


        self.panel.SetSizer(vbox)
        
        if 1:
            self.asyncio_thread = threading.Thread(target=self.start_asyncio_event_loop, daemon=True)
            self.asyncio_thread.start()

            self.status_bar = CustomStatusBar(self, rows, cols)
            self.SetStatusBar(self.status_bar)
            self.timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
            self.progress = [0 for _ in range(self.num_of_images)]
        self.SetSize(cols*450, 300+rows*450)
        self.Layout()
        self.clicked_bitmap = None
        pub.subscribe(self.increment_counter, "increment_counter")
        if not isdir('generated'):
            os.mkdir('generated')
    def update_label(self, event):
        elapsed_time = datetime.now() - self.last_generation_time
        self.elapsed_time_label.SetLabel(f"{elapsed_time.seconds} secs")
        secs=self.rows*self.cols*10
        if elapsed_time.seconds > secs:
            self.elapsed_timer.Stop()
            self.elapsed_time_label.SetLabel(f"0 secs")
            self.generate_button.Enable()
    def increment_counter(self):
        self.completed_cnt+=1
        #print(self.completed_cnt, 'increment_counter')
        self.status_bar.SetStatusText(f"Completed: {self.completed_cnt}")
        self.last_generation_time = datetime.now()

    def on_timer(self, event):
       for row in range(self.rows):
            for col in range(self.cols):
                pos=(row, col)
                id=row*self.cols+col
                progress = self.progress[id]
                progress += 1  # This is just an example, replace it with your actual code
                if progress >= self.status_bar.progress_bar[pos].GetRange() + 3:
                    progress = 0
                self.status_bar.SetProgress(progress, pos)
                self.progress[id] = progress

    def start_asyncio_event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def on_generate(self, event):

        self.completed_cnt=0
        #pub.sendMessage("increment_counter")
        self.generate_button.Disable()
        self.status_bar.SetStatusText("Generating ...", 0)
        prompt = self.prompt_ctrl.GetValue()
        for row in   range(self.rows):
            for col in range(self.cols):
                
                #self.generate_image_and_display(prompt, (row,col)))
                threading.Thread(target=self.generate_image_and_display, args=(prompt, (row,col)), daemon=True).start()
        self.timer.Start(100)
        self.last_generation_time = datetime.now()
        self.elapsed_timer.Start(1000) 

    def generate_image_and_display(self, prompt, pos):
        row, col=pos
        future = asyncio.run_coroutine_threadsafe(self.generate_image(prompt), self.loop)
        try:
            image_data = future.result()
        except Exception as e:
            print(str(e))
            #wx.CallAfter(wx.MessageBox, str(e), "Error in thread %d" % id, wx.ICON_ERROR)
            return
        finally:
            #wx.CallAfter(self.generate_button.Enable)
            
            self.timer.Stop()
            self.status_bar.SetProgress(100, pos)

        image = self.data_to_image(image_data)
        wx.CallAfter(self.display_image, image, pos)
        pub.sendMessage("increment_counter")

    async def generate_image(self, prompt): 
        client = OpenAI(api_key=api_key)  # will use environment "OPENAI_API_KEY"
        image_params = {
            "model": self.model_name.GetValue(),
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

    def display_image(self, image, pos):
        width, height = image.size
        if 1:
            from datetime import datetime
            # Get current date and time
            now = datetime.now()
            # Format as a string
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            # Append to filename
            filename = join('generated',f"output_{timestamp_str}.png")
            image.save(filename)

        image = image.resize((int(width // 2.1), int(height // 2.1)))  # resize for display
        wx_image = wx.Image(image.size[0], image.size[1])
        wx_image.SetData(image.convert("RGB").tobytes())
        bitmap = wx_image.ConvertToBitmap()
        row, col=pos
        if self.bitmaps[row][col]:  
            self.bitmaps[row][col].Destroy()
        self.bitmaps[row][col] = wx.StaticBitmap(self.panels[row][col], bitmap=bitmap)
        self.bitmaps[row][col].Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)            
        if 0:
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
