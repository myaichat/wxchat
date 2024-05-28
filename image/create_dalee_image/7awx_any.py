#https://platform.openai.com/settings/organization/billing/overview
import wx
import os, sys
from os.path import isdir, join
from io import BytesIO
from PIL import Image
import base64
from openai import OpenAI
import asyncio
import threading


from pprint import pprint as pp
from copy import deepcopy

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
#A floating blue and yellow glowing silhouette of the body and legs of an adult female in profile, filled with light, surrounded by black space, in the center of which is depicted as lightning or water splash. black background, ukrainian theme
class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="DALL-E Image Generator",pos=(300,50))
        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        

        self.popup = wx.PopupWindow(self)
        self.rows=rows = 2
        self.cols=cols = 4
        self.num_of_images=rows*cols
        self.panels=panels={}
        self.bitmaps=bitmaps={}
        self.static_bitmap=None
        self.images=images={}
        self.text_controls =text_controls= {}
        h_sizers = {}
        self.completed_cnt=0
        copy_text_id = wx.NewIdRef()
        enter_id = wx.NewIdRef()
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('U'), copy_text_id)])
        enter_accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, wx.WXK_RETURN, enter_id)])
        self.num_of_im_to_generate=0
        if 1:
            sbox = wx.BoxSizer(wx.VERTICAL)
            self.scrolled_window = wx.ScrolledWindow(self.panel, -1)
            self.scrolled_window.SetScrollRate(10, 10)
            for row in range(rows):
                panels[row]={}
                bitmaps[row]={}
                images[row]={}
                text_controls[row] = {}
                h_sizers[row] = wx.BoxSizer(wx.HORIZONTAL)
                for col in range(cols):
                    panels[row][col]=panel = wx.Panel(self.scrolled_window)  # Change the parent to self.scrolled_window
                    bitmaps[row][col]=None
                    images[row][col]=None
                    text_controls[row][col] = text_ctrl = wx.TextCtrl(panels[row][col], style=wx.TE_MULTILINE) 
                    text_ctrl.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                    #text_ctrl.Hide()
                    sizer = panels[row][col].GetSizer()
                    if sizer is None:
                        sizer = wx.BoxSizer(wx.VERTICAL)
                        panels[row][col].SetSizer(sizer) 
                    sizer.Add(text_ctrl, 1, wx.EXPAND|wx.ALL)                   
                    text_ctrl.Bind(wx.EVT_LEFT_DCLICK, self.on_text_ctrl_dclick, text_ctrl)
                    text_ctrl.SetAcceleratorTable(accel_tbl)
                    text_ctrl.Bind(wx.EVT_MENU, self.copy_text, id=copy_text_id)
                    text_ctrl.pos=(row, col)
                    h_sizers[row].Add(panel, 1, wx.EXPAND|wx.ALL)


                sbox.Add(h_sizers[row], 1, wx.EXPAND|wx.ALL)
            self.scrolled_window.SetSizer(sbox)
            vbox.Add(self.scrolled_window, 1, wx.EXPAND)


        
        #vbox.Add(self.grid_sizer, 1, flag=wx.EXPAND | wx.ALL, border=10)
        if 1:
            self.prompt_ctrl = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE )
            vbox.Add(self.prompt_ctrl, 0, flag=wx.EXPAND | wx.ALL, border=10)
            self.prompt_ctrl.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            self.prompt_ctrl.SetValue('''a simple clean minimal  3d sculpture "Ukraine" incorporating  ukrainian tryzub, representing heroic resistance and bringing relief to millions of people worldwide, simple, high quality clean minimal warrior nation  design, high detail, hyper-realistic rendering in a hyper-detailed, hyper photorealistic style with high sharpness and a high octane render, dark and light blues and yellows, cyan color palette, white background, ''')
            self.prompt_ctrl.SetAcceleratorTable(enter_accel_tbl)
            self.prompt_ctrl.Bind(wx.EVT_MENU, self.on_ctrl_enter, id=enter_id)
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


            self.number_of_images_choices = [str(i) for i in range(1, self.rows*self.cols+1)]
            self.number_of_images = wx.ComboBox(self.panel, choices=self.number_of_images_choices)
            self.num_of_im=1
            self.number_of_images.SetValue(str(self.num_of_im))  # Set default number of images
            
            self.number_of_images.Bind(wx.EVT_COMBOBOX, self.on_number_of_images_change)

            h_sizer.Add(self.number_of_images, 0, flag=wx.EXPAND | wx.ALL, border=3)

            self.hd_checkbox = wx.CheckBox(self.panel, label="HD")
            self.hd_checkbox.Bind(wx.EVT_CHECKBOX, self.on_hd_checkbox_change)
            h_sizer.Add(self.hd_checkbox, 0, flag=wx.EXPAND | wx.ALL, border=3)
            self.is_hd=False

            self.image_size_choices = ["256x256", "512x512", "1024x1024", "1024x1792","1792x1024"]
            self.image_size = wx.ComboBox(self.panel, choices=self.image_size_choices)
            self.image_size.SetValue("1024x1024")  # Set default image size
            self.image_size.Bind(wx.EVT_COMBOBOX, self.on_image_size_change)
            h_sizer.Add(self.image_size, 0, flag=wx.EXPAND | wx.ALL, border=3)
            

            self.generate_button = wx.Button(self.panel, label=f'Generate {self.num_of_im} {"Images" if self.num_of_im>1 else "Image"}')
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
        

        
        self.clicked_bitmap = None
        pub.subscribe(self.increment_counter, "increment_counter")
        pub.subscribe(self.on_set_text, "on_set_text")
        if not isdir('generated'):
            os.mkdir('generated')
        self.image_params = {
            #"model": self.model_name.GetValue(),
            "n": 1,
            #"size": "1024x1024",
            "user": "myName",
            "response_format": "b64_json"
        } 
        self.prompt_ctrl.SetFocus()  
        self.SetSize(cols*450, 300+rows*450)
        width, height = wx.DisplaySize()
        print(f"Screen width: {width}, Screen height: {height}")
        if self.rows*self.cols>2:
            if self.GetSize().GetHeight()>height:
                self.SetSize(cols*450, height-100)
            if self.GetSize().GetWidth()>width:
                self.SetSize(width, 300+rows*450)
        else:
            self.SetSize(cols*1024, 300+1024)                
        print(f"Frame width: {self.GetSize().GetWidth()}, Frame height: {self.GetSize().GetHeight()}")
        self.Layout()
    def on_ctrl_enter(self, event):
        print('on_ctrl_enter')
        self.on_generate(event)
    def on_set_text(self, text):
        self.prompt_ctrl.SetValue(text) 
    def copy_text(self, event):    
        #print('copy_text')
        text_ctrl = event.GetEventObject()
        #pub.sendMessage("on_set_text", text=text_ctrl.GetValue())
        self.prompt_ctrl.SetValue(text_ctrl.GetValue()) 
        self.status_bar.SetStatusText("Text copied to prompt")
        self.prompt_ctrl.SetFocus()
    def on_image_dclick(self, event):
        
        bitmap = event.GetEventObject()
        print('on_image_dclick', bitmap.pos)
        bitmap.Hide()

        row, col = bitmap.pos
        #print(self.text_controls)
        print(self.text_controls[row][col])
        if 1:
            self.text_controls[row][col].Show()
            #self.text_controls[row][col].pos=bitmap.pos
            self.panels[row][col].Layout()
            self.text_controls[row][col].SetFocus()

    def on_text_ctrl_dclick(self, event):
        print('on_text_ctrl_dclick')
        
        text_ctrl = event.GetEventObject()
        text_ctrl.Hide()

        row, col = text_ctrl.pos
        if self.bitmaps[row][col]:
            self.bitmaps[row][col].Show()

            self.panels[row][col].Layout()

    def on_image_size_change(self, event):
        #self.image_size = self.image_size_dropdown.GetValue()
        pass
    def on_hd_checkbox_change(self, event):
        #A postcard with  light yellow background with small stars and bokeh lights scattered across the surface, creating an elegant and festive atmosphere for New Year's celebration or special events. The soft tones of  blue add to its beauty, making it suitable as a digital backdrop for photography or graphic design projects. This vector illustration is designed in high resolution, providing clear lines and intricate details that highlight every tiny startryzub and shimmering sparkles. The style is reminiscent of in the style of festive New Year's artwork. blue and yellow theme, ukrainian tryzzub
        self.hd = self.hd_checkbox.GetValue()
        self.is_hd=not self.is_hd

    def on_number_of_images_change(self, event):
        self.num_of_im = int(self.number_of_images.GetValue())
        #print(self.num_of_im)
        self.generate_button.SetLabel(f'Generate {self.num_of_im} Images')
        # Your code to handle the change in number of images here
                    
    def update_label(self, event):
        elapsed_time = datetime.now() - self.last_generation_time
        self.elapsed_time_label.SetLabel(f"{elapsed_time.seconds} secs")
        secs=self.num_of_im_to_generate *7
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
       counter = self.num_of_im
       for row in range(self.rows):
            for col in range(self.cols):
                if counter:
                    pos=(row, col)
                    id=row*self.cols+col
                    progress = self.progress[id]
                    progress += 1  # This is just an example, replace it with your actual code
                    if progress >= self.status_bar.progress_bar[pos].GetRange() + 3:
                        progress = 0
                    self.status_bar.SetProgress(progress, pos)
                    self.progress[id] = progress
                    counter -=1

    def start_asyncio_event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    def clear_images(self):
        for row in range(self.rows):
            for col in range(self.cols):
                panel= self.panels[row][col]
                self.text_controls[row][col].Hide()
                for child in panel.GetChildren():
                    if type(child) == wx.StaticBitmap:
                        child.Destroy()
        self.scrolled_window.Layout()
    def on_generate(self, event):
        self.clear_images()
        self.completed_cnt=0
        self.num_of_im_to_generate = int(self.number_of_images.GetValue())
        #pub.sendMessage("increment_counter")
        self.generate_button.Disable()
        self.status_bar.SetStatusText("Generating ...", 0)
        prompt = self.prompt_ctrl.GetValue()
        counter = self.num_of_im
        for row in   range(self.rows):
            for col in range(self.cols):
                if counter:
                    #self.generate_image_and_display(prompt, (row,col)))
                    threading.Thread(target=self.generate_image_and_display, args=(prompt, (row,col)), daemon=True).start()
                    counter -=1
        self.timer.Start(100)
        self.last_generation_time = datetime.now()
        self.elapsed_timer.Start(1000) 

    def generate_image_and_display(self, prompt, pos):
        row, col=pos
        future = asyncio.run_coroutine_threadsafe(self.generate_image(prompt), self.loop)
        try:
            image_data, revised_prompt = future.result()
        except Exception as e:
            
            print(pos, str(e))
            #wx.CallAfter(wx.MessageBox, str(e), "Error in thread %d" % id, wx.ICON_ERROR)
            wx.CallAfter(self.update_revised_prompt, str(e), pos,True, True)
            pub.sendMessage("increment_counter")
            return
        finally:
            #wx.CallAfter(self.generate_button.Enable)
            
            self.timer.Stop()
            self.status_bar.SetProgress(100, pos)

        image = self.data_to_image(image_data)
        wx.CallAfter(self.display_image, image, pos)
        wx.CallAfter(self.update_revised_prompt, revised_prompt, pos)
        pub.sendMessage("increment_counter")

    async def generate_image(self, prompt): 
        client = OpenAI(api_key=api_key)  # will use environment "OPENAI_API_KEY"
        
        image_params= deepcopy(self.image_params)
        image_params.update({"prompt": prompt}) 
        if self.is_hd:
            image_params.update({"quality": "hd"})
        image_params.update({"size": self.image_size.GetValue()})
        image_params.update({"model": self.model_name.GetValue()})
        #pp(image_params)
        images_response = await self.loop.run_in_executor(None, lambda: client.images.generate(**image_params))
        revised_prompt= images_response.data[0].model_dump()['revised_prompt']
        return images_response.data[0].model_dump()["b64_json"], revised_prompt

    def data_to_image(self, data):
        image_data = base64.b64decode(data)
        return Image.open(BytesIO(image_data))

    def update_revised_prompt(self, revised_prompt, pos, set_visible=False, error=False):
        row,col=pos
        text_ctrl=self.text_controls[row][col]
        text_ctrl.SetValue(revised_prompt)
        if set_visible:
            text_ctrl.Show()
            self.panels[row][col].Layout()
        if error:
            text_ctrl.SetForegroundColour(wx.RED)
        else:
            text_ctrl.SetForegroundColour(wx.BLACK)

        
    def display_image(self, image, pos):
        width, height = image.size
        orig=image
        if 1:
            from datetime import datetime
            # Get current date and time
            now = datetime.now()
            # Format as a string
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            # Append to filename
            row,col=pos
            filename = join('generated',f"{self.num_of_im_to_generate}.{row}_{col}.{width}_{height}.{timestamp_str}.png")
            image.save(filename)
        if self.rows*self.cols>2:
            if self.image_size.GetValue() not in ["256x256", "512x512"]:
                if self.image_size.GetValue()  in ["1024x1024"]:

                    image = image.resize((int(width // 2.1), int(height // 2.1)))  # resize for display
                else:
                    image = image.resize((int(width // 2.5), int(height // 2.5)))  # resize for display
        wx_image = wx.Image(image.size[0], image.size[1])
        wx_image.SetData(image.convert("RGB").tobytes())
        bitmap = wx_image.ConvertToBitmap()
        row, col=pos
        if self.bitmaps[row][col]:  
            self.bitmaps[row][col].Destroy()
            self.images[row][col].Destroy()
        self.images[row][col] = orig
        self.bitmaps[row][col] = wx.StaticBitmap(self.panels[row][col], bitmap=bitmap)
        if 0:
            sizer = self.panels[row][col].GetSizer()
            if sizer is None:
                sizer = wx.BoxSizer(wx.VERTICAL)
                self.panels[row][col].SetSizer(sizer)        
            
            sizer.Add(self.bitmaps[row][col], 1, wx.EXPAND)
        self.bitmaps[row][col].pos=pos
        self.bitmaps[row][col].Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu) 
        self.bitmaps[row][col].Bind(wx.EVT_LEFT_DCLICK, self.on_image_dclick)
        self.bitmaps[row][col].Bind(wx.EVT_MOTION, self.on_mouse_hover)
        self.bitmaps[row][col].Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
                  


        #panel=self.panels[row][col]
        #panel.Update()
        #panel.Layout()
        self.scrolled_window.Layout()
        self.scrolled_window.GetSizer().FitInside(self.scrolled_window)
        self.Layout()
    def on_mouse_hover(self, event):

        if wx.GetKeyState(wx.WXK_CONTROL):
            if not self.static_bitmap:
                row,col=event.GetEventObject().pos
                image=self.images[row][col]
                wx_image = wx.Image(image.size[0], image.size[1])
                wx_image.SetData(image.convert("RGB").tobytes())
                bitmap = wx_image.ConvertToBitmap()

                self.static_bitmap = wx.StaticBitmap(self.popup, bitmap=bitmap)
                self.popup.SetSize(self.static_bitmap.GetSize())   



                             
            pos = self.ClientToScreen(event.GetPosition())
            self.popup.Position(pos, (0, 0))
            
            #create new bitmap

            self.popup.Show()

    def on_mouse_leave(self, event):
        self.popup.Hide()
        if self.static_bitmap:
            self.static_bitmap.Destroy()

    def on_context_menu(self, event):
        
        # Store the wx.StaticBitmap that was right-clicked
        self.clicked_bitmap = event.GetEventObject()
        #print('clicked_bitmap.pos', self.clicked_bitmap.pos)
        self.popup_menu = wx.Menu()
        copy_item = self.popup_menu.Append(wx.ID_COPY, "Copy")
        self.Bind(wx.EVT_MENU, self.on_copy, id=copy_item.GetId())
        self.PopupMenu(self.popup_menu)


    def pil_image_to_wx_bitmap(self, pil_image):
        width, height = pil_image.size
        wx_image = wx.Image(width, height)
        wx_image.SetData(pil_image.convert("RGB").tobytes())
        return wx_image.ConvertToBitmap()
    def on_copy(self, event):
        # Use the stored wx.StaticBitmap
        #print(222, event.GetEventObject())
        #clicked_bitmap=self.clicked_bitmap.GetBitmap()
        pos=self.clicked_bitmap.pos
        if 1:
            assert pos
            #clicked_bitmap = self.clicked_bitmap.GetBitmap() if self.clicked_bitmap else None
            #assert clicked_bitmap
            image=self.images[pos[0]][pos[1]]
            if image:
                # Convert the wx.Bitmap to a wx.Image
                #image = clicked_bitmap.ConvertToImage()

                # Convert the wx.Image back to a wx.Bitmap

                bitmap = self.pil_image_to_wx_bitmap(image)

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
