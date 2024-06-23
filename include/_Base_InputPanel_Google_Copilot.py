import wx
import sys, traceback
from pubsub import pub
from include.fmt import fmt
from pprint import pprint as pp 
import include.config.init_config as init_config 
apc = init_config.apc
import wx.html
from include.Common import Base_InputPanel, ChatHistoryDialog, dict2, evaluate



class ShowSystemPrompts_Chat(wx.Dialog):
    def __init__(self, parent, tab_id, chat_history):
        super(ShowSystemPrompts_Chat, self).__init__(parent, title="Chat System Prompts", size=(600, 400))
        self.tab_id = tab_id
        self.chat_history = chat_history
        
        # Create the ListCtrl
        self.listCtrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        
        # Add columns
        self.listCtrl.InsertColumn(0, 'Name', width=100)
        self.listCtrl.InsertColumn(1, 'Content', width=450)
        
        # Populate the ListCtrl with chat history
        self.populate_list_ctrl()
        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(580, 100))  # Adjust size and style as needed
        
        # Create a close button
        useButton = wx.Button(self, label="Use Prompt")
        useButton.Bind(wx.EVT_BUTTON, self.on_use)        
        closeButton = wx.Button(self, label="Close")
        closeButton.Bind(wx.EVT_BUTTON, self.on_close)
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.listCtrl, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self.inputCtrl, 0, wx.EXPAND | wx.ALL, 10) 
        
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.AddStretchSpacer(1)
        h_sizer.Add(useButton, 0, wx.ALL, 10)
        h_sizer.Add(closeButton, 0,  wx.ALL, 10)
        sizer.Add(h_sizer, 0, wx.EXPAND | wx.ALL, 10) 

        self.SetSizer(sizer)
        # Bind the event for row selection
        self.listCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_row_click)
        
        # Bind the event for double click or Enter key
        self.listCtrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_row_activated)        

    def on_row_click(self, event):
        # Get the selected row index
        selected_index = event.Index
        
        # Get the content of the selected row
        role = self.listCtrl.GetItemText(selected_index, col=0)
        content = self.listCtrl.GetItemText(selected_index, col=1)
        self.inputCtrl.SetValue(content)
        # Process the row click
        # For example, show the content in a message dialog
        #wx.MessageBox(f"Role: {role}\nContent: {content}", "Row Clicked")

    def on_row_activated(self, event):
        # This method will be called when a row is double-clicked or Enter key is pressed on a row
        self.on_row_click(event)
        
    def populate_list_ctrl(self):
        chat= apc.chats[self.tab_id]

        for name, content in apc.all_system_templates[chat.workspace].Chat.items():
            
            index = self.listCtrl.InsertItem(self.listCtrl.GetItemCount(), name)
            prompt=evaluate(content, dict2(question=chat.question))
            self.listCtrl.SetItem(index, 1, prompt) 

           

    def on_use(self, event):
        chat=apc.chats[self.tab_id]
        #print(self.inputCtrl.GetValue())
        chat.system_prompt=self.inputCtrl.GetValue()
        pub.sendMessage('set_system_prompt', message=chat.system_prompt, tab_id=self.tab_id)
        self.Close() 
    def on_close(self, event):
        self.Close()         



class Base_InputPanel_Google_Copilot(Base_InputPanel):
    def AddButtons(self, h_sizer):
        if 1: #second row



            #h_sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
            chat=apc.chats[self.tab_id] 
            self.max_tokens_dropdown = wx.ComboBox(self, choices=['100', '150','300','450', '600', '750', '1000', '2000', '3000'], style=wx.CB_READONLY)
            self.max_tokens_dropdown.SetValue('300')  # Default value
            self.max_tokens_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMinTokensChange)
            chat.max_tokens = int(self.max_tokens_dropdown.GetValue())
            h_sizer.Add(self.max_tokens_dropdown, 0, wx.ALIGN_CENTER) 

            self.historyButton = wx.Button(self, label='Hist', size=(40, 25))
            self.historyButton.Bind(wx.EVT_BUTTON, self.onHistoryButton)
            h_sizer.Add(self.historyButton, 0, wx.ALIGN_CENTER) 
            self.sysButton = wx.Button(self, label='Sys', size=(40, 25))
            self.sysButton.Bind(wx.EVT_BUTTON, self.onSysButton)
            h_sizer.Add(self.sysButton, 0, wx.ALIGN_CENTER) 

            if 0:
                self.min_tokens_dropdown = wx.ComboBox(self, choices=['1','256', '512', '768','1024','1536', '2048'], style=wx.CB_READONLY)
                self.min_tokens_dropdown.SetValue('1')  # Default value
                self.min_tokens_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMaxTokensChange)
                chat.min_tokens = int(self.min_tokens_dropdown.GetValue())
                h_sizer.Add(self.min_tokens_dropdown, 0, wx.ALIGN_CENTER) 
    def onHistoryButton(self, event):
        
        dialog = ChatHistoryDialog(self, self.tab_id, apc.chatHistory)
        dialog.ShowModal()
        dialog.Destroy()

    def onSysButton(self, event):
        
        dialog = ShowSystemPrompts_Chat(self, self.tab_id, apc.chatHistory)
        dialog.ShowModal()
        dialog.Destroy() 

            #v_sizer.Add(h_sizer_1, 0, wx.ALIGN_CENTER) 
    def OnMaxTokensChange(self, event):
        # Get the selected do_sample value
        selected_value = self.max_tokens_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.max_tokens = selected_value
        print('OnMaxTokensChange',selected_value, self.tab_id)
        # Continue processing the event
        event.Skip()  
    def OnMinTokensChange(self, event):
        # Get the selected do_sample value
        selected_value = self.min_tokens_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.min_tokens = selected_value
        print('OnMinTokensChange',selected_value, self.tab_id)
        # Continue processing the event
        event.Skip()
    

    def RestoreQuestionForTabId(self, tab_id):
        self.tab_id=tab_id
        message=tab_id
        chat=apc.chats[message]

        if message in self.tabs:
            assert self.chat_type==message[1]
            #print('Chat restoring', message)
            #pp(self.tabs[message])
            self.inputCtrl.SetValue(self.tabs[message]['q'])
            
            self.model_dropdown.SetValue(apc.currentModel[message])
            chat.model = self.model_dropdown.GetValue()
            #self.tab_id=message
            #self.q_tab_id=message
            #self.inputCtrl.SetSelection(0, -1)
            self.inputCtrl.SetFocus()
            
            print(message, self.tab_id)
            #pp(self.tabs)
        
            if chat.get('max_tokens', None):
                self.max_tokens_dropdown.SetValue(str(chat.max_tokens)) 
            else:
                chat.max_tokens = int(self.max_tokens_dropdown.GetValue())  

            if 0:
                if chat.get('min_tokens', None):
                    self.min_tokens_dropdown.SetValue(str(chat.min_tokens))
                else:
                    chat.min_tokens = int(self.min_tokens_dropdown.GetValue())
    def split_text_into_chunks(self, text, chunk_length=80):
        # Split the text into chunks of specified length
        chunks = [text[i:i+chunk_length] for i in range(0, len(text), chunk_length)]
        return chunks

