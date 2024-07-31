import wx
import wx.stc as stc
import wx.lib.agw.aui as aui
from include.Common_Panel import StyledTextDisplay
from pubsub import pub
from pprint import pprint as pp 
from include.Common import *
import time, random
from os.path import isfile, join  , isdir  
from datetime import datetime
e=sys.exit
import include.config.init_config as init_config 
apc = init_config.apc
apc.canvas={}
class PromptCtrl(StyledTextDisplay):
    subscribed=False
    def __init__(self, parent,chat):
        super().__init__(parent)
        self.chat=chat
        self.prompt_path=None
        if 'default_file' in chat:
            self.prompt_path = chat.default_file
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('V'), wx.ID_PASTE)
        ])
        #self.SetAcceleratorTable(accel_tbl)
        #self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        self.SetAcceleratorTable(accel_tbl)
        self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        
        if not PromptCtrl.subscribed:
                
            pub.subscribe(self.OnOpenPromptFile, 'open_prompt_file')
            PromptCtrl.subscribed=True
    def OnOpenPromptFile(self, file_path):

        if self.IsTabVisible():
            print('Opening prompt file...')
            self.load_prompt_file(file_path)
        else:
            print('Not visible')
    def IsTabVisible(self):
        parent_notebook = self.GetParent()  # Assuming direct parent is the notebook
        current_page = parent_notebook.GetCurrentPage()
        return current_page == self            
    def OnPaste(self, event):
        print('Pasting...')
        clipboard = wx.Clipboard.Get()
        if clipboard.Open():
            #get text from clipboard
            if clipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                data_object = wx.TextDataObject()
                if clipboard.GetData(data_object):
                    text = data_object.GetText()
                                        
                    # Save the image to a temporary file or set it directly to the canvas
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    temp_prompt_path = join('image_log',f'temp_pasted_image_{timestamp}.png' )                  
                    
                    with open(temp_prompt_path, 'w') as f:
                        f.write(data_object.GetText())
                    self.load_prompt_file(temp_prompt_path)

                else:
                    print("Clipboard data retrieve failed")
            

            else:
                print("Clipboard does not contain text data")
            clipboard.Close()
            log('Paste done.')
            set_status('Paste done.') 
        else:
            print("Unable to open clipboard")

    def load_prompt(self, prompt_path):
        text = None
        
        assert isfile(prompt_path), prompt_path
        with open(prompt_path, 'r') as f:
            text = f.read()
            
        return text
    
    def load_prompt_file(self, file_path):
        # This method will be used to load and display an image on the canvas
        self.prompt_path = file_path
        self.DisplayPrompt(file_path)
        #self.update_notebook_tab_label(file_path)

    def OnPromptClick(self, event):
        # Set focus to the notebook tab containing the static bitmap (canvasCtrl)
        self.SetFocus()


    def DisplayPrompt(self, prompt_path):
        # Load the image
     
        txt = self.load_prompt(prompt_path)
        if txt is None:
            print("Failed to load prompt.")
            return
        
        self.SetText(txt)



class CanvasCtrl(wx.Panel):
    subscribed=False
    def __init__(self, parent,chat):
        super().__init__(parent)
        self.chat=chat
        self.image_path=None
        if 'default_file' in chat:
            self.image_path = chat.default_file
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('V'), wx.ID_PASTE)
        ])
        #self.SetAcceleratorTable(accel_tbl)
        #self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        self.SetAcceleratorTable(accel_tbl)
        self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        
        if not CanvasCtrl.subscribed:
                
            pub.subscribe(self.OnOpenImageFile, 'open_image_file')
            CanvasCtrl.subscribed=True
    def OnOpenImageFile(self, file_path):

        if self.IsTabVisible():
            print('Opening image file...')
            self.load_image_file(file_path)
        else:
            print('Not visible')
    def IsTabVisible(self):
        parent_notebook = self.GetParent()  # Assuming direct parent is the notebook
        current_page = parent_notebook.GetCurrentPage()
        return current_page == self            
    def OnPaste(self, event):
        print('Pasting...')
        clipboard = wx.Clipboard.Get()
        if clipboard.Open():
            if clipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
                data_object = wx.BitmapDataObject()
                if clipboard.GetData(data_object):
                    bitmap = data_object.GetBitmap()
                    image = wx.Image(bitmap.ConvertToImage())
                    
                    # Save the image to a temporary file or set it directly to the canvas
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    temp_image_path = join('image_log',f'temp_pasted_image_{timestamp}.png' )                  
                    
                    image.SaveFile(temp_image_path, wx.BITMAP_TYPE_PNG)
                    self.load_image_file(temp_image_path)
                else:
                    print("Clipboard data retrieve failed")
            else:
                print("Clipboard does not contain image data")
            clipboard.Close()
            log('Paste done.')
            set_status('Paste done.') 
        else:
            print("Unable to open clipboard")

    def load_image(self, image_path):
        image = None
        try:
            if image_path.lower().endswith('.webp'):
                pil_image = PILImage.open(image_path)
                image = wx.Image(pil_image.size[0], pil_image.size[1])
                image.SetData(pil_image.convert("RGB").tobytes())
                image.SetAlpha(pil_image.convert("RGBA").tobytes()[3::4])
            else:
                image = wx.Image(image_path, wx.BITMAP_TYPE_ANY)
            self.image_path = image_path
        except Exception as e:
            print(f"Error loading image: {e}")
            log(f"Error loading image: {e}", 'red')
            
        return image
    
    def load_image_file(self, file_path):
        # This method will be used to load and display an image on the canvas
        self.image_path = file_path
        self.DisplayImageOnCanvas(file_path)
        #self.update_notebook_tab_label(file_path)

    def OnBitmapClick(self, event):
        # Set focus to the notebook tab containing the static bitmap (canvasCtrl)
        self.SetFocus()


    def DisplayImageOnCanvas(self, image_path):
        # Load the image
        if hasattr(self, 'static_bitmap') and self.static_bitmap:
            self.static_bitmap.Destroy()      
        image = self.load_image(image_path)
        if image is None:
            print("Failed to load image.")
            return
        
        # Get the top-level window size
        top_level_window = self.GetTopLevelParent()
        canvas_width, canvas_height = top_level_window.GetSize()
        canvas_width=canvas_width/2
        canvas_height -=200
        # Get the image size
        image_width = image.GetWidth()
        image_height = image.GetHeight()
        
        # Calculate the new size maintaining aspect ratio
        if image_width > image_height:
            new_width = canvas_width
            new_height = canvas_width * image_height / image_width
        else:
            new_height = canvas_height
            new_width = canvas_height * image_width / image_height
        
        # Resize the image
        image = image.Scale(int(new_width), int(new_height), wx.IMAGE_QUALITY_HIGH)
        
        # Convert it to a bitmap
        bitmap = wx.Bitmap(image)
        
        # Create a StaticBitmap widget to display the image
        self.static_bitmap = wx.StaticBitmap(self, -1, bitmap)
        self.static_bitmap.Bind(wx.EVT_LEFT_DOWN, self.OnBitmapClick)
        # Optionally, resize the panel to fit the image
        self.SetSize(bitmap.GetWidth(), bitmap.GetHeight()) 

class MyNotebookImagePanel(wx.Panel):
    subscribed=False
    def __init__(self, parent, tab_id):
        super(MyNotebookImagePanel, self).__init__(parent)
        
        notebook = aui.AuiNotebook(self)
        self.tab_id=tab_id
        self.notebook = notebook
        self.canvasCtrl=[]
        chat = apc.chats[tab_id]
        canvasCtrl=CanvasCtrl(notebook, chat)
        self.canvasCtrl.append(canvasCtrl)
        

        apc.canvas[tab_id] = self.canvasCtrl
        self.static_bitmap = None
        #self.Bind(wx.EVT_SIZE, self.OnResize)
        self.image_path = None
        
        chat.num_of_images=    chat.get('num_of_images',    1)
        if canvasCtrl.image_path:
            
            print(canvasCtrl.image_path)
            canvasCtrl.DisplayImageOnCanvas(canvasCtrl.image_path)
            notebook.AddPage(canvasCtrl, canvasCtrl.image_path)
        else:
            notebook.AddPage(canvasCtrl, f'Image_1')
            
            
            for i in range(2,chat.num_of_images+1):
                canvasCtrl = CanvasCtrl(notebook, chat)
                self.canvasCtrl.append(canvasCtrl)                
                notebook.AddPage(canvasCtrl, f'Image_{i}')
                
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Layout()
        
        # Bind paste event
        #self.Bind(wx.EVT_TEXT_PASTE, self.OnPaste)
        
        # Bind key down event to handle Ctrl+V

        #self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        pub.subscribe(self.load_random_images, 'load_random_images')
        pub.subscribe(self.reset_image_pool, 'reset_image_pool')
        if 0: #not MyNotebookImagePanel.subscribed:
                
            pub.subscribe(self.load_random_images, 'load_random_images')
            pub.subscribe(self.reset_image_pool, 'reset_image_pool')
            
            MyNotebookImagePanel.subscribed=True  
        self.notebook.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.onTabClose)
    def onTabClose(self, event):
        # Check if the panel being closed is MyNotebookImagePanel
        page_index = event.GetSelection()
        #print(page_index, self.notebook.GetPageCount(), isinstance(self, MyNotebookImagePanel))
        page = self.notebook.GetPage(page_index)
        if isinstance(self, MyNotebookImagePanel):
            # Prevent the tab from closing
            #dialog asking if want to close
            dialog=wx.MessageDialog(self, 'Are you sure you want to close this tab?', 'Close Tab', wx.YES_NO | wx.ICON_QUESTION)
            response = dialog.ShowModal()
            if response == wx.ID_YES:
                # Close the tab
                event.Skip()    
            else:       

                event.Veto()              
    def get_image_list(self, chat):
        from pathlib import Path

        image_path = Path.home() / 'Downloads'
        image_path = Path.cwd() / 'in' / chat.img_source
        assert isdir(join(image_path)), image_path  
        #image_path= Path(__file__).parent / 'test'
        print(image_path)
        
        jpg_files = list(image_path.glob('*.jpg')) +list(image_path.glob('*.jpeg'))
        png_files = list(image_path.glob('*.png'))
        webp_files = list(image_path.glob('*.webp'))
        assert len(jpg_files + png_files + webp_files), f'No images found in {image_path}'
        return  jpg_files + png_files + webp_files
    def reset_image_pool(self, tab_id):
        print('Resetting image pool...')
        chat = apc.chats[tab_id]
        self.image_pool = self.get_image_list(chat)
    def load_random_images(self, tab_id):
        chat = apc.chats[self.tab_id]
        if tab_id == self.tab_id:
            if not hasattr(self, 'image_pool'):
                self.image_pool = self.get_image_list(chat)

            
            print('Loading random images...', chat.num_of_images)
            
            assert len(self.image_pool)>=chat.num_of_images, f'Not enough images in pool: {len(self.image_pool)} < {chat.num_of_images}'
            random_subset = random.sample(self.image_pool, chat.num_of_images)
            #pp(random_subset)
            if 1:
                for i, fn in enumerate(random_subset):
                    print(i, fn)
                    self.canvasCtrl[i].load_image_file(str(fn))
        else:
            pass
            #print('Not for me', self.tab_id)
    def update_notebook_tab_label(self, file_path):
        # Update the notebook tab label to the new file name
        file_name = os.path.basename(file_path)
        notebook = self.notebook
        
        # Find the tab with the canvas and update its label
        for i in range(notebook.GetPageCount()):
            if notebook.GetPage(i) == self.canvasCtrl:
                notebook.SetPageText(i, file_name)
                break
        





    def ScaleImage(self, image, max_width, max_height):
        image_width = image.GetWidth()
        image_height = image.GetHeight()

        # Calculate the new size maintaining the aspect ratio
        if image_width > image_height:
            new_width = max_width
            new_height = max_width * image_height / image_width
            if new_height > max_height:
                new_height = max_height
                new_width = max_height * image_width / image_height
        else:
            new_height = max_height
            new_width = max_height * image_width / image_height
            if new_width > max_width:
                new_width = max_width
                new_height = max_width * image_height / image_width

        # Resize the image
        return image.Scale(int(new_width), int(new_height), wx.IMAGE_QUALITY_HIGH)
            




    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('V') or event.GetKeyCode() == wx.WXK_RETURN):
            self.log('Loading...')
            self.OnPaste(event)
            self.log('Done.')
        else:
            event.Skip()

    def log(self, message):
        pub.sendMessage('log', message=f'{self.__class__.__name__}: {message}')

    def output(self, message):
        pub.sendMessage('output', message=f'{message}')

    def exception(self, message):
        pub.sendMessage('exception', message=f'{message}')



class MyNotebookPromptPanel(wx.Panel):
    subscribed=False
    def __init__(self, parent, tab_id):
        super(MyNotebookPromptPanel, self).__init__(parent)
        
        notebook = aui.AuiNotebook(self)
        self.tab_id=tab_id
        self.notebook = notebook
        self.promptCtrl=[]
        chat = apc.chats[tab_id]
        promptCtrl=CanvasCtrl(notebook, chat)
        self.promptCtrl.append(promptCtrl)

        apc.prompts = self.promptCtrl
        
        #self.Bind(wx.EVT_SIZE, self.OnResize)
        
        
        chat.num_of_prompts=    chat.get('num_of_prompts',    1)
        if promptCtrl.prompt_path:
            
            print(promptCtrl.prompt_path)
            promptCtrl.DisplayPrompt(promptCtrl.prompt_path)
            notebook.AddPage(promptCtrl, promptCtrl.prompt_path)
        else:
            notebook.AddPage(promptCtrl, f'Prompt_1')
            
            
            for i in range(2,chat.num_of_prompts+1):
                promptCtrl = PromptCtrl(notebook, chat)
                self.promptCtrl.append(promptCtrl)                
                notebook.AddPage(promptCtrl, f'Prompt_{i}')
                
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Layout()
        
        # Bind paste event
        #self.Bind(wx.EVT_TEXT_PASTE, self.OnPaste)
        
        # Bind key down event to handle Ctrl+V

        #self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        pub.subscribe(self.load_random_prompts, 'load_random_prompts')
        self.prompt_pool=self.get_prompt_list()
        if 0 and not MyNotebookPromptPanel.subscribed:
                
            pub.subscribe(self.load_random_prompts, 'load_random_prompts')
            MyNotebookPromptPanel.subscribed=True  
        self.notebook.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.onTabClose)

    
    def onTabClose(self, event):
        # Check if the panel being closed is MyNotebookImagePanel
        page_index = event.GetSelection()
        #print(page_index, self.notebook.GetPageCount(), isinstance(self, MyNotebookImagePanel))
        page = self.notebook.GetPage(page_index)
        if isinstance(self, MyNotebookPromptPanel):
            # Prevent the tab from closing
            #dialog asking if want to close
            dialog=wx.MessageDialog(self, 'Are you sure you want to close this tab?', 'Close Tab', wx.YES_NO | wx.ICON_QUESTION)
            response = dialog.ShowModal()
            if response == wx.ID_YES:
                # Close the tab
                event.Skip()    
            else:       

                event.Veto()              
    def get_prompt_list(self):
        from pathlib import Path

        prompt_path = Path(apc.home)/'prompts'
        #image_path= Path(__file__).parent / 'test'
        #print(apc.home)
        #print(prompt_path)
        #e()
        txt_files = list(prompt_path.glob('*.txt')) 

        return  txt_files
    def load_random_prompts(self, tab_id):
        print(tab_id == self.tab_id , tab_id, self.tab_id)
        if tab_id == self.tab_id:
            
            chat = apc.chats[self.tab_id]
            print('Loading random prompts...', chat.num_of_prompts)
            
            print(len(self.prompt_pool))
            random_subset = random.sample(self.prompt_pool, chat.num_of_prompts)
            pp(random_subset)
            if 1:
                for i, fn in enumerate(random_subset):
                    print(i, fn)
                    self.promptCtrl[i].load_prompt_file(str(fn))
        else:
            pass
            #print('Not for me', self.tab_id)
    def update_notebook_tab_label(self, file_path):
        # Update the notebook tab label to the new file name
        file_name = os.path.basename(file_path)
        notebook = self.notebook
        
        # Find the tab with the canvas and update its label
        for i in range(notebook.GetPageCount()):
            if notebook.GetPage(i) == self.promptCtrl:
                notebook.SetPageText(i, file_name)
                break
        







    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('V') or event.GetKeyCode() == wx.WXK_RETURN):
            self.log('Loading...')
            self.OnPaste(event)
            self.log('Done.')
        else:
            event.Skip()

    def log(self, message):
        pub.sendMessage('log', message=f'{self.__class__.__name__}: {message}')

    def output(self, message):
        pub.sendMessage('output', message=f'{message}')

    def exception(self, message):
        pub.sendMessage('exception', message=f'{message}')




class _Copilot_DisplayPanel(StyledTextDisplay):
    subscribed=False
    def __init__(self, parent, tab_id):
        StyledTextDisplay.__init__(self,parent)
        
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.SetFont(font) 
     
        self.tab_id=tab_id

        if 1: #not Copilot_DisplayPanel.subscribed:
                
            pub.subscribe(self.AddChatOutput, 'chat_output')
            #print('#' * 20, self.tab_id, 'subscribing to chat_output')
            Copilot_DisplayPanel.subscribed=True 
        else:
            pass
            #print('-' * 20, 'Already subscribed', self.tab_id)
            #print('Copilot_DisplayPanel passing on subscription', self.tab_id)       
    def IsTabVisible(self):
        # Get the parent notebook
        parent_notebook = self.GetParent().GetParent().GetParent()
        #print ('Copilot', self.tab_id, parent_notebook, parent_notebook.GetSelection())
        # Check if the current page is the selected page in the parent notebook
        return parent_notebook.GetPage(parent_notebook.GetSelection())       
    def AddChatOutput(self, message, tab_id):
        #print(1111, self.tab_id,tab_id, self.tab_id==tab_id, message)
        #print('Copilot',  self.IsTabVisible(), self.tab_id)
        if self.tab_id==tab_id:
            #start_pos = self.GetLastPosition()
            if 1: #for line in message.splitlines():

                wx.CallAfter(self.AddOutput, message)
                
                #end_pos = self.chatDisplay.GetLastPosition()
                #self.chatDisplay.SetStyle(start_pos, end_pos, wx.TextAttr(wx.BLACK))        
    def OnShowTabId(self):
        print('show_tab_id', self.tab_id)

          


class Copilot_DisplayPanel(wx.Panel):
    def __init__(self, parent, tab_id, chat):
        super(Copilot_DisplayPanel, self).__init__(parent)
        apc.chats[tab_id]=chat
        # Create a splitter window
        self.copilot_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        #splitter = wx.SplitterWindow(self, style = wx.SP_3D| wx.SP_LIVE_UPDATE)
        self.tab_id=tab_id

        # Initialize the notebook_panel and logPanel
        self.notebook_panel=notebook_panel = MyNotebookImagePanel(self.copilot_splitter, tab_id)
        notebook_panel.SetMinSize((-1, 50))
        #notebook_panel.SetMinSize((800, -1))
        self.chatPanel = _Copilot_DisplayPanel(self.copilot_splitter, tab_id)
        self.chatPanel.SetMinSize((-1, 50))

        # Add notebook panel and log panel to the splitter window
        #self.splitter.AppendWindow(notebook_panel)
        #self.splitter.AppendWindow(self.logPanel)
        self.copilot_splitter.SplitVertically( self.chatPanel, notebook_panel) 
        #print(111, self.GetSize().GetWidth() // 2)
        self.copilot_splitter.SetSashPosition(500)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.copilot_splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Set initial sash positions
        #
        self.Bind(wx.EVT_SIZE, self.OnResize)
    def _GetImagePath(self, tab_id):
        assert tab_id==self.tab_id, self.__class__.__name__
        
        out=[]
        notebook= self.notebook_panel.promptCtrl
        for prompt in  self.notebook_panel.promptCtrl:
            out.append(prompt.prompt_path)
        
    def GetImagePath(self, tab_id):
        assert tab_id==self.tab_id, self.__class__.__name__
        
        out=[]
        notebook= self.notebook_panel.notebook
       
        page_count = notebook.GetPageCount()

        for page_index in range(page_count):
            # Get the panel (page) at the current index
            page = notebook.GetPage(page_index)
            
            out.append(page.image_path)
        return out
    
    def OnResize(self, event):
        # Adjust the sash position to keep the vertical splitter size constant
        width, height = self.GetSize()
        self.copilot_splitter.SetSashPosition(width // 2)
        event.Skip() 