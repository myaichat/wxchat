class CanvasCtrl(wx.Panel):
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
        pub.subscribe(self.OnOpenImageFile, 'open_image_file')
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
        except Exception as e:
            print(f"Error loading image: {e}")
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
    def __init__(self, parent, tab_id):
        super(MyNotebookImagePanel, self).__init__(parent)
        
        notebook = aui.AuiNotebook(self)
        self.tab_id=tab_id
        self.notebook = notebook
        self.canvasCtrl=[]
        chat = apc.chats[tab_id]
        canvasCtrl=CanvasCtrl(notebook, chat)
        self.canvasCtrl.append(canvasCtrl)

        apc.canvas = self.canvasCtrl
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
        self.image_pool=self.get_image_list()
    def get_image_list(self):
        from pathlib import Path

        image_path = Path.home() / 'Downloads'
        #image_path= Path(__file__).parent / 'test'
        print(image_path)
        
        jpg_files = list(image_path.glob('*.jpg')) +list(image_path.glob('*.jpeg'))
        png_files = list(image_path.glob('*.png'))
        webp_files = list(image_path.glob('*.webp'))
        
        return  jpg_files + png_files + webp_files
    def load_random_images(self, tab_id):
        if tab_id == self.tab_id:
            
            chat = apc.chats[self.tab_id]
            print('Loading random images...', chat.num_of_images)
            
            print(len(self.image_pool))
            random_subset = random.sample(self.image_pool, chat.num_of_images)
            pp(random_subset)
            if 1:
                for i, fn in enumerate(random_subset):
                    self.canvasCtrl[i].load_image_file(str(fn))
        else:
            print('Not for me', self.tab_id)
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



class Copilot_DisplayPanel(StyledTextDisplay):
    def __init__(self, parent, tab_id):
        StyledTextDisplay.__init__(self,parent)
        
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.SetFont(font) 
     
        self.tab_id=tab_id
        pub.subscribe(self.AddChatOutput, 'chat_output')
        #pub.subscribe(lambda message, tab_id: self.AddOutput(message, tab_id), 'chat_output')
        pub.subscribe(self.OnShowTabId, 'show_tab_id') 
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

          


class Microsoft_Copilot_DisplayPanel(wx.Panel):
    def __init__(self, parent, tab_id, chat):
        super(Microsoft_Copilot_DisplayPanel, self).__init__(parent)
        apc.chats[tab_id]=chat
        # Create a splitter window
        self.copilot_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        #splitter = wx.SplitterWindow(self, style = wx.SP_3D| wx.SP_LIVE_UPDATE)
        self.tab_id=tab_id

        # Initialize the notebook_panel and logPanel
        self.notebook_panel=notebook_panel = MyNotebookImagePanel(self.copilot_splitter, tab_id)
        notebook_panel.SetMinSize((-1, 50))
        #notebook_panel.SetMinSize((800, -1))
        self.chatPanel = Copilot_DisplayPanel(self.copilot_splitter, tab_id)
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
    def GetImagePath(self, tab_id):
        assert tab_id==self.tab_id, self.__class__.__name__
        
        out=[]
        notebook= self.notebook_panel.canvasCtrl
        for canvas in  self.notebook_panel.canvasCtrl:
            out.append(canvas.image_path)
        return out

    def OnResize(self, event):
        # Adjust the sash position to keep the vertical splitter size constant
        width, height = self.GetSize()
        self.copilot_splitter.SetSashPosition(width // 2)
        event.Skip()        

                                         

class Microsoft_ChatDisplayNotebookPanel(wx.Panel):
    def __init__(self, parent, vendor_tab_id, ws_name):
        super(Microsoft_ChatDisplayNotebookPanel, self).__init__(parent)
        self.tabs={}
        self.ws_name=ws_name
        self.chat_notebook = wx.Notebook(self, style=wx.NB_BOTTOM)
        self.vendor_tab_id=vendor_tab_id
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.chat_notebook, 1, wx.EXPAND)
        #self.chat_notebook.SetActiveTabColour(wx.RED)
        #self.chat_notebook.SetNonActiveTabTextColour(wx.BLUE)
        self.SetSizer(sizer)    
        self.chat_notebook.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.chat_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.chat_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        pub.subscribe(self.OnWorkspaceTabChanging, 'workspace_tab_changing')
        pub.subscribe(self.OnWorkspaceTabChanged, 'workspace_tab_changed')
        pub.subscribe(self.OnVendorspaceTabChanging, 'vendor_tab_changing')   
        pub.subscribe(self.OnVendorspaceTabChanged, 'vendor_tab_changed')
    def get_active_chat_panel(self):
        active_chat_tab_index = self.chat_notebook.GetSelection()
        if active_chat_tab_index == wx.NOT_FOUND:
            return None
        return self.chat_notebook.GetPage(active_chat_tab_index)
            
    def OnWorkspaceTabChanging(self, message):
        if message==self.ws_name:
            active_chat_panel = self.get_active_chat_panel()
            if active_chat_panel is not None:
                active_tab_id = active_chat_panel.tab_id
                #print('OnWorkspaceTabChanging dd', message, self.vendor_tab_id, self.ws_name, active_tab_id)
                pub.sendMessage('save_question_for_tab_id', message=active_tab_id)
            else:
                print('No active chat panel found')
        
    def OnWorkspaceTabChanged(self, message):
        if message==self.ws_name:
            active_chat_panel = self.get_active_chat_panel()
            if active_chat_panel is not None:
                active_tab_id = active_chat_panel.tab_id
                #print('OnWorkspaceTabChanged', message, self.vendor_tab_id, self.ws_name, active_tab_id)
            if 1:
                pub.sendMessage('restore_question_for_tab_id', message=active_tab_id)

                assert active_tab_id in apc.chats
                chat=apc.chats[active_tab_id]
                print('swapping', active_tab_id )
                pub.sendMessage('swap_input_panel', chat=chat,tab_id=active_tab_id)
                            

    def OnVendorspaceTabChanging(self, message):
        #print('TODO OnVendorspaceTabChanging', message)
        #raise NotImplementedError
        pass
    def OnVendorspaceTabChanged(self, message):
       
        #print('TODO OnVendorspaceTabChanged', message)
        
        #raise NotImplementedError
        pass
    def OnMouseMotion(self, event):
        # Get the mouse position
        position = event.GetPosition()
        # Get the tab index under the mouse position
        #print(self.notebook.HitTest(position))
        tab_index, _= self.chat_notebook.HitTest(position)

        #print(tab_index)
        # If the mouse is over a tab
        if tab_index >= 0:
            # Get the tab text
            tab_text = self.chat_notebook.GetPageText(tab_index)
            # Set the tab tooltip
            tt=self.GetToolTipText()
            self.chat_notebook.SetToolTip(f'{tt}/{tab_text}')
        else:
            self.chat_notebook.SetToolTip(None)
        event.Skip()
    def GetToolTipText(self):
        tab_id=self.tabs[self.chat_notebook.GetSelection()]
        return f'{apc.default_workspace.name}/{apc.default_workspace.vendor} {apc.chats[tab_id].chat_type}'
        

    def AddTab(self, chat):
        chat_notebook=self.chat_notebook
        title=f'{chat.chat_type}: {chat.name}'
        title=f'{chat.name}'
        chatDisplay=None
        tab_id=(chat.workspace, chat.chat_type, chat.vendor,self.vendor_tab_id, chat_notebook.GetPageCount())
        self.tabs[chat_notebook.GetPageCount()]=tab_id
        if 1:
            #pp(panels.__dict__)
            #pp(chat.__dict__)
            display_panel = f'{chat.vendor}_{chat.chat_type}_{panels.chat}'
            #print('display_panel', display_panel)
            try:
                assert display_panel in globals(), display_panel
                print(f'\t\tAdding {chat.workspace} "{chat.chat_type}" panel:', display_panel)
                cls= globals()[display_panel]
                # Gpt4_Chat_DisplayPanel/ Gpt4_Copilot_DisplayPanel
                try:
                    chatDisplay = cls (chat_notebook, tab_id=tab_id, chat=chat)
                    #chatDisplay.SetFocus()
                except:
                    print(format_stacktrace())
                    print(f'Error in {display_panel} class')
                    e(1)
                if 1:
                    pub.sendMessage('swap_input_panel', chat=chat, tab_id=tab_id)
            except AssertionError:
                #raise AssertionError(f"Display class '{display_panel}' does not exist.")
                raise
        assert chatDisplay   
        chat_notebook.AddPage(chatDisplay, title)
        chat_notebook.SetSelection(chat_notebook.GetPageCount() - 1)  
        
        chat_tab_id = chat_notebook.GetPageCount() - 1
        #self.SetTabLabelColor(chat_tab_id, wx.Colour(255, 0, 0))
        chatDisplay.tab_id=self.tab_id=tab_id=(chat.workspace,chat.chat_type, chat.vendor, self.vendor_tab_id, chat_tab_id)
        apc.chats[tab_id]=chat
        apc.chat_panels[tab_id]=chatDisplay
        
        pub.sendMessage('set_chat_defaults', tab_id=tab_id)

    def OnPageChanging(self, event):
        # Code to execute when the notebook page is about to be changed
        #print("Notebook page is about to be changed")
        # Get the index of the new tab that is about to be selected
        nb=event.GetEventObject()
        oldTabIndex = event.GetSelection()
        current_chatDisplay = nb.GetPage(oldTabIndex)
        #print('OnPageChanging 111', current_chatDisplay.tab_id)
        pub.sendMessage('save_question_for_tab_id', message=current_chatDisplay.tab_id)
  
        event.Skip()

    
    def OnPageChanged(self, event):
        # Code to execute when the notebook page has been changed
        nb=event.GetEventObject()
        newtabIndex = nb.GetSelection()
        current_chatDisplay = nb.GetPage(newtabIndex)
        tab_id=current_chatDisplay.tab_id
        #print('OnPageChanged 222', tab_id)
        pub.sendMessage('restore_question_for_tab_id', message=tab_id)
        current_chatDisplay = nb.GetPage(newtabIndex)
        #pp(current_chatDisplay.tab_id)
        #e()
        if tab_id in apc.chats:
            chat=apc.chats[tab_id]
            pub.sendMessage('swap_input_panel', chat=chat,tab_id=tab_id)
        # Continue processing the event
        event.Skip()          



    def get_latest_chat_tab_id(self):
        return self.GetPageCount() - 1

class ChatHistoryDialog(wx.Dialog):
    def __init__(self, parent, tab_id, chat_history):
        super(ChatHistoryDialog, self).__init__(parent, title="Chat History", size=(600, 400))
        self.tab_id = tab_id
        self.chat_history = chat_history
        
        # Create the ListCtrl
        self.listCtrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        
        # Add columns
        self.listCtrl.InsertColumn(0, 'Role', width=100)
        self.listCtrl.InsertColumn(1, 'Content', width=450)
        
        # Populate the ListCtrl with chat history
        self.populate_list_ctrl()
        
        # Create a close button
        closeButton = wx.Button(self, label="Close")
        closeButton.Bind(wx.EVT_BUTTON, self.on_close)
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.listCtrl, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(closeButton, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(sizer)
        
    def populate_list_ctrl(self):
        for entry in self.chat_history[self.tab_id]:
            index = self.listCtrl.InsertItem(self.listCtrl.GetItemCount(), entry['role'])
            self.listCtrl.SetItem(index, 1, entry['content'])
    
    def on_close(self, event):
        self.Close()        
class Microsoft_Copilot_InputPanel(wx.Panel, NewChat, GetClassName, Base_InputPanel):
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Microsoft_Copilot_InputPanel, self).__init__(parent)
        NewChat.__init__(self)
        GetClassName.__init__(self)
        self.tabs={}
        self.image_id=1
        self.tab_id=tab_id
        chat=   apc.chats[tab_id]
        self.chat_type=chat.chat_type
        chatHistory[self.tab_id]=[]
        #chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Copilot[default_copilot_template]}]
        self.askLabel = wx.StaticText(self, label=f'Ask Phy-3 {tab_id}:')
        if 0:
            model_names = [DEFAULT_MODEL, 'gpt-4-turbo', 'gpt-4']  # Add more model names as needed
            self.model_dropdown = wx.ComboBox(self, choices=model_names, style=wx.CB_READONLY)
            self.model_dropdown.SetValue(DEFAULT_MODEL)
            
            self.model_dropdown.Bind(wx.EVT_COMBOBOX, self.OnModelChange)

        if 1:       
            max_new_tokens_values = ["256", "512", "1024", "2048", "4096", "8192", "16384", "32768"]
            # Create a ComboBox for max_new_tokens
            self.max_new_tokens_dropdown = wx.ComboBox(self, choices=max_new_tokens_values, style=wx.CB_READONLY)
            self.max_new_tokens_dropdown.SetValue("2048")  # Default value
            chat.max_new_tokens = "2048"
            self.max_new_tokens_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMaxNewTokensChange)
        if 1:
            do_sample_values = ["True", "False"]
            self.do_sample_dropdown = wx.ComboBox(self, choices=do_sample_values, style=wx.CB_READONLY)
            self.do_sample_dropdown.SetValue("False")  # Default value
            chat.do_sample = "False"
            self.do_sample_dropdown.Bind(wx.EVT_COMBOBOX, self.OnDoSampleChange) 
                    
        if 1:       
            temp_vals = ["0", "0.2", "0.4", "0.6", "0.8", "1","1.3","1.6", "2","2.5", "3","4", "5", "10", "20", "50", "100"]
            # Create a ComboBox for max_new_tokens
            self.temp_dropdown = wx.ComboBox(self, choices=temp_vals, style=wx.CB_READONLY)
            self.temp_dropdown.SetValue("1")  # Default value
            chat.temp_val = "1"
            self.temp_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTempChange)

        self.askButton = wx.Button(self, label='Ask', size=(40, 25))
        self.askButton.Bind(wx.EVT_BUTTON, self.onAskButton)

        self.historyButton = wx.Button(self, label='Hist', size=(40, 25))
        self.historyButton.Bind(wx.EVT_BUTTON, self.onHistoryButton)
        # New Random button
        self.randomButton = wx.Button(self, label='Rand', size=(40, 25))
        self.randomButton.Bind(wx.EVT_BUTTON, self.onRandomButton)    

        self.numOfTabsCtrl = wx.TextCtrl(self, value="1", size=(40, 25))
        self.tabsButton = wx.Button(self, label='Tabs', size=(40, 25))
        self.tabsButton.Bind(wx.EVT_BUTTON, self.onTabsButton)

        askSizer = wx.BoxSizer(wx.HORIZONTAL)
        askSizer.Add(self.askLabel, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.max_new_tokens_dropdown, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.do_sample_dropdown, 0, wx.ALIGN_CENTER)    
        askSizer.Add(self.temp_dropdown, 0, wx.ALIGN_CENTER)
        if 0:
            self.pause_panel=pause_panel=PausePanel(self, self.tab_id)
            askSizer.Add(pause_panel, 0, wx.ALL)
  
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.historyButton, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.randomButton, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.numOfTabsCtrl, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.tabsButton, 0, wx.ALIGN_CENTER)
        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE)
        if 1:
            q= apc.chats[self.tab_id].question
            self.tabs[self.tab_id]=dict(q=q)
            questionHistory[self.tab_id]=[q]
            currentQuestion[self.tab_id]=0
            currentModel[self.tab_id]=DEFAULT_MODEL

            #chatHistory[self.tab_id]= [{"role": "system", "content": chat.system}]

        self.inputCtrl.SetValue(self.tabs[self.tab_id]['q'])
        #self.inputCtrl.SetMinSize((-1, 120))  
        self.inputCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(askSizer, 0, wx.EXPAND)
        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.ex=None
        self.receiveing_tab_id=0

        #pub.subscribe(self.SetException, 'fix_exception')
        pub.subscribe(self.SetChatDefaults  , 'set_chat_defaults')
        #pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
        pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
        wx.CallAfter(self.inputCtrl.SetFocus)
        if  not  hasattr(apc, 'vrs'):
            apc.vrs=VisionResponseStreamer(DEFAULT_MODEL)
    def OnDoSampleChange(self, event):
        selected_value = self.do_sample_dropdown.GetValue()
        print(f"Selected do_sample: {selected_value}")
        chat = apc.chats[self.tab_id]
        chat.do_sample = selected_value

    def onTabsButton(self, event):
        try:
            num_of_tabs = int(self.numOfTabsCtrl.GetValue())
            pub.sendMessage('set_num_of_tabs', num=num_of_tabs, tab_id=self.tab_id)
        except ValueError:
            self.log("Invalid number of tabs.", color=wx.RED)

    def onRandomButton(self, event):
        # Implement the random function logic here
        self.log('Random button clicked')
        pub.sendMessage('load_random_images', tab_id=self.tab_id)
    def onHistoryButton(self, event):
        global chatHistory
        dialog = ChatHistoryDialog(self, self.tab_id, chatHistory)
        dialog.ShowModal()
        dialog.Destroy()
        
    def OnMaxNewTokensChange(self, event):
        # This method will be called when the selection changes
        selected_value = self.max_new_tokens_dropdown.GetValue()
        print(f"Selected max_new_tokens: {selected_value}")
        chat = apc.chats[self.tab_id]
        chat.max_new_tokens = selected_value
    def OnTempChange(self, event):

        # This method will be called when the selection changes
        selected_value = self.temp_dropdown.GetValue()
        print(f"Selected temp: {selected_value}")
        chat = apc.chats[self.tab_id]
        chat.temp_val = selected_value            
    def SetTabId(self, tab_id):
        self.tab_id=tab_id
        self.askLabel.SetLabel(f'Ask Phy-3 {tab_id}:')
    def SetChatDefaults(self, tab_id):
        global chatHistory, questionHistory, currentModel
        if tab_id ==self.tab_id:
            assert self.chat_type==tab_id[1]
            chat=apc.chats[tab_id]
  

            self.tabs[self.tab_id]=dict(q=chat.question)
            #chatHistory[self.tab_id]= [{"role": "system", "content": chat.system}]
            questionHistory[self.tab_id]=[]
            currentModel[self.tab_id]=DEFAULT_MODEL 
            chatHistory[self.tab_id]=[]       
    def OnModelChange(self, event):
        # Get the selected model
        selected_model = self.model_dropdown.GetValue()


        # Continue processing the event
        event.Skip()

    def RestoreQuestionForTabId(self, message):
        global currentModel
        tab_id=message
        if tab_id in self.tabs:
            self.inputCtrl.SetValue(self.tabs[message]['q'])
            
            #self.model_dropdown.SetValue(currentModel[message])
            self.tab_id=message
            #self.q_tab_id=message
            #self.inputCtrl.SetSelection(0, -1)
            self.inputCtrl.SetFocus()
    def _SaveQuestionForTabId(self, message):
        global currentModel
        q=self.inputCtrl.GetValue()
        self.tabs[message]=dict(q=q)
        currentModel[message]=self.model_dropdown.GetValue()
        if 0:
            d={"role": "user", "content":q}
            if self.tab_id in chatHistory:
                if d not in chatHistory[self.tab_id]:
                    chatHistory[self.tab_id] += [{"role": "user", "content":q}]


    def SetException(self, message):
        self.ex=message
    def onAskButton(self, event):
        # Code to execute when the Ask button is clicked
        #print('Ask button clicked')
        self.AskQuestion()
    def AskQuestion(self):
        global chatHistory, questionHistory, currentQuestion,currentModel
        try:
            #self.Base_OnAskQuestion()
            question = self.inputCtrl.GetValue()
            if not question:
                self.log('There is no question!', color=wx.RED)
            else:
                question = self.inputCtrl.GetValue()
                self.log(f'Asking question: {question}')
                pub.sendMessage('start_progress')
                #code=???
                chatDisplay=apc.chat_panels[self.tab_id]
                image_path=chatDisplay.GetImagePath(self.tab_id)
                pp(image_path)
                
                assert image_path,chatDisplay
                #print(888, chatDisplay.__class__.__name__)
                #code='print(1223)'
                chat=apc.chats[self.tab_id]
                

                #question=question.replace('\n', ' ')
                system= chat.get('system', 'DESCRIBE_IMAGE')
                prompt=self.evaluate(all_system_templates[chat.workspace].Copilot[system], dict2(image_id=1, input=question))
                pp(prompt)
                payload =[{"role": "user", "content": prompt}] 


                questionHistory[self.tab_id].append(question)
                currentQuestion[self.tab_id]=len(questionHistory[self.tab_id])-1
                currentModel[self.tab_id]=chat.model_id


                

                # DO NOT REMOVE THIS LINE
                chat.temp_val = chat.get('temp_val',"1")
                chat.do_sample = chat.get('do_sample',"False")
                header=fmt([[f'User Question|Hist:{chat.history}|{ self.max_new_tokens_dropdown.GetValue()}|{system}|{chat.temp_val}|{chat.do_sample}']],[])
                pfmtv(chat)
                log(fmtv(chat))
                #e()
                print(header)
                print(question)
                pub.sendMessage('chat_output', message=f'{header}\n{question}\n', tab_id=self.tab_id)
                #pub.sendMessage('chat_output', message=f'{prompt}\n')
                
                #out=rs.stream_response(prompt, chatHistory[self.q_tab_id])  
                for i, fn in enumerate(image_path):
                    if not fn:
                        log(f'Image {i} is not set', color=wx.RED)
                        pub.sendMessage('stop_progress')
                        return
                    log(fn)
                import random  
                pp(image_path)
                if 1:
                    random.shuffle(image_path)
                pp(image_path)

                threading.Thread(target=self.stream_response, args=(prompt, payload, self.tab_id, image_path, chat.history)).start()
        except Exception as e:
            print(format_stacktrace())
            self.log(f'Error: {format_stacktrace()}', color=wx.RED)
            pub.sendMessage('stop_progress')
    def stream_response(self, prompt, payload, tab_id,  image_path, keep_history):
        # Call stream_response and store the result in out
        global chatHistory, questionHistory, currentQuestion,currentModel
        self.receiveing_tab_id=tab_id
        
        print(1111, keep_history)
        chatHistory[self.tab_id] += payload
        if keep_history:
            payload=chatHistory[self.tab_id]

        out = apc.vrs.stream_response(prompt, payload, self.receiveing_tab_id, int(self.max_new_tokens_dropdown.GetValue()) ,image_path)
        if out:
            chatHistory[tab_id].append({"role": "assistant", "content": out}) 
            self.image_id +=1
        pub.sendMessage('stop_progress')
        log('Done.')
        set_status('Done.')        

    def PrevQuestion(self):
        qid=currentQuestion[self.tab_id]
        if qid:
            q=questionHistory[self.tab_id][qid-1]
            self.inputCtrl.SetValue(q)
            self.inputCtrl.SetFocus()
            currentQuestion[self.tab_id]=qid-1
        else:
            self.log('No previous question.', color=wx.RED)
    def NextQuestion(self):
        qid=currentQuestion[self.tab_id]
        if len(questionHistory[self.tab_id])>qid+1:
            q=questionHistory[self.tab_id][qid+1]
            self.inputCtrl.SetValue(q)
            self.inputCtrl.SetFocus()
            currentQuestion[self.tab_id]=qid+1
        else:
            self.log('No next question.', color=wx.RED)
    def OnCharHook(self, event):
        if event.ControlDown() and  event.GetKeyCode() == wx.WXK_RETURN:
            self.AskQuestion()
        elif event.ControlDown() and event.GetKeyCode() == wx.WXK_RIGHT:
            log("Ctrl+-> pressed")
            set_status("Ctrl+-> pressed")
            self.NextQuestion()
        elif event.ControlDown() and event.GetKeyCode() == wx.WXK_LEFT:
            self.log("Ctrl+<- pressed")
            set_status("Ctrl+<- pressed")
            self.PrevQuestion()
                       
        else:
            event.Skip()


    def log(self, message, color=wx.BLUE):
        
        pub.sendMessage('log', message=f'{message}', color=color)

class VisionResponseStreamer:
    def __init__(self, model_id):
        # Set your OpenAI API key here
        from transformers import AutoModelForCausalLM 
        from transformers import AutoProcessor 

        # Initialize the client
        self.model = AutoModelForCausalLM.from_pretrained(model_id, device_map="cuda", trust_remote_code=True, torch_dtype="auto", _attn_implementation='flash_attention_2') # use _attn_implementation='eager' to disable flash attention

        self.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True) 

    def stream_response(self, prompt, chatHistory, receiveing_tab_id, max_new_tokens, image_path):
        # Create a chat completion request with streaming enabled
        #pp(chatHistory)
        from PIL import Image 
        import requests 

        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]

        #model_id = chat.model_id
    
        model, processor = self.model, self.processor
        print(fmt([[f'Prompt']], []) )
        pp(chatHistory)
        
    
        

        #prompt = processor.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        #chat history
        prompt = processor.tokenizer.apply_chat_template(chatHistory, tokenize=False, add_generation_prompt=True)
        
        out = []
        try:
            images=[]   
            for fn in image_path:
                if not fn:
                    log(f'No image file not set', 'red')
                    return ''
                assert isfile(fn)
                images.append( Image.open(fn))
            print(fmt([[f'Images']], []) )
            pp(images)
            inputs = processor(prompt, images, return_tensors="pt").to("cuda:0") 

            generation_args = { 
                "max_new_tokens": max_new_tokens , 
                "temperature": float(chat.temp_val), 
                "do_sample": True if chat.do_sample =="True" else False, 
            } 

            generate_ids = model.generate(**inputs, eos_token_id=processor.tokenizer.eos_token_id, **generation_args) 

            # remove input tokens 
            generate_ids = generate_ids[:, inputs['input_ids'].shape[1]:]
            response = processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0] 
            stop_output=apc.stop_output[receiveing_tab_id]
            pause_output=apc.pause_output[receiveing_tab_id]

            
            
            out.append(response)
           
            header=fmt([[f'System Answer']],[])
            
            print(header)
            print(response)
            #print(content, receiveing_tab_id)
            pub.sendMessage('chat_output', message=f'{header}\nFiles: {len(image_path)}\n\n{response}', tab_id=receiveing_tab_id)
            
        except Exception as e:
            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')
            return ''
        if 0:

            self.client = openai.OpenAI()
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=chatHistory,
                    stream=True,
		    max_tokens=4096 
                )
            except Exception as e:
                log(f'Error in stream_response', 'red')
                log(str(e), 'red')
                return ''
            
            # Print each response chunk as it arrives
            #pp(apc.stop_output)
            stop_output=apc.stop_output[receiveing_tab_id]
            pause_output=apc.pause_output[receiveing_tab_id]
            for chunk in response:
                if stop_output[0] or pause_output[0] :
                    
                    if stop_output[0] :
                        #print('\n-->Stopped\n')
                        pub.sendMessage("stopped")
                        break
                        #pub.sendMessage("append_text", text='\n-->Stopped\n')
                    else:
                        while pause_output[0] :
                            time.sleep(0.1)
                            if stop_output[0]:
                                #print('\n-->Stopped\n')
                                pub.sendMessage("stopped")
                                break
                                #pub.sendMessage("append_text", text='\n-->Stopped\n')
                                                
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    #print(content, end='', flush=True)
                    #pp(content)
                    if content:
                        out.append(content)
                        #print(content, receiveing_tab_id)
                        pub.sendMessage('chat_output', message=f'{content}', tab_id=receiveing_tab_id)

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)
