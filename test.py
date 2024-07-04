import wx
from wx.lib import statbmp
import cv2
import numpy as np
import os
import traceback

class ChooseSaveDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent)
        panel = wx.Panel(self, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        btn1 = wx.Button(panel, -1, 'Save Original Image')
        btn2 = wx.Button(panel, -1, 'Save ROI Image')
        btn3 = wx.Button(panel, -1, 'Save Both')
        sizer.Add(btn1, 0)
        sizer.Add(btn2, 0)
        sizer.Add(btn3, 0)
        panel.SetSizer(sizer)

        btn1.Bind(wx.EVT_BUTTON, self.save_orig)
        btn2.Bind(wx.EVT_BUTTON, self.save_roi)
        btn3.Bind(wx.EVT_BUTTON, self.save_both)

    def save_orig(self, evt):
        save_dialog = wx.FileDialog(self, "Save Original to JPEG", "", "", "JPG files(*.jpg)", wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)#|wx.FD_CHANGE_DIR)

        if save_dialog.ShowModal() == wx.ID_OK:
            save_path = save_dialog.GetPath()
            if save_path[:-4].lower() != '.jpg':
                save_path += '.jpg'
            print (save_path)
            cv2.imwrite(save_path, self.GetParent().orig_frame)
        self.EndModal(wx.OK)

    def save_roi(self, evt):
        save_dialog = wx.FileDialog(self, "Save ROI to JPEG", "", "", "JPG files(*.jpg)", wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)#|wx.FD_CHANGE_DIR)

        if save_dialog.ShowModal() == wx.ID_OK:
            save_path = save_dialog.GetPath()
            if save_path[:-4].lower() != '.jpg':
                save_path += '.jpg'
            print (save_path)
            cv2.imwrite(save_path, self.GetParent().frameRoi)
        try:
            self.EndModal(wx.OK)
        except wx.PyAssertionError:
            pass

    def save_both(self, evt):
        self.save_orig(evt)
        self.save_roi(evt)


class ShowCapture(wx.Frame):
    def __init__(self, capture, fps=15):
        wx.Frame.__init__(self, None)
        panel = wx.Panel(self, -1)

        #create a grid sizer with 5 pix between each cell
        sizer = wx.GridBagSizer(5, 5)

        self.capture = capture
        ret, frame = self.capture.read()

        height, width = frame.shape[:2]
        self.orig_height = height
        self.orig_width = width

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        self.bmp = wx.BitmapFromBuffer(width, height, frame)

        self.dummy_element = wx.TextCtrl(panel, -1,'')
        self.dummy_element.Hide()

        #create SpinCtrl widgets, these have vertical up/down buttons and a TextCtrl that increments with up/down press
        self.roi_x = wx.SpinCtrl(panel, -1, "ROI X",  style=wx.TE_PROCESS_ENTER|wx.SP_ARROW_KEYS, min=0, max=width, initial=0, size=(60,-1))
        self.roi_y = wx.SpinCtrl(panel, -1, "ROI Y",  style=wx.TE_PROCESS_ENTER|wx.SP_ARROW_KEYS, min=0, max=height, initial=0, size=(60,-1))
        self.roi_width = wx.SpinCtrl(panel, -1, "ROI W",  style=wx.TE_PROCESS_ENTER|wx.SP_ARROW_KEYS, min=0, max=width, initial=width, size=(60,-1))
        self.roi_height = wx.SpinCtrl(panel, -1, "ROI H",  style=wx.TE_PROCESS_ENTER|wx.SP_ARROW_KEYS, min=0, max=height, initial=height, size=(60,-1))

        save_bmp_path = os.path.join(os.path.dirname(__file__), 'icons', 'ic_action_save.png')
        if os.path.isfile(save_bmp_path):
            save_bmp = wx.Image(save_bmp_path).ConvertToBitmap()
            save_button = wx.BitmapButton(panel,wx.ID_ANY, bitmap=save_bmp, style = wx.NO_BORDER, size=(32,32)) # )
        else:
            save_button = wx.Button(panel, -1, 'Save')

        settings_bmp_path = os.path.join(os.path.dirname(__file__), 'icons', 'ic_action_settings.png')
        if os.path.isfile(settings_bmp_path):
            settings_bmp = wx.Image(settings_bmp_path).ConvertToBitmap()
            settings_button = wx.BitmapButton(panel,wx.ID_ANY, bitmap=settings_bmp, style = wx.NO_BORDER, size=(32,32)) # )
        else:
            settings_button = wx.Button(panel, -1, 'Settings')

        #create image display widgets
        self.ImgControl = statbmp.GenStaticBitmap(panel, wx.ID_ANY, self.bmp)
        self.ImgControl2 = statbmp.GenStaticBitmap(panel, wx.ID_ANY, self.bmp)

        #add text to the sizer grid
        sizer.Add(wx.StaticText(panel, -1, 'ROI'), (0, 0), (1,2),  wx.ALL, 5)
        sizer.Add(wx.StaticText(panel, -1, 'X'), (1, 0), wx.DefaultSpan,  wx.ALL, 5)
        sizer.Add(wx.StaticText(panel, -1, 'Y'), (2, 0), wx.DefaultSpan,  wx.ALL, 5)
        sizer.Add(wx.StaticText(panel, -1, 'width,'), (1, 2), wx.DefaultSpan,  wx.ALL, 5)
        sizer.Add(wx.StaticText(panel, -1, 'height'), (2, 2), wx.DefaultSpan,  wx.ALL, 5)
        sizer.Add(wx.StaticText(panel, -1, 'Right-click image to reset ROI'), (2, 4), wx.DefaultSpan,  wx.ALL, 5)

        tool_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        tool_button_sizer.Add(save_button, 0)
        tool_button_sizer.Add(settings_button, 0)
        #sizer.Add(, (0, 6), wx.DefaultSpan, wx.ALIGN_RIGHT)#,  wx.ALL, 5)
        sizer.Add(tool_button_sizer, (0, 7), wx.DefaultSpan, wx.ALIGN_RIGHT)#,  wx.ALL, 5)

        #add SpinCtrl widgets to the sizer grid
        sizer.Add(self.roi_x, (1, 1), wx.DefaultSpan,  wx.ALL, 5)
        sizer.Add(self.roi_y, (2, 1), wx.DefaultSpan,  wx.ALL, 5)
        sizer.Add(self.roi_width, (1, 3), wx.DefaultSpan,  wx.ALL, 5)
        sizer.Add(self.roi_height, (2, 3), wx.DefaultSpan,  wx.ALL, 5)

        #add image widgets to the sizer grid
        sizer.Add(self.ImgControl, (3, 0), (1,4), wx.EXPAND|wx.CENTER|wx.LEFT|wx.BOTTOM, 5)
        sizer.Add(self.ImgControl2, (3, 4), (1,4), wx.EXPAND|wx.CENTER|wx.RIGHT|wx.BOTTOM, 5)

        #set the sizer and tell the Frame about the best size
        panel.SetSizer(sizer)
        sizer.SetSizeHints(self)
        panel.Layout()
        panel.SetFocus()

        #start a timer that's handler grabs a new frame and updates the image widgets
        self.timer = wx.Timer(self)
        self.fps = fps
        self.timer.Start(int(1000./self.fps))

        #bind timer events to the handler
        self.Bind(wx.EVT_TIMER, self.NextFrame)

        #bind events to ROI image widget
        self.ImgControl2.Bind(wx.EVT_LEFT_DOWN, self.On_ROI_Click)
        self.ImgControl2.Bind(wx.EVT_LEFT_UP, self.On_ROI_ClickRelease)
        self.ImgControl2.Bind(wx.EVT_RIGHT_DOWN, self.On_ROI_RightClick)
        self.ImgControl2.Bind(wx.EVT_MOTION, self.On_ROI_Hover)
        self.ImgControl2.Bind(wx.EVT_ENTER_WINDOW, self.On_ROI_mouse_enter)
        self.ImgControl2.Bind(wx.EVT_LEAVE_WINDOW, self.On_ROI_mouse_leave)

        #bind save button
        save_button.Bind(wx.EVT_BUTTON, self.on_save_click)
        save_button.Bind(wx.EVT_RIGHT_DOWN, self.on_quick_save)

        #bind settings button
        settings_button.Bind(wx.EVT_BUTTON, self.on_settings_click)
        settings_button.Bind(wx.EVT_LEFT_UP, self.on_settings_click_release)

    def on_settings_click(self, evt):
        pass

    def on_settings_click_release(self, evt):
        self.dummy_element.SetFocus()

    def on_save_click(self, evt):
        modal = ChooseSaveDialog(self)
        self.timer.Stop()
        modal.ShowModal()
        modal.Destroy()
        self.timer.Start(int(1000./self.fps))

    def on_quick_save(self, evt):
        cv2.imwrite('orig_frame.jpg', self.orig_frame)
        cv2.imwrite('frameRoi.jpg', self.frameRoi)

    def On_ROI_RightClick(self, evt):
        self.roi_x.SetValue(0)        
        self.roi_y.SetValue(0)
        self.roi_width.SetValue(self.orig_width)
        self.roi_height.SetValue(self.orig_height)

    def On_ROI_Hover(self, evt):
        self.ROI_crosshair_pos = evt.GetPosition()

    def On_ROI_mouse_enter(self, evt):
        self.enable_crosshairs = True

    def On_ROI_mouse_leave(self, evt):
        try:
            self.enable_crosshairs = False
            if hasattr(self, 'roi_click_down_pos'):
                self.update_spinners(evt.GetPosition())
            del self.roi_click_down_pos
        except AttributeError:
            pass

    def On_ROI_Click(self, evt):
        self.roi_click_down_pos = evt.GetPosition()

    def On_ROI_ClickRelease(self, evt):
        roi_click_up_pos = evt.GetPosition()
        #if roi_click_up_pos[0] >= 0 and roi_click_up_pos[1] >= 0:
        if hasattr(self, 'roi_click_down_pos'):
            self.update_spinners(roi_click_up_pos)
        try:
            del self.roi_click_down_pos
        except AttributeError:
            pass

    def update_spinners(self, new_pos):
        self.roi_width.SetValue(abs(new_pos[0] - self.roi_click_down_pos[0]))
        self.roi_height.SetValue(abs(new_pos[1] - self.roi_click_down_pos[1]))
        self.roi_x.SetValue(min(self.roi_click_down_pos[0], new_pos[0]))
        self.roi_y.SetValue(min(self.roi_click_down_pos[1], new_pos[1]))

    def NextFrame(self, event):
        ret, self.orig_frame = self.capture.read()
        if ret:
            frame = cv2.cvtColor(self.orig_frame, cv2.COLOR_BGR2RGB)

            self.bmp.CopyFromBuffer(frame)
            self.ImgControl.SetBitmap(self.bmp)

            try:
                orig_height, orig_width = frame.shape[:2]
                y1 = self.roi_y.GetValue()
                y2 = y1 + self.roi_height.GetValue()
                y2 = min(y2, orig_height)
                x1 = self.roi_x.GetValue()
                x2 = x1 + self.roi_width.GetValue()
                x2 = min(x2, orig_width)

                frameRoi = self.orig_frame[y1:y2, x1:x2]
                roi_width = x2-x1
                roi_height = y2-y1
                #frameRoi = cv2.cvtColor(frameRoi, cv2.COLOR_BGR2GRAY )
                #print len(frameRoi)

                #frameRoi -= 110#frameRoi #* 1.25
                #print len(frameRoi)

                #frameRoi = frameRoi.clip(255.)
                #frameRoi = (255./1)*((frameRoi/(255./1))**0.5)# 0.5

                if hasattr(self, 'ROI_crosshair_pos') and self.enable_crosshairs:
                    try:
                        cross_x = self.ROI_crosshair_pos[0]
                        cross_y = self.ROI_crosshair_pos[1]
                        frameRoi[0:roi_height, cross_x:cross_x+1] = [42,0,255]
                        frameRoi[cross_y:cross_y+1, 0:roi_width] = [42,0,255]

                        if hasattr(self, 'roi_click_down_pos'):
                            roi_x1 = self.roi_click_down_pos[0]
                            roi_y1 = self.roi_click_down_pos[1]

                            if cross_y>roi_y1:
                                frameRoi[0:roi_y1, 0:roi_width] = frameRoi[0:roi_y1, 0:roi_width]*.50
                                frameRoi[cross_y:roi_height, 0:roi_width] = frameRoi[cross_y:roi_height, 0:roi_width]*.50
                            else:
                                frameRoi[roi_y1:roi_height, 0:roi_width] = frameRoi[roi_y1:roi_height, 0:roi_width]*.50
                                frameRoi[0:cross_y, 0:roi_width] = frameRoi[0:cross_y, 0:roi_width]*.50

                            if cross_x>roi_x1:
                                frameRoi[0:roi_height, 0:roi_x1] = frameRoi[0:roi_height, 0:roi_x1]*.50
                                frameRoi[0:roi_height, cross_x:roi_width] = frameRoi[0:roi_height, cross_x:roi_width]*.50
                            else:
                                frameRoi[0:roi_height, roi_x1:roi_width] = frameRoi[0:roi_height, roi_x1:roi_width]*.50
                                frameRoi[0:roi_height, 0:cross_x] = frameRoi[0:roi_height, 0:cross_x]*.50


                    except:
                        print ('couldn\'t draw crosshairs')
                        traceback.print_exc()
                self.frameRoi = np.array(frameRoi , dtype = np.uint8)

                #frameRoi = np.repeat(frameRoi, 3)
                #frameRoi = array(newImage0,dtype=uint8)

                frameRoi = cv2.cvtColor(self.frameRoi, cv2.COLOR_BGR2RGB)#GRAY2RGB)
                self.bmp2 = wx.BitmapFromBuffer(roi_width, roi_height, frameRoi)
                self.ImgControl2.SetBitmap(self.bmp2)

            except:
                traceback.print_exc()

capture = cv2.VideoCapture('test.mp4')
#capture.set(cv.CV_CAP_PROP_FRAME_WIDTH, 320)
#capture.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 240)

app = wx.App()
frame = ShowCapture( capture)
frame.Show()
app.MainLoop()