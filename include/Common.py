import wx
import sys, traceback
from pubsub import pub
from include.fmt import fmt
from pprint import pprint as pp 
import include.config.init_config as init_config 
apc = init_config.apc
import wx.html



def split_text_into_chunks( text, chunk_length=80):
    # Split the text into chunks of specified length
    chunks = [text[i:i+chunk_length] for i in range(0, len(text), chunk_length)]
    return chunks


def evaluate(ss, params):
    #a = f"{ss}"
    a=eval('f"""'+ss+'"""')
    return a 

class dict2(dict):                                                              
    def __setitem__(self, key, value):
        super(dict2, self).__setitem__(key, value)
        #print(f"Set {key} to {value}")
    def __init__(self, *args, **kwargs):                                               
        super(dict2, self).__init__(*args,  **kwargs)                                     

    def __setattr__(self, key, value):                                          
        self[key] = value                                                       

    def __dir__(self):                                                          
        return self.keys()                                                      

    def __getattr__(self, key):                                                 
        try:                                                                    
            return self[key]                                                    
        except KeyError:                                                        
            raise AttributeError(key)                                           

    def __setstate__(self, state):                                              
        pass 

def d2d2(d):
    out=dict2()
    for k, v in d.items():
        if type(v) in [dict]:
            out[k]= d2d2(v)
        else:
            out[k]=v
    return out

class AttrDict(object):
    def __init__(self, adict):
        self.__dict__.update(adict)

def log(message, color=None):
    pub.sendMessage('log', message=message, color=color)
def set_status(message):
    pub.sendMessage('set_status', message=message)
def format_stacktrace():
    parts = ["Traceback (most recent call last):\n"]
    parts.extend(traceback.format_stack(limit=25))
    parts.extend(traceback.format_exception(*sys.exc_info())[1:])
    return "".join(parts)

class NewChat(object):
    def __init__(self):
        if 1:
            accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('N'), wx.ID_NEW)])

            # Set the accelerator table for chatInput
            self.SetAcceleratorTable(accel_tbl)

            # Bind the event to the handler
            self.Bind(wx.EVT_MENU, self.OnNewChat, id=wx.ID_NEW)
        #pub.subscribe(self.OnDefaultChat, 'adddefault_chat')
    def OnNewChat(self, event):
        dialog = NewChatDialog(self, title="New Chat")
        if dialog.ShowModal() == wx.ID_OK:
            vendor=dialog.vendor.GetStringSelection()
            chat_type_str = dialog.chat_type.GetStringSelection()
            chat_type =chat_type_str
            name = dialog.name.GetValue()
            system = dialog.system.GetValue()
            chatName = name
            chat=AttrDict(dict(vendor=vendor, chat_type=chat_type, name=name, system=system))
            #pp(chat.__dict__)
            
            print(fmt([[f"New chat: {name}"]], ['New Chat']))
            pub.sendMessage('log', message=f'New chat name: {name}')
            pub.sendMessage('add_chat', chat=chat)
        dialog.Destroy()        
class GetClassName:
    def __init__(self):
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClick)
    def OnRightClick(self, event):
        # Create a popup menu
        menu = wx.Menu()
        
        # Add a menu item to the popup menu
        current_class_name=self.__class__.__name__
        item = menu.Append(wx.ID_ANY, current_class_name)

        pname=self.GetParent().__class__.__name__
        parent_item = menu.Append(wx.ID_ANY, pname)
        
        # Bind the menu item to an event handler
        self.Bind(wx.EVT_MENU, lambda event, name=current_class_name: self.OnCopyName(event, name), item)
        self.Bind(wx.EVT_MENU, lambda event, name=pname: self.OnCopyName(event, name), parent_item)

        
        # Show the popup menu
        self.PopupMenu(menu)
        
        # Destroy the menu after it's used
        menu.Destroy()

    def OnCopyName(self, event, name):
        # Create a data object for the clipboard
        data_object = wx.TextDataObject()

        # Set the class name into the data object
        
        data_object.SetText(name)

        # Copy the text to the clipboard
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(data_object)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox('Unable to open the clipboard', 'Error', wx.OK | wx.ICON_ERROR)

class Scroll_Handlet:
    def __init__(self):
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll)

        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scrolled=False
        self.previous_scroll_pos=self.GetScrollPos(wx.VERTICAL)        
        #self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        pub.subscribe(self.OnScroll, 'scroll_output')
    def OnScroll(self, message):
        self.scrolled=True
    def on_scroll(self, event):
        current_scroll_pos = self.GetScrollPos(wx.VERTICAL)

        # If the current scroll position is greater than the previous scroll position,
        # you've scrolled down
        if current_scroll_pos > self.previous_scroll_pos:
            self.scrolled = True
        # If the current scroll position is less than the previous scroll position,
        # you've scrolled up
        elif current_scroll_pos < self.previous_scroll_pos:
            self.scrolled = False

        # Update the previous scroll position
        self.previous_scroll_pos = current_scroll_pos
        event.Skip()

    def on_key_down(self, event):
        if event.GetKeyCode() in [ wx.WXK_PAGEDOWN]:
            self.scrolled = True
        if event.GetKeyCode() in [wx.WXK_PAGEUP]:
            self.scrolled = False    
        if event.ControlDown() and event.GetKeyCode() == ord('P'):
            if self.pause_output:
                self.resume_answer(self.pause_button)
            else:
                self.pause_output = True
                #print('Paused')    
                self.statusbar.SetStatusText('Paused')            
        event.Skip()    
class PauseHandlet:
    def __init__(self,tab_id):
        self.tab_id=tab_id

        #print('-------------setting PauseHandlet', self.tab_id)
        apc.pause_output[self.tab_id]=[False]
        apc.stop_output[self.tab_id]=[False]
        pub.subscribe(self.SetPause, 'pause_output')
        pub.subscribe(self.SetStop, 'stop_output')
    def pause_output(self,on_off=None):
        if on_off is not None:
            apc.pause_output[self.tab_id][0]=on_off
        else:
            return apc.pause_output[self.tab_id][0]

    def stop_output(self,on_off=None):
        if on_off is not None:
            apc.stop_output[self.tab_id][0]=on_off
            if on_off:
                self.stop_button.Disable()
            else:
                self.stop_button.Enable()
                self.pause_button.Enable()
        else:
            return apc.stop_output[self.tab_id][0]
    
    def on_pause(self, event):
        print('\nPause\n')
        if not self.stop_output():
            self.pause_output(not self.pause_output())

            if  self.pause_output():
                #self.statusBar.SetStatusText('Paused')
                pub.sendMessage('set_status', message='Paused')
                event.GetEventObject().SetLabel('Resume')
            else:
                #self.statusBar.SetStatusText('Resumed')
                pub.sendMessage('set_status', message='Resumed')
                event.GetEventObject().SetLabel('Pause')
                #self.resume_answer(event.GetEventObject())  
    def on_stop(self, event):
        print('\nStop\n')
        #self.stop_output(not self.stop_output())
        self.stop_output(True)
        if  1: #self.stop_output():
            #self.statusBar.SetStatusText('Stopped')
            pub.sendMessage('set_status', message='Stopped')
            #event.GetEventObject().SetLabel('Start')
            self.pause_button.Disable()
            self.stop_button.Disable()
        if 0:
            #self.statusBar.SetStatusText('Started')

            pub.sendMessage('set_status', message='Started')
            event.GetEventObject().SetLabel('Stop')
            self.pause_button.Enable()
            self.pause_button.SetLabel('Pause')
    def SetPause(self, message):
        self.pause_output = message
    def SetStop(self, message):
        self.stop_output = message

class PausePanel(wx.Panel,PauseHandlet):
    def __init__(self, parent, tab_id):
        super(PausePanel, self).__init__(parent)
        PauseHandlet.__init__(self, tab_id)
        self.pause_button = wx.Button(self, label="Pause", size=(40, -1))
        self.stop_button = wx.Button(self, label="Stop", size=(40, -1))
        self.pause_button.Bind(wx.EVT_BUTTON, self.on_pause)
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.pause_button, 0, wx.ALL)
        sizer.Add(self.stop_button, 0, wx.ALL)
        self.SetSizer(sizer)
        self.stop_button.Disable()
        self.pause_button.Disable()
        
class HtmlToolTip(wx.Frame):
    def __init__(self, parent, html_content):
        super(HtmlToolTip, self).__init__(parent, style=wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP | wx.FRAME_TOOL_WINDOW)
        html_window = wx.html.HtmlWindow(self)
        html_window.SetPage(html_content)
        self.SetSize((300, 200))  # Adjust size as needed
        self.Layout()

class HtmlDialog(wx.Dialog):
    def __init__(self, parent, title, html_content):
        super(HtmlDialog, self).__init__(parent, title=title, size=(600, 800))
        self.html_window = wx.html.HtmlWindow(self)
        self.html_window.SetPage(html_content)
        self.initializeUI()
        self.Centre(wx.BOTH)  # Center the dialog on its parent

    def initializeUI(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.html_window, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)
        self.Layout()
class Base_InputPanel:
    def Base_OnAskQuestion(self):
        self.pause_panel.pause_output(False)
        self.pause_panel.stop_output(False)   

    def RestoreQuestionForTabId(self, tab_id):
        self.tab_id=tab_id
        message=tab_id
        chat=apc.chats[message]
        #pp(chat)
        #print('RestoreQuestionForTabId', chat)
        if message in self.tabs:
            assert self.chat_type==message[1]

            self.inputCtrl.SetValue(self.tabs[message]['q'])
            self.model_dropdown.SetValue(apc.currentModel[message])
            chat.model = self.model_dropdown.GetValue()
            self.inputCtrl.SetFocus()
   
        else:   
            print('not in self.tabs', message)


class ShowSystemPrompts(wx.Dialog):
    def __init__(self, parent, tab_id, chat_history):
        super(ShowSystemPrompts, self).__init__(parent, title="Chat History", size=(600, 400))
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

        for name, content in apc.all_system_templates[chat.workspace].Copilot.items():
            
            index = self.listCtrl.InsertItem(self.listCtrl.GetItemCount(), name)
            prompt=evaluate(content, dict2( input=chat.question, num_of_images=chat.num_of_images))
            self.listCtrl.SetItem(index, 1, prompt) 

        for name, content in apc.all_system_templates[chat.workspace].Copilot.items():
            
            index = self.listCtrl.InsertItem(self.listCtrl.GetItemCount(), name)
            prompt=evaluate(content, dict2( input=chat.question, num_of_images=chat.num_of_images))
            self.listCtrl.SetItem(index, 1, prompt)            

    def on_use(self, event):
        chat=apc.chats[self.tab_id]
        #print(self.inputCtrl.GetValue())
        chat.system_prompt=self.inputCtrl.GetValue()
        pub.sendMessage('set_system_prompt', message=chat.system_prompt, tab_id=self.tab_id)
        self.Close() 
    def on_close(self, event):
        self.Close()  

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

class Base_InputPanel:
    def AddButtons(self, v_sizer):
        if 1: #second row



            h_sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
            chat=apc.chats[self.tab_id] 
            self.do_sample_dropdown = wx.ComboBox(self, choices=['True', 'False'], style=wx.CB_READONLY)
            self.do_sample_dropdown.SetValue('False')  # Default value
            self.do_sample_dropdown.Bind(wx.EVT_COMBOBOX, self.OnDoSampleChange)
            chat.do_sample = (self.do_sample_dropdown.GetValue() == 'True')
        
            self.max_length_dropdown = wx.ComboBox(self, choices=['512', '768','1024','1536', '2048', '4096', str(1024* 10), str(1024* 20), str(1024* 40)], style=wx.CB_READONLY)
            self.max_length_dropdown.SetValue('2048')  # Default value
            self.max_length_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMaxLengthChange)
            chat.max_length = int(self.max_length_dropdown.GetValue())

            self.min_length_dropdown = wx.ComboBox(self, choices=['1', '512', '1024', '2048', '4096'], style=wx.CB_READONLY)
            self.min_length_dropdown.SetValue('1')  # Default value
            self.min_length_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMinLengthChange)
            chat.min_length = int(self.min_length_dropdown.GetValue()  )

            self.top_p_dropdown = wx.ComboBox(self, choices=['0.0',  '0.1',  '0.2',  '0.3',  '0.4',  '0.5',  '0.6',  '0.7',  '0.8',  '0.9',  '1.0',  '1.1',], style=wx.CB_READONLY)
            self.top_p_dropdown.SetValue('0.9')  # Default value
            self.top_p_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTopPChange)
            chat.top_p = float(self.top_p_dropdown.GetValue()  )
            #top_k
            self.top_k_dropdown = wx.ComboBox(self, choices=['1',  '2',  '3',  '4',  '5',  '10',  '20',  '50',  '75',  '100',  '150', '200','300',], style=wx.CB_READONLY)
            self.top_k_dropdown.SetValue('50')  # Default value
            self.top_k_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTopKChange)
            chat.top_k = int(self.top_k_dropdown.GetValue()  )     

            self.temp_dropdown = wx.ComboBox(self, choices=['0.0',  '0.1',  '0.2',  '0.3',  '0.4',  '0.5',  '0.6',  '0.7',  '0.8',  '0.9',  '1.0', '1.2', '1.4', '1.7',  '2.0', '5.0', '10.0', '50.0'], style=wx.CB_READONLY)
            self.temp_dropdown.SetValue('1.2')  # Default value
            self.temp_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTempChange)
            chat.temperature = float(self.temp_dropdown.GetValue()  )  
            #repetition_penalty
            self.repetition_penalty_dropdown = wx.ComboBox(self, choices=['1.0',  '1.1',  '1.2',  '1.3',  '1.4',  '1.5',  '1.6',  '1.7',  '1.8',  '1.9',  '2.0',  '2.1','2.5','3.0','5.0','10.0',], style=wx.CB_READONLY)
            self.repetition_penalty_dropdown.SetValue('1.1')  # Default value
            self.repetition_penalty_dropdown.Bind(wx.EVT_COMBOBOX, self.OnRepetitionPenaltyChange)
            chat.repetition_penalty = float(self.repetition_penalty_dropdown.GetValue()  )             

            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="do_sample")
            dos.html_content="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Increasing Artfulness with do_sample=True</title>
</head>
<body>
    <h1>Increasing Artfulness with do_sample=True</h1>
    
    <p>When <code>do_sample=true</code>, the model uses stochastic decoding methods such as sampling with temperature, top-p, or top-k sampling. Here are several strategies to increase the artfulness of the output:</p>
    
    <h2>Strategies:</h2>
    
    <h3>1. Adjust Temperature:</h3>
    <ul>
        <li><strong>Description:</strong> Increasing the temperature value increases the randomness of the predictions, leading to more creative and diverse outputs.</li>
        <li><strong>Example:</strong> Set <code>temperature=1.2</code> for more creativity.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "temperature": 1.2
}
    </pre>

    <h3>2. Adjust Top-p (Nucleus Sampling):</h3>
    <ul>
        <li><strong>Description:</strong> Top-p sampling considers the smallest set of tokens whose cumulative probability exceeds the threshold p. Lowering top-p can make the output more focused, while increasing it can make it more diverse.</li>
        <li><strong>Example:</strong> Set <code>top_p=0.9</code> to balance creativity and coherence.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "top_p": 0.9
}
    </pre>

    <h3>3. Adjust Top-k:</h3>
    <ul>
        <li><strong>Description:</strong> Top-k sampling considers only the top k tokens. Increasing the value of k allows the model to consider a broader range of tokens, increasing diversity.</li>
        <li><strong>Example:</strong> Set <code>top_k=100</code> for more diverse outputs.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "top_k": 100
}
    </pre>

    <h3>4. Combine Strategies:</h3>
    <ul>
        <li><strong>Description:</strong> Combining temperature, top-p, and top-k adjustments can amplify their effects, leading to even more artful and creative outputs.</li>
        <li><strong>Example:</strong> Use a combination of these parameters for maximum creativity.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "temperature": 1.2,
  "top_p": 0.9,
  "top_k": 100
}
    </pre>

    <h3>5. Apply Repetition Penalty:</h3>
    <ul>
        <li><strong>Description:</strong> Using a repetition penalty discourages the model from repeating the same phrases or words, promoting more varied and interesting outputs.</li>
        <li><strong>Example:</strong> Set <code>repetition_penalty=1.2</code>.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "repetition_penalty": 1.2
}
    </pre>

    <h3>6. Adjust Length Penalty:</h3>
    <ul>
        <li><strong>Description:</strong> Tuning the length penalty can influence the length of the output, which can indirectly affect its creativity. A lower length penalty encourages longer outputs, while a higher penalty favors shorter ones.</li>
        <li><strong>Example:</strong> Set <code>length_penalty=0.8</code> for longer, potentially more creative outputs.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "length_penalty": 0.8
}
    </pre>

    <h2>Example Configuration Combining Multiple Strategies:</h2>
    <pre>
{
  "do_sample": true,
  "temperature": 1.2,
  "top_p": 0.9,
  "top_k": 100,
  "repetition_penalty": 1.2,
  "length_penalty": 0.8
}
    </pre>
    
</body>
</html>

"""        
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.do_sample_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)

            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="max_len")
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.max_length_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)


            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="min_len")
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.min_length_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)
                   
            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="top_k")
            dos.html_content ="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Top-k Ranges Explained</title>
</head>
<body>
    <h1>Top-k Ranges Explained</h1>
    
    <h2>Top-k Range Effects:</h2>
    
    <h3>Low Top-k (1 to 50):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model considers only a small number of the most likely tokens.</li>
        <li><strong>Output:</strong> The text will be more coherent and focused, with less randomness and creativity.</li>
        <li><strong>Use Case:</strong> Ideal for generating concise, coherent text where maintaining context is crucial.</li>
    </ul>
    
    <h3>Moderate Top-k (51 to 100):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model considers a wider range of tokens, increasing diversity while maintaining coherence.</li>
        <li><strong>Output:</strong> The text is generally well-structured with a moderate amount of creativity and variation.</li>
        <li><strong>Use Case:</strong> Suitable for most applications where a balance between creativity and coherence is desired.</li>
    </ul>
    
    <h3>High Top-k (101 to 200):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model has a larger pool of tokens to choose from, enhancing creativity and diversity.</li>
        <li><strong>Output:</strong> The text becomes more varied and creative, with an increased likelihood of unexpected or novel phrases.</li>
        <li><strong>Use Case:</strong> Good for creative writing, brainstorming, and when you want more innovative or out-of-the-box content.</li>
    </ul>
    
    <h3>Very High Top-k (201 and above):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model considers a very large number of tokens, greatly increasing the diversity of the output.</li>
        <li><strong>Output:</strong> The text can become very varied and potentially less coherent, with a higher chance of novel and surprising elements.</li>
        <li><strong>Use Case:</strong> Best for generating highly creative, experimental, or whimsical content where innovation is prioritized over coherence.</li>
    </ul>
    
    <h2>Example Configurations:</h2>
    
    <h3>Low Top-k:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.8,
  "top_p": 0.9,
  "top_k": 20
}
    </pre>
    <p><strong>Output:</strong> Highly coherent and focused text.</p>
    
    <h3>Moderate Top-k:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.9,
  "top_p": 0.9,
  "top_k": 75
}
    </pre>
    <p><strong>Output:</strong> Balanced text with coherence and creativity.</p>
    
    <h3>High Top-k:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.0,
  "top_p": 0.9,
  "top_k": 150
}
    </pre>
    <p><strong>Output:</strong> More creative and diverse text with a good balance of coherence.</p>
    
    <h3>Very High Top-k (Maximum Diversity):</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.2,
  "top_p": 0.9,
  "top_k": 300
}
    </pre>
    <p><strong>Output:</strong> Highly creative and varied text, with a higher chance of unexpected or novel content.</p>
    
</body>
</html>
"""   

            # Modify the event binding to use a lambda function
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))            
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.top_k_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)


            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="top_p")
            
            # Assuming "some_text" is the text you want to pass as a parameter
            dos.html_content ="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Top-p Ranges Explained</title>
</head>
<body>
    <h1>Top-p Ranges Explained</h1>
    
    <h2>Top-p Range Effects:</h2>
    
    <h3>Low Top-p (0.1 to 0.3):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model focuses on a very small set of highly probable tokens.</li>
        <li><strong>Output:</strong> The text will be highly coherent and predictable, with less creativity and diversity.</li>
        <li><strong>Use Case:</strong> Suitable for generating formal, factual, or highly structured content where precision and coherence are paramount.</li>
    </ul>
    
    <h3>Moderate Top-p (0.4 to 0.7):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model considers a broader set of probable tokens, balancing coherence and creativity.</li>
        <li><strong>Output:</strong> The text will have a good balance of coherence and creativity, with more diverse and interesting outputs than a low top-p.</li>
        <li><strong>Use Case:</strong> Suitable for general-purpose text generation where a balance between creativity and coherence is desired.</li>
    </ul>
    
    <h3>High Top-p (0.8 to 1.0):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model considers a wide range of tokens, including less probable ones.</li>
        <li><strong>Output:</strong> The text will be more creative, diverse, and potentially surprising, but with a higher risk of incoherence.</li>
        <li><strong>Use Case:</strong> Suitable for creative writing, brainstorming, and generating artistic or unconventional content.</li>
    </ul>
    
    <h2>Example Configurations:</h2>
    
    <h3>Low Top-p:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.8,
  "top_p": 0.2,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Highly coherent, predictable text.</p>
    
    <h3>Moderate Top-p:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.9,
  "top_p": 0.5,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Balanced text with both coherence and creativity.</p>
    
    <h3>High Top-p:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.0,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Creative and diverse text with a higher chance of surprises.</p>
    
    <h3>Very High Top-p (Maximum Creativity):</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.2,
  "top_p": 1.0,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Highly creative and diverse, with a significant chance of incoherence.</p>
    
</body>
</html>"""   

            # Modify the event binding to use a lambda function
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))

            #dos.Bind(wx.EVT_ENTER_WINDOW, self.onHover)
            #dos.Bind(wx.EVT_LEAVE_WINDOW, self.onLeave)
    
   
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.top_p_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)




            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="temp-re")
            dos.html_content ="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Temperature Ranges Explained</title>
</head>
<body>
    <h1>Temperature Ranges Explained</h1>
    
    <h2>Temperature Range Effects:</h2>
    
    <h3>Low Temperature (0.2 to 0.5):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model produces highly deterministic and predictable text, focusing on the most probable tokens.</li>
        <li><strong>Output:</strong> The text will be very coherent and structured, with little randomness or creativity.</li>
        <li><strong>Use Case:</strong> Ideal for tasks requiring precision and accuracy, such as technical writing, factual content, and formal documentation.</li>
    </ul>
    
    <h3>Moderate Temperature (0.6 to 0.8):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model introduces some randomness while maintaining a balance between coherence and creativity.</li>
        <li><strong>Output:</strong> The text will be well-structured with moderate creativity, suitable for general-purpose applications.</li>
        <li><strong>Use Case:</strong> Suitable for generating conversational, narrative, and informative text where a balance of creativity and coherence is needed.</li>
    </ul>
    
    <h3>High Temperature (0.9 to 1.2):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model generates more random and creative text, considering a wider range of possible tokens.</li>
        <li><strong>Output:</strong> The text will be diverse, creative, and less predictable, but with a higher risk of incoherence.</li>
        <li><strong>Use Case:</strong> Good for creative writing, brainstorming, and scenarios where innovation and originality are prioritized.</li>
    </ul>
    
    <h3>Very High Temperature (>1.2):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model produces highly random and varied text, often prioritizing creativity over coherence.</li>
        <li><strong>Output:</strong> The text will be highly diverse and potentially novel, but with a significant risk of being incoherent or nonsensical.</li>
        <li><strong>Use Case:</strong> Best for experimental and highly creative tasks where unconventional and surprising outputs are desired.</li>
    </ul>
    
    <h2>Example Configurations:</h2>
    
    <h3>Low Temperature:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.4,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Highly coherent and structured text.</p>
    
    <h3>Moderate Temperature:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Balanced text with coherence and creativity.</p>
    
    <h3>High Temperature:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.0,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Creative and diverse text with a higher risk of surprises.</p>
    
    <h3>Very High Temperature (Maximum Creativity):</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.5,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Highly creative and varied text, with a significant risk of incoherence.</p>
    
</body>
</html>
"""   

            # Modify the event binding to use a lambda function
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))
            
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.temp_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)

            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="repeti")
            dos.html_content ="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Repetition Penalty Ranges Explained</title>
</head>
<body>
    <h1>Repetition Penalty Ranges Explained</h1>
    
    <h2>Repetition Penalty Range Effects:</h2>
    
    <h3>Low Repetition Penalty (1.0 to 1.1):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model slightly penalizes repeated phrases or words, encouraging some variation while maintaining coherence.</li>
        <li><strong>Output:</strong> The text will have minor diversity with high coherence, producing natural-sounding and fluent sentences.</li>
        <li><strong>Use Case:</strong> Suitable for general-purpose text generation where maintaining coherence is important, such as dialogue or narrative writing.</li>
    </ul>
    
    <h3>Moderate Repetition Penalty (1.2 to 1.5):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model moderately penalizes repeated phrases or words, encouraging more variation and creativity.</li>
        <li><strong>Output:</strong> The text will be more diverse and creative, with less repetition and potentially more interesting language.</li>
        <li><strong>Use Case:</strong> Suitable for creative writing, brainstorming, and content that benefits from a higher level of creativity and variation.</li>
    </ul>
    
    <h3>High Repetition Penalty (1.6 to 2.0):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model heavily penalizes repeated phrases or words, promoting maximum variation and creativity.</li>
        <li><strong>Output:</strong> The text will be highly diverse and creative, with minimal repetition, but may risk losing some coherence.</li>
        <li><strong>Use Case:</strong> Ideal for generating highly creative and experimental content where uniqueness and novelty are prioritized over coherence.</li>
    </ul>
    
    <h3>Very High Repetition Penalty (>2.0):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model severely penalizes repeated phrases or words, pushing for extreme variation and novelty.</li>
        <li><strong>Output:</strong> The text will be extremely varied and creative, with very low repetition, but may become difficult to follow or understand.</li>
        <li><strong>Use Case:</strong> Best for experimental writing, artistic projects, or situations where extreme creativity and novelty are desired, even at the cost of coherence.</li>
    </ul>
    
    <h2>Example Configurations:</h2>
    
    <h3>Low Repetition Penalty:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.9,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Text with minor diversity and high coherence.</p>
    
    <h3>Moderate Repetition Penalty:</h3>
    <pre>
{
  "repetition_penalty": 1.3,
  "temperature": 0.9,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> More diverse and creative text with less repetition.</p>
    
    <h3>High Repetition Penalty:</h3>
    <pre>
{
  "repetition_penalty": 1.7,
  "temperature": 0.9,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Highly diverse and creative text with minimal repetition.</p>
    
    <h3>Very High Repetition Penalty (Maximum Creativity):</h3>
    <pre>
{
  "repetition_penalty": 2.1,
  "temperature": 0.9,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Extremely varied and creative text with very low repetition.</p>
    
</body>
</html>
>"""   

            # Modify the event binding to use a lambda function
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))
                        
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.repetition_penalty_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)

           
            
            v_sizer.Add(h_sizer_1, 0, wx.ALIGN_CENTER) 
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
        selected_repetition_penalty = self.repetition_penalty_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.repetition_penalty = float(selected_repetition_penalty )

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
        pp(chat)
        print('RestoreQuestionForTabId', chat)
        if message in self.tabs:
            assert self.chat_type==message[1]
            #print('Chat restoring', message)
            #pp(self.tabs[message])
            self.inputCtrl.SetValue(self.tabs[message]['q'])
            print(self.__class__.__name__, 'RestoreQuestionForTabId', message)
            self.model_dropdown.SetValue(apc.currentModel[message])
            #self.tab_id=message
            #self.q_tab_id=message
            #self.inputCtrl.SetSelection(0, -1)
            self.inputCtrl.SetFocus()
            #print('Restored', message)
            
            #chat.do_sample = (self.do_sample_dropdown.GetValue() == 'True')
            #chat.max_length = int(self.max_length_dropdown.GetValue() )
            
            #chat.min_length = int(self.min_length_dropdown.GetValue() )
            #chat.top_p = float(self.top_p_dropdown.GetValue() )
            #chat.top_k = float(self.top_k_dropdown.GetValue() )
            #chat.temperature = float(self.temp_dropdown.GetValue() )
            #chat.repetition_penalty = float(self.repetition_penalty_dropdown.GetValue() )
            
            print(message, self.tab_id)
            #pp(self.tabs)
        
            if chat.get('max_length', None):
                self.max_length_dropdown.SetValue(str(chat.max_length)) 
            else:
                chat.max_length = int(self.max_length_dropdown.GetValue())  


            if chat.get('min_length', None):
                self.min_length_dropdown.SetValue(str(chat.min_length))
            else:
                chat.min_length = int(self.min_length_dropdown.GetValue())


            if chat.get('top_p', None):
                
                self.top_p_dropdown.SetValue(str(chat.top_p))
                
                #wx.MessageBox(f"top_p {chat.top_p} {self.top_p_dropdown.GetValue()}", "top_p"   )
            else:
                chat.top_p= float(self.top_p_dropdown.GetValue())

            
            if chat.get('top_k', None):
                self.top_k_dropdown.SetValue(str(chat.top_k))
            else:
                chat.top_k = int(self.top_k_dropdown.GetValue())


            if chat.get('temperature', None):
                self.temp_dropdown.SetValue(str(chat.temperature))
            else:
                chat.temperature = float(self.temp_dropdown.GetValue())



            if chat.get('repetition_penalty', None):
                self.repetition_penalty_dropdown.SetValue(str(chat.repetition_penalty))
            else:
                chat.repetition_penalty = float(self.repetition_penalty_dropdown.GetValue())

            if chat.get('do_sample', None) is not None:
                
                val = 'True' if chat.do_sample else 'False'
                self.do_sample_dropdown.SetValue(val)
            else:
                chat.do_sample = (self.do_sample_dropdown.GetValue() == 'True')
    

            #self.max_length_dropdown.SetValue(str(chat.get('max_length', 2048)))    