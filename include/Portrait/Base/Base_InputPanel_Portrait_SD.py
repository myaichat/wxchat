import wx
import sys, traceback
from pubsub import pub
from include.fmt import fmt
from pprint import pprint as pp 
import include.config.init_config as init_config 
apc = init_config.apc
import wx.html
from include.Common import HtmlDialog, Base_InputPanel, ChatHistoryDialog, dict2, evaluate



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



class Base_InputPanel_Portrait_SD(Base_InputPanel):
    def AddButtons_Level_1(self, h_sizer):
        if 1: #second row



            #h_sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
            chat=apc.chats[self.tab_id] 


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






    def split_text_into_chunks(self, text, chunk_length=80):
        # Split the text into chunks of specified length
        chunks = [text[i:i+chunk_length] for i in range(0, len(text), chunk_length)]
        return chunks


    def AddButtons_Level_2(self, v_sizer):
        if 1: #second row



            h_sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
            chat=apc.chats[self.tab_id] 

        if 1:  
            img_source_vals = ["Alex", "Olga", "Greta"]
            # Create a ComboBox for max_new_tokens
            self.img_source_dropdown = wx.ComboBox(self, choices=img_source_vals, style=wx.CB_READONLY)
            self.img_source_dropdown.SetValue("Olga")  # Default value
            chat.img_source =  self.img_source_dropdown.GetValue()
            self.img_source_dropdown.Bind(wx.EVT_COMBOBOX, self.OnImgSourceChange)

            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="image source")
            dos.html_content ="""

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>image source</title>
</head>
<body>
    
    <pre>
directory with images
    </pre>

</body>
</html>

"""   

            # Modify the event binding to use a lambda function
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.img_source_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)

        if 1:  
            default=f'512x{int(512*1.5)}'
            img_size_vals = ['512x512',default, f'{int(512*1.5)}x512', '1024x1024', f'1024x{int(1024*1.5)}', f'{int(1024*1.5)}x1024']
            # Create a ComboBox for max_new_tokens
            self.img_size_dropdown = wx.ComboBox(self, choices=img_size_vals, style=wx.CB_READONLY)
            self.img_size_dropdown.SetValue(default)  # Default value
            chat.img_size =  [int(x) for x in self.img_size_dropdown.GetValue().split('x')]
            self.img_size_dropdown.Bind(wx.EVT_COMBOBOX, self.OnImgSizeChange)

            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="image size")
            dos.html_content ="""

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>image size</title>
</head>
<body>
    
    <pre>
image size
    </pre>

</body>
</html>

"""   

            # Modify the event binding to use a lambda function
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.img_size_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)

            
            v_sizer.Add(h_sizer_1, 0, wx.ALIGN_CENTER) 

    def OnImgSizeChange(self, event):

        # This method will be called when the selection changes
        selected_value = self.img_size_dropdown.GetValue()
        print(f"Selected img_size: {selected_value}")
        chat = apc.chats[self.tab_id]
        chat.img_size = [ int(x) for x in selected_value.split('x')]
        #pub.sendMessage('reset_image_pool', tab_id=self.tab_id)      

    def OnClickDos(self, event):
        # Define your HTML content here. It could also be loaded from a file or a webpage.
        html_content = event.GetEventObject().html_content
        dialog = HtmlDialog(self, "HTML Content", html_content)
        dialog.ShowModal()
        dialog.Destroy()

    def onHover(self, event):
        # Fetch the webpage content. For demonstration, we're just using static HTML.
        html_content ="""<html><body><h3>top_p</h3><p>top_p is a parameter used in text generation that controls the nucleus sampling method, also known as top-p sampling. 
This sampling strategy is designed to focus the model's attention on the most probable next words or tokens, 
enhancing the quality and coherence of the generated text.
</p></body></html>"""
        # In a real application, you might fetch the content like so:
        # response = requests.get("http://example.com")
        # html_content = response.text
        self.tooltip = HtmlToolTip(None, html_content)  # Use self.tooltip to store the window
        pos = wx.GetMousePosition()
        self.tooltip.SetPosition(pos)
        self.tooltip.Show()
    def onLeave(self, event):
        # Destroy the tooltip window when the mouse leaves the widget
        if self.tooltip:
            self.tooltip.Destroy()
            self.tooltip = None  # Reset the tooltip attribute to None
    def OnDoSampleChange(self, event):
        # Get the selected do_sample value
        selected_do_sample = self.do_sample_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.do_sample = (selected_do_sample == 'True')
        print('OnDoSampleChange',selected_do_sample, self.tab_id)
        # Continue processing the event
        event.Skip()
    def OnMaxLengthChange(self, event):
        # Get the selected do_sample value
        selected_max_length = self.max_length_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.max_length = int(selected_max_length )
        print('OnMaxLengthChange',selected_max_length, self.tab_id)
        # Continue processing the event
        event.Skip()
    def OnMinLengthChange(self, event):
        # Get the selected do_sample value
        selected_min_length = self.min_length_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.min_length = int(selected_min_length )

        # Continue processing the event
        event.Skip()     
    def OnTopPChange(self, event):
        # Get the selected do_sample value
        selected_top_p = self.top_p_dropdown.GetValue()
        print('OnTopPChange',selected_top_p, self.tab_id)
        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.top_p = float(selected_top_p )

        # Continue processing the event
        pp(chat)
        print(apc.chats)
        event.Skip()        
    def OnTopKChange(self, event):
        # Get the selected do_sample value
        selected_top_k = self.top_k_dropdown.GetValue()
        print('OnTopKChange',selected_top_k, self.tab_id)
        # Print the selected model
        chat = apc.chats[self.tab_id]
        
        chat.top_k = int(selected_top_k )

        # Continue processing the event
        event.Skip()

    def OnTempChange(self, event):
        # Get the selected do_sample value
        selected_temp = self.temp_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.temperature = float(selected_temp )


        # Continue processing the event
        event.Skip()    
    def OnRepetitionPenaltyChange(self, event):
        # Get the selected do_sample value
        selected_repetition_penalty = self.length_penalty_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.length_penalty = float(selected_repetition_penalty )

        # Continue processing the event
        event.Skip()

    def OnLengthPenaltyChange(self, event):
        # Get the selected do_sample value
        selected_length_penalty = self.repetition_penalty_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.length_penalty = float(selected_length_penalty )

        # Continue processing the event
        event.Skip()
    def Base_OnAskQuestion(self):
        self.pause_panel.pause_output(False)
        self.pause_panel.stop_output(False)   
    def evaluate(self,ss, params):
        #a = f"{ss}"
        a=eval('f"""'+ss+'"""')
        return a   



    def RestoreQuestionForTabId(self, tab_id):
        self.tab_id=tab_id
        message=tab_id
        chat=apc.chats[message]

        if message in self.tabs:
            assert self.chat_type==message[1]
            #print('Chat restoring', message)
            #pp(self.tabs[message])
            self.inputCtrl.SetValue(self.tabs[message]['q'])
            
            self.model_dropdown.SetValue(chat.model)
            #chat.model = self.model_dropdown.GetValue()
            #self.tab_id=message
            #self.q_tab_id=message
            #self.inputCtrl.SetSelection(0, -1)
            self.inputCtrl.SetFocus()
            
            #print(message, self.tab_id)
            #pp(self.tabs)
            if 0:
                if chat.get('img_source', None):
                    self.img_source_dropdown.SetValue(chat.img_source) 
                else:
                    chat.img_source = self.img_source_dropdown.GetValue()  
            else:
                chat.img_source = self.img_source_dropdown.GetValue()  


            if 0:
                if chat.get('img_size', None):
                    self.iimg_size_dropdown.SetValue(chat.img_size) 
                else:
                    chat.img_size = self.img_size_dropdown.GetValue()  
            else:
                chat.img_size = [int(x) for x in self.img_size_dropdown.GetValue().split('x')]