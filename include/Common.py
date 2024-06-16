import wx
import sys, traceback
from pubsub import pub
from include.fmt import fmt
from pprint import pprint as pp 
import include.config.init_config as init_config 
apc = init_config.apc

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
        
        
class Base_InputPanel:
    def AddButtons(self, h_sizer):
        if 1: #second row
            chat=apc.chats[self.tab_id] 
            self.do_sample_dropdown = wx.ComboBox(self, choices=['True', 'False'], style=wx.CB_READONLY)
            self.do_sample_dropdown.SetValue('False')  # Default value
            self.do_sample_dropdown.Bind(wx.EVT_COMBOBOX, self.OnDoSampleChange)
            chat.do_sample = (self.do_sample_dropdown.GetValue() == 'True')
        
            self.max_length_dropdown = wx.ComboBox(self, choices=['512', '1024', '2048', '4096'], style=wx.CB_READONLY)
            self.max_length_dropdown.SetValue('2048')  # Default value
            self.max_length_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMaxLengthChange)
            chat.max_length = int(self.max_length_dropdown.GetValue())

            self.min_length_dropdown = wx.ComboBox(self, choices=['1', '512', '1024', '2048', '4096'], style=wx.CB_READONLY)
            self.min_length_dropdown.SetValue('1')  # Default value
            self.min_length_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMinLengthChange)
            chat.min_length = int(self.min_length_dropdown.GetValue()  )

            self.top_p_dropdown = wx.ComboBox(self, choices=['0.0',  '0.1',  '0.2',  '0.3',  '0.4',  '0.5',  '0.6',  '0.7',  '0.8',  '0.9',  '1.0',  '1.1',], style=wx.CB_READONLY)
            self.top_p_dropdown.SetValue('1.0')  # Default value
            self.top_p_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTopPChange)
            chat.top_p = float(self.top_p_dropdown.GetValue()  )
            #top_k
            self.top_k_dropdown = wx.ComboBox(self, choices=['1',  '2',  '3',  '4',  '5',  '10',  '20',  '50',  '75',  '100',  '150',], style=wx.CB_READONLY)
            self.top_k_dropdown.SetValue('50')  # Default value
            self.top_k_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTopKChange)
            chat.top_k = int(self.top_k_dropdown.GetValue()  )     

            self.temp_dropdown = wx.ComboBox(self, choices=['0.0',  '0.1',  '0.2',  '0.3',  '0.4',  '0.5',  '0.6',  '0.7',  '0.8',  '0.9',  '1.0',  '2.0', '5.0', '10.0', '50.0'], style=wx.CB_READONLY)
            self.temp_dropdown.SetValue('1.0')  # Default value
            self.temp_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTempChange)
            chat.temperature = float(self.temp_dropdown.GetValue()  )  
            #repetition_penalty
            self.repetition_penalty_dropdown = wx.ComboBox(self, choices=['1.0',  '1.1',  '1.2',  '1.3',  '1.4',  '1.5',  '1.6',  '1.7',  '1.8',  '1.9',  '2.0',  '2.1',], style=wx.CB_READONLY)
            self.repetition_penalty_dropdown.SetValue('1.0')  # Default value
            self.repetition_penalty_dropdown.Bind(wx.EVT_COMBOBOX, self.OnRepetitionPenaltyChange)
            chat.repetition_penalty = float(self.repetition_penalty_dropdown.GetValue()  )             

            h_sizer.Add(self.do_sample_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer.Add(self.max_length_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer.Add(self.min_length_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer.Add(self.top_p_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer.Add(self.top_k_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer.Add(self.temp_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer.Add(self.repetition_penalty_dropdown, 0, wx.ALIGN_CENTER)

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