import wx
import wx.stc as stc
import wx.lib.agw.aui as aui
from include.Common_Panel import StyledTextDisplay
from pubsub import pub
from pprint import pprint as pp 
from include.Common import *
import time, random
from datetime import datetime
e=sys.exit
import include.config.init_config as init_config 
apc = init_config.apc

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


class MyNotebookPromptPanel(wx.Panel):
    subscribed=False
    def __init__(self, parent, tab_id):
        super(MyNotebookPromptPanel, self).__init__(parent)
        
        notebook = aui.AuiNotebook(self)
        self.tab_id=tab_id
        self.notebook = notebook
        self.promptCtrl=[]
        chat = apc.chats[tab_id]
        promptCtrl=PromptCtrl(notebook, chat)
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
        self.notebook_panel=notebook_panel = MyNotebookPromptPanel(self.copilot_splitter, tab_id)
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
        
    def GetPromptPath(self, tab_id):
        assert tab_id==self.tab_id, self.__class__.__name__
        
        out=[]
        notebook= self.notebook_panel.notebook
       
        page_count = notebook.GetPageCount()

        for page_index in range(page_count):
            # Get the panel (page) at the current index
            page = notebook.GetPage(page_index)
            
            out.append(page.prompt_path)
        return out
    
    def OnResize(self, event):
        # Adjust the sash position to keep the vertical splitter size constant
        width, height = self.GetSize()
        self.copilot_splitter.SetSashPosition(width // 2)
        event.Skip() 