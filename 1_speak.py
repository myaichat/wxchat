import wx
import threading
import time
import  asyncio
import unittest
from unittest.mock import AsyncMock, patch
from pprint import pprint as pp
import os, time
import numpy as np
import pyaudio

from typing import Optional

#from ai_voice_bot.transcribe.LocalWhisper import LocalWhisper
#from ai_voice_bot.transcribe.ApiWhisper import ApiWhisper
#from ai_voice_bot.transcribe.GooTranscribe import GooTranscribe   


from colorama import Fore, Back, Style, init

#from ai_voice_bot.mock.MockAudioHandler import MockAudioHandler
#from ai_voice_bot.client.TextRealtimeClient import RealtimeClient
# AudioHandler class

init(autoreset=True)


class MockAudioHandler:
    def __init__(self):
        # Audio parameters
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 24000
        self.chunk = 1024  # Buffer size for each read

        self.audio = pyaudio.PyAudio()

        # Threshold for detecting speech (based on amplitude)
        self.speech_threshold = 500  # Adjust this value as needed
        self.silence_duration_threshold = 1.0  # 1 second of silence considered speech stop

        # Recording params
        self.recording_stream: Optional[pyaudio.Stream] = None
        self.recording = False

        # streaming params
        self.streaming = False
        self.stream = None

        self.last_speech_time = None
        self.speech_started = False
        self.tid=0

    def is_speech(self, audio_chunk: bytes) -> bool:
        """Determine if an audio chunk contains speech based on amplitude."""
        audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
        max_amplitude = np.max(np.abs(audio_data))
        return max_amplitude > self.speech_threshold

    async def start_streaming(self, client: 'MockRealtimeClient'):
        """Start continuous audio streaming."""
        if self.streaming:
            return

        self.streaming = True
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )

        print("\nListening for speech...")

        self.last_speech_time = None
        self.speech_started = False

        while self.streaming:
            try:
                # Read raw PCM data
                data = self.stream.read(self.chunk * 8, exception_on_overflow=False)

                # Check if the chunk contains speech
                if self.is_speech(data):
                    if not self.speech_started:
                        # Speech has just started
                        print("\n[Speech detected]")
                        self.tid +=1
                        tid=self.tid                        
                        await client.handle_event("input_audio_buffer.speech_started",tid)
                        self.speech_started = True

                    # Reset the silence duration
                    self.last_speech_time = asyncio.get_event_loop().time()

                else:
                    # Check if it's been quiet for longer than the threshold
                    if self.speech_started and (asyncio.get_event_loop().time() - self.last_speech_time > self.silence_duration_threshold):
                        print("\n[Speech ended]")

                        
                        tid=self.tid
                        await client.handle_event("input_audio_buffer.speech_stopped", tid)
                        self.speech_started = False

                # Stream the audio to the client only if speech is ongoing
                if self.speech_started:

                    await client.stream_audio(tid,data)

            except Exception as e:
                print(f"Error streaming: {e}")
                raise e
                break
            await asyncio.sleep(0.01)

    def stop_streaming(self):
        """Stop audio streaming."""
        self.streaming = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def cleanup(self):
        """Clean up audio resources"""
        self.stop_streaming()
        self.audio.terminate()
class MockRealtimeClient:
    def __init__(self, on_audio_transcript_delta=None):
        """Initialize the mock client with optional callback."""
        self.audio = {} #b''
        if 0:
            self.local_whisper = LocalWhisper()
        self.api_whisper = ApiWhisper()
        self.goo_transcribe = GooTranscribe()
        

    async def connect(self) -> None:
        """Mock WebSocket connection for testing."""
        print("Connected to Mock WebSocket")

    async def stream_audio(self, tid, audio_chunk: bytes):
        """Mock method to stream audio chunks to WebSocket."""
        if tid not in self.audio:
            self.audio[tid] = b''
        self.audio[tid]  += audio_chunk

    async def handle_event(self, event_type, tid):
        """Handle events such as speech_started and speech_stopped."""
        if event_type == "input_audio_buffer.speech_started":
            pass
        elif event_type == "input_audio_buffer.speech_stopped":
            # When speech stops, trigger transcription in parallel
           
            
            asyncio.create_task(self.on_audio_transcript(tid))

    async def on_audio_transcript(self, tid):
        """Transcribe audio chunk in parallel while streaming continues."""
        print("\nTranscribing audio...", tid)
        #await asyncio.sleep(10)  # Simulate processing delay
        start_time = time.time()
        file_name: str = f"{tid}_temp_audio_chunk.wav"
        audio = self.audio[tid]
        self.api_whisper.write_audio(audio, file_name)
        if 1:

            tasks = [
                #asyncio.to_thread(self.local_whisper.local_transcribe_audio, audio,file_name),
                asyncio.to_thread(self.api_whisper.transcribe_audio, audio,file_name),
                asyncio.to_thread(self.goo_transcribe.transcribe_audio, audio,file_name)
            ]
        else:
            tasks = [
                #asyncio.create_task(self.local_whisper.write_audio(audio,file_name)),
                #asyncio.create_task(self.local_whisper.local_transcribe_audio(audio,file_name)),
                asyncio.create_task(self.api_whisper.transcribe_audio(audio,file_name)),
                asyncio.create_task(self.goo_transcribe.transcribe_audio(audio,file_name))
            ]
        if 1:
            results= await asyncio.gather(*tasks)
            pp( results)
            self.chunk = b''  # Reset the chunk after processing
            for res in results:
                if res:
                    print(res[1], end=" ")

            print()
            for res in results:
                if res:
                    print(res[2], end=" ")

            print()            
        end_time = time.time()
        elapsed_time = end_time - start_time
        print("Transcription complete", tid, elapsed_time)


class MyFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(MyFrame, self).__init__(*args, **kw)

        panel = wx.Panel(self)

        # Create ListCtrl
        self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT)
        
        # Add columns to the list control
        self.list_ctrl.InsertColumn(0, 'Column 1', width=100)
        self.list_ctrl.InsertColumn(1, 'Column 2', width=100)
        self.list_ctrl.InsertColumn(2, 'Column 3', width=100)

        # Create button
        self.button = wx.Button(panel, label='Populate List')
        self.button.Bind(wx.EVT_BUTTON, self.on_button_click)
        self.button.Disable()  # Disable button until thread completes

        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.button, 0, wx.CENTER | wx.ALL, 5)
        panel.SetSizer(sizer)

        # Start the long-running process in a background thread
        self.long_running_thread = threading.Thread(target=self.long_running_process)
        self.long_running_thread.start()

    def long_running_process(self):
        # Simulate a long-running task
        time.sleep(5)  # Simulate the process taking 5 seconds
        
        # After long-running task, enable the button
        wx.CallAfter(self.enable_button)

    def enable_button(self):
        # Enable the button when the long-running task is done
        self.button.Enable()

    def on_button_click(self, event):
        # Clear the list before populating
        self.list_ctrl.DeleteAllItems()

        # Add rows to the list control
        data = [("Item 1", "Value 1", "Info 1"),
                ("Item 2", "Value 2", "Info 2"),
                ("Item 3", "Value 3", "Info 3")]

        for row in data:
            index = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), row[0])
            self.list_ctrl.SetItem(index, 1, row[1])
            self.list_ctrl.SetItem(index, 2, row[2])

class MyApp(wx.App):
    def OnInit(self):
        frame = MyFrame(None, title="wxPython List Control with Threading", size=(400, 300))
        frame.Show()
        return True

if __name__ == "__main__":
    app = MyApp()
    app.MainLoop()
