import wx
import math

def fraction_to_value(fraction, min_value, max_value):
    return (max_value - min_value) * fraction + min_value

def value_to_fraction(value, min_value, max_value):
    return float(value - min_value) / (max_value - min_value)

def round_to_step(value, step, min_value):
    return round((value - min_value) / step) * step + min_value

class SliderThumb:
    def __init__(self, parent, value):
        self.parent = parent
        self.dragged = False
        self.mouse_over = False
        self.thumb_poly = ((0, 0), (0, 13), (5, 18), (10, 13), (10, 0))
        self.thumb_shadow_poly = ((0, 14), (4, 18), (6, 18), (10, 14))
        min_coords = [float('Inf'), float('Inf')]
        max_coords = [-float('Inf'), -float('Inf')]
        for pt in list(self.thumb_poly) + list(self.thumb_shadow_poly):
            for i_coord, coord in enumerate(pt):
                if coord > max_coords[i_coord]:
                    max_coords[i_coord] = coord
                if coord < min_coords[i_coord]:
                    min_coords[i_coord] = coord
        self.size = (max_coords[0] - min_coords[0],
                     max_coords[1] - min_coords[1])

        self.value = value
        self.normal_color = wx.Colour((0, 120, 215))
        self.normal_shadow_color = wx.Colour((120, 180, 228))
        self.dragged_color = wx.Colour((204, 204, 204))
        self.dragged_shadow_color = wx.Colour((222, 222, 222))
        self.mouse_over_color = wx.Colour((23, 23, 23))
        self.mouse_over_shadow_color = wx.Colour((132, 132, 132))

    def GetPosition(self):
        min_x = self.GetMin()
        max_x = self.GetMax()
        parent_size = self.parent.GetSize()
        min_value = self.parent.GetMin()
        max_value = self.parent.GetMax()
        fraction = value_to_fraction(self.value, min_value, max_value)
        pos = (fraction_to_value(fraction, min_x, max_x), parent_size[1] / 2 + 1)
        return pos

    def SetPosition(self, pos):
        pos_x = pos[0]
        # Limit movement by the position of the other thumb
        who_other, other_thumb = self.GetOtherThumb()
        other_pos = other_thumb.GetPosition()
        if who_other == 'low':
            pos_x = max(other_pos[0] + other_thumb.size[0] / 2 + self.size[0] / 2, pos_x)
        else:
            pos_x = min(other_pos[0] - other_thumb.size[0] / 2 - self.size[0] / 2, pos_x)
        # Limit movement by slider boundaries
        min_x = self.GetMin()
        max_x = self.GetMax()
        pos_x = min(max(pos_x, min_x), max_x)

        fraction = value_to_fraction(pos_x, min_x, max_x)
        self.value = round_to_step(fraction_to_value(fraction, self.parent.GetMin(), self.parent.GetMax()), self.parent.step, self.parent.min_value)
        # Post event notifying that position changed
        self.PostEvent()

    def GetValue(self):
        return self.value

    def SetValue(self, value):
        self.value = round_to_step(value, self.parent.step, self.parent.min_value)
        # Post event notifying that value changed
        self.PostEvent()

    def PostEvent(self):
        event = wx.PyCommandEvent(wx.EVT_SLIDER.typeId, self.parent.GetId())
        event.SetEventObject(self.parent)
        wx.PostEvent(self.parent.GetEventHandler(), event)

    def GetMin(self):
        min_x = self.parent.border_width + self.size[0] / 2
        return min_x

    def GetMax(self):
        parent_size = self.parent.GetSize()
        max_x = parent_size[0] - self.parent.border_width - self.size[0] / 2
        return max_x

    def IsMouseOver(self, mouse_pos):
        in_hitbox = True
        my_pos = self.GetPosition()
        for i_coord, mouse_coord in enumerate(mouse_pos):
            boundary_low = my_pos[i_coord] - self.size[i_coord] / 2
            boundary_high = my_pos[i_coord] + self.size[i_coord] / 2
            in_hitbox = in_hitbox and (boundary_low <= mouse_coord <= boundary_high)
        return in_hitbox

    def GetOtherThumb(self):
        if self.parent.thumbs['low'] != self:
            return 'low', self.parent.thumbs['low']
        else:
            return 'high', self.parent.thumbs['high']

    def OnPaint(self, dc):
        if self.dragged or not self.parent.IsEnabled():
            thumb_color = self.dragged_color
            thumb_shadow_color = self.dragged_shadow_color
        elif self.mouse_over:
            thumb_color = self.mouse_over_color
            thumb_shadow_color = self.mouse_over_shadow_color
        else:
            thumb_color = self.normal_color
            thumb_shadow_color = self.normal_shadow_color
        my_pos = self.GetPosition()

        # Draw thumb shadow (or anti-aliasing effect)
        dc.SetBrush(wx.Brush(thumb_shadow_color, style=wx.BRUSHSTYLE_SOLID))
        dc.SetPen(wx.Pen(thumb_shadow_color, width=1, style=wx.PENSTYLE_SOLID))
        dc.DrawPolygon(points=self.thumb_shadow_poly,
                       xoffset=int(my_pos[0] - self.size[0] / 2),
                       yoffset=int(my_pos[1] - self.size[1] / 2))
        # Draw thumb itself
        dc.SetBrush(wx.Brush(thumb_color, style=wx.BRUSHSTYLE_SOLID))
        dc.SetPen(wx.Pen(thumb_color, width=1, style=wx.PENSTYLE_SOLID))
        dc.DrawPolygon(points=self.thumb_poly,
                       xoffset=int(my_pos[0] - self.size[0] / 2),
                       yoffset=int(my_pos[1] - self.size[1] / 2))


class RangeSlider(wx.Panel):
    def __init__(self, parent, id=wx.ID_ANY, lowValue=None, highValue=None, minValue=0.0, maxValue=1.0,
                 step=0.1, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.SL_HORIZONTAL,
                 validator=wx.DefaultValidator, name='rangeSlider'):
        if style != wx.SL_HORIZONTAL:
            raise NotImplementedError('Styles not implemented')
        if validator != wx.DefaultValidator:
            raise NotImplementedError('Validator not implemented')
        super().__init__(parent=parent, id=id, pos=pos, size=size, name=name)
        self.SetMinSize(size=(max(50, size[0]), max(26, size[1])))
        if minValue > maxValue:
            minValue, maxValue = maxValue, minValue
        self.min_value = minValue
        self.max_value = maxValue
        self.step = step
        if lowValue is None:
            lowValue = self.min_value
        if highValue is None:
            highValue = self.max_value
        if lowValue > highValue:
            lowValue, highValue = highValue, lowValue
        lowValue = max(lowValue, self.min_value)
        highValue = min(highValue, self.max_value)

        self.border_width = 8

        self.thumbs = {
            'low': SliderThumb(parent=self, value=lowValue),
            'high': SliderThumb(parent=self, value=highValue)
        }
        self.thumb_width = self.thumbs['low'].size[0]

        # Aesthetic definitions
        self.slider_background_color = wx.Colour((231, 234, 234))
        self.slider_outline_color = wx.Colour((214, 214, 214))
        self.selected_range_color = wx.Colour((0, 120, 215))
        self.selected_range_outline_color = wx.Colour((0, 120, 215))

        # Bind events
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseLost)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnResize)

    def Enable(self, enable=True):
        super().Enable(enable)
        self.Refresh()

    def Disable(self):
        super().Disable()
        self.Refresh()

    def SetValueFromMousePosition(self, click_pos):
        for thumb in self.thumbs.values():
            if thumb.dragged:
                thumb.SetPosition(click_pos)

    def OnMouseDown(self, evt):
        if not self.IsEnabled():
            return
        click_pos = evt.GetPosition()
        for thumb in self.thumbs.values():
            if thumb.IsMouseOver(click_pos):
                thumb.dragged = True
                thumb.mouse_over = False
                break
        self.SetValueFromMousePosition(click_pos)
        self.CaptureMouse()
        self.Refresh()

    def OnMouseUp(self, evt):
        if not self.IsEnabled():
            return
        self.SetValueFromMousePosition(evt.GetPosition())
        for thumb in self.thumbs.values():
            thumb.dragged = False
        if self.HasCapture():
            self.ReleaseMouse()
        self.Refresh()

    def OnMouseLost(self, evt):
        for thumb in self.thumbs.values():
            thumb.dragged = False
            thumb.mouse_over = False
        self.Refresh()

    def OnMouseMotion(self, evt):
        if not self.IsEnabled():
            return
        refresh_needed = False
        mouse_pos = evt.GetPosition()
        if evt.Dragging() and evt.LeftIsDown():
            self.SetValueFromMousePosition(mouse_pos)
            refresh_needed = True
        else:
            for thumb in self.thumbs.values():
                old_mouse_over = thumb.mouse_over
                thumb.mouse_over = thumb.IsMouseOver(mouse_pos)
                if old_mouse_over != thumb.mouse_over:
                    refresh_needed = True
        if refresh_needed:
            self.Refresh()

    def OnMouseEnter(self, evt):
        if not self.IsEnabled():
            return
        mouse_pos = evt.GetPosition()
        for thumb in self.thumbs.values():
            if thumb.IsMouseOver(mouse_pos):
                thumb.mouse_over = True
                self.Refresh()
                break

    def OnMouseLeave(self, evt):
        if not self.IsEnabled():
            return
        for thumb in self.thumbs.values():
            thumb.mouse_over = False
        self.Refresh()

    def OnResize(self, evt):
        self.Refresh()

    def OnPaint(self, evt):
        w, h = self.GetSize()
        # BufferedPaintDC should reduce flickering
        dc = wx.BufferedPaintDC(self)
        background_brush = wx.Brush(self.GetBackgroundColour(), wx.SOLID)
        dc.SetBackground(background_brush)
        dc.Clear()
        # Draw slider
        track_height = 12
        dc.SetPen(wx.Pen(self.slider_outline_color, width=1, style=wx.PENSTYLE_SOLID))
        dc.SetBrush(wx.Brush(self.slider_background_color, style=wx.BRUSHSTYLE_SOLID))
        dc.DrawRectangle(int(self.border_width), int(h / 2 - track_height / 2),
                         int(w - 2 * self.border_width), int(track_height))
        # Draw selected range
        if self.IsEnabled():
            dc.SetPen(wx.Pen(self.selected_range_outline_color, width=1, style=wx.PENSTYLE_SOLID))
            dc.SetBrush(wx.Brush(self.selected_range_color, style=wx.BRUSHSTYLE_SOLID))
        else:
            dc.SetPen(wx.Pen(self.slider_outline_color, width=1, style=wx.PENSTYLE_SOLID))
            dc.SetBrush(wx.Brush(self.slider_outline_color, style=wx.BRUSHSTYLE_SOLID))
        low_pos = self.thumbs['low'].GetPosition()[0]
        high_pos = self.thumbs['high'].GetPosition()[0]
        dc.DrawRectangle(int(low_pos), int(h / 2 - track_height / 4),
                         int(high_pos - low_pos), int(track_height / 2))
        # Draw thumbs
        for thumb in self.thumbs.values():
            thumb.OnPaint(dc)
        evt.Skip()

    def OnEraseBackground(self, evt):
        # This should reduce flickering
        pass

    def GetValues(self):
        return self.thumbs['low'].value, self.thumbs['high'].value

    def SetValues(self, lowValue, highValue):
        if lowValue > highValue:
            lowValue, highValue = highValue, lowValue
        lowValue = max(lowValue, self.min_value)
        highValue = min(highValue, self.max_value)
        self.thumbs['low'].SetValue(lowValue)
        self.thumbs['high'].SetValue(highValue)
        self.Refresh()

    def GetMax(self):
        return self.max_value

    def GetMin(self):
        return self.min_value

    def SetMax(self, maxValue):
        if maxValue < self.min_value:
            maxValue = self.min_value
        _, old_high = self.GetValues()
        if old_high > maxValue:
            self.thumbs['high'].SetValue(maxValue)
        self.max_value = maxValue
        self.Refresh()

    def SetMin(self, minValue):
        if minValue > self.max_value:
            minValue = self.max_value
        old_low, _ = self.GetValues()
        if old_low < minValue:
            self.thumbs['low'].SetValue(minValue)
        self.min_value = minValue
        self.Refresh()


class TestFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, 'Range Slider Demo', size=(300, 100))
        panel = wx.Panel(self)
        b = 6
        vbox = wx.BoxSizer(orient=wx.VERTICAL)
        vbox.Add(wx.StaticText(parent=panel, label='Custom Range Slider:'), flag=wx.ALIGN_LEFT | wx.ALL, border=b)
        self.rangeslider = RangeSlider(parent=panel, lowValue=1.0, highValue=1.9, minValue=0.1, maxValue=2.2,
                                       step=0.3, size=(300, 26))
        self.rangeslider.Bind(wx.EVT_SLIDER, self.rangeslider_changed)
        vbox.Add(self.rangeslider, proportion=1, flag=wx.EXPAND | wx.ALL, border=b)
        self.rangeslider_static = wx.StaticText(panel)
        vbox.Add(self.rangeslider_static, flag=wx.ALIGN_LEFT | wx.ALL, border=b)
        vbox.Add(wx.StaticText(parent=panel, label='Regular Slider with wx.SL_SELRANGE style:'),
                 flag=wx.ALIGN_LEFT | wx.ALL, border=b)
        self.slider = wx.Slider(parent=panel, style=wx.SL_SELRANGE)
        self.slider.SetSelection(20, 40)
        self.slider.Bind(wx.EVT_SLIDER, self.slider_changed)
        vbox.Add(self.slider, proportion=1, flag=wx.EXPAND | wx.ALL, border=b)
        self.slider_static = wx.StaticText(panel)
        vbox.Add(self.slider_static, flag=wx.ALIGN_LEFT | wx.ALL, border=b)
        self.button_toggle = wx.Button(parent=panel, label='Disable')
        self.button_toggle.Bind(wx.EVT_BUTTON, self.toggle_slider_enable)
        vbox.Add(self.button_toggle, flag=wx.ALIGN_CENTER | wx.ALL, border=b)
        panel.SetSizerAndFit(vbox)
        box = wx.BoxSizer()
        box.Add(panel, proportion=1, flag=wx.EXPAND)
        self.SetSizerAndFit(box)

    def slider_changed(self, evt):
        obj = evt.GetEventObject()
        val = obj.GetValue()
        self.slider_static.SetLabel('Value: {}'.format(val))

    def rangeslider_changed(self, evt):
        obj = evt.GetEventObject()
        lv, hv = obj.GetValues()
        self.rangeslider_static.SetLabel('Low value: {:.1f}, High value: {:.1f}'.format(lv, hv))

    def toggle_slider_enable(self, evt):
        if self.button_toggle.GetLabel() == 'Disable':
            self.slider.Enable(False)
            self.rangeslider.Enable(False)
            self.button_toggle.SetLabel('Enable')
        else:
            self.slider.Enable(True)
            self.rangeslider.Enable(True)
            self.button_toggle.SetLabel('Disable')


def main():
    app = wx.App()
    TestFrame().Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
