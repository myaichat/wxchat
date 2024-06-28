import wx
import sys, traceback
from pubsub import pub
from include.fmt import fmt
from pprint import pprint as pp 
import include.config.init_config as init_config 
apc = init_config.apc
import wx.html
from include.Common import Base_InputPanel, HtmlDialog
class Base_InputPanel_Gpt4(Base_InputPanel):
    def AddButtons(self, h_sizer):
        if 1: #second row



            #h_sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
            chat=apc.chats[self.tab_id] 
            self.max_tokens_dropdown = wx.ComboBox(self, choices=['100', '150','300','450', '600', '750', '1000', '2000', '3000'], style=wx.CB_READONLY)
            self.max_tokens_dropdown.SetValue('300')  # Default value
            self.max_tokens_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMinTokensChange)
            chat.max_tokens = int(self.max_tokens_dropdown.GetValue())
            h_sizer.Add(self.max_tokens_dropdown, 0, wx.ALIGN_CENTER) 
            if 0:
                self.min_tokens_dropdown = wx.ComboBox(self, choices=['1','256', '512', '768','1024','1536', '2048'], style=wx.CB_READONLY)
                self.min_tokens_dropdown.SetValue('1')  # Default value
                self.min_tokens_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMaxTokensChange)
                chat.min_tokens = int(self.min_tokens_dropdown.GetValue())
                h_sizer.Add(self.min_tokens_dropdown, 0, wx.ALIGN_CENTER) 
           
            
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
