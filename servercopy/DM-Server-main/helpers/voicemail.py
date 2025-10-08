import os
import io
import requests
from pydub import AudioSegment
import pyaudio

def play_audio_voice(file_path: str, vac_index: int):
    """
    Plays an MP3 or WAV file to a Virtual Audio Cable output.
    Can accept both local file paths and HTTP URLs.
    """
    print(f"Sending voice mail {file_path} with VAC {vac_index}")

    # Decide how to load the file
    if file_path.startswith("http://") or file_path.startswith("https://"):
        # Download from URL
        try:
            response = requests.get(file_path)
            response.raise_for_status()
        except Exception as e:
            print(f"Error downloading audio: {e}")
            return
        
        # Try detecting format from file extension
        ext = file_path.split('.')[-1].lower()
        audio = AudioSegment.from_file(io.BytesIO(response.content), format=ext)
    else:
        # Load directly from local path
        if not os.path.exists(file_path):
            print(f"Local file not found: {file_path}")
            return
        audio = AudioSegment.from_file(file_path)

    # Extract audio parameters
    raw_data = audio.raw_data
    sample_width = audio.sample_width
    channels = audio.channels
    frame_rate = audio.frame_rate

    # Play through VAC
    p = pyaudio.PyAudio()
    stream = p.open(
        format=p.get_format_from_width(sample_width),
        channels=channels,
        rate=frame_rate,
        output=True,
        output_device_index=vac_index
    )

    chunk_size = 1024
    for i in range(0, len(raw_data), chunk_size):
        stream.write(raw_data[i:i+chunk_size])

    stream.stop_stream()
    stream.close()
    p.terminate()


def get_list():

    p = pyaudio.PyAudio()

    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        print(i, dev['name'], dev['maxOutputChannels'])

# 0 Microsoft Sound Mapper - Input 0
# 1 Microphone Array (Realtek High  0
# 2 Line 2 (Virtual Audio Cable) 0
# 3 Line 1 (Virtual Audio Cable) 0
# 4 Line 3 (Virtual Audio Cable) 0
# 5 CABLE Output (VB-Audio Virtual  0
# 6 Line 4 (Virtual Audio Cable) 0
# 7 Microsoft Sound Mapper - Output 2
# 8 Speaker/HP (Realtek High Defini 2
# 9 CABLE In 16 Ch (VB-Audio Virtua 16
# 10 Line 4 (Virtual Audio Cable) 8
# 11 Line 2 (Virtual Audio Cable) 8
# 12 Line 1 (Virtual Audio Cable) 8
# 13 Line 3 (Virtual Audio Cable) 8
# 14 Speakers (VB-Audio Virtual Cabl 16
# 15 Primary Sound Capture Driver 0
# 16 Microphone Array (Realtek High Definition Audio) 0
# 17 Line 2 (Virtual Audio Cable) 0
# 18 Line 1 (Virtual Audio Cable) 0
# 19 Line 3 (Virtual Audio Cable) 0
# 20 CABLE Output (VB-Audio Virtual Cable) 0
# 21 Line 4 (Virtual Audio Cable) 0
# 22 Primary Sound Driver 2
# 23 Speaker/HP (Realtek High Definition Audio) 2
# 24 CABLE In 16 Ch (VB-Audio Virtual Cable) 16
# 25 Line 4 (Virtual Audio Cable) 8
# 26 Line 2 (Virtual Audio Cable) 8
# 27 Line 1 (Virtual Audio Cable) 8
# 28 Line 3 (Virtual Audio Cable) 8
# 29 Speakers (VB-Audio Virtual Cable) 16
# 30 CABLE In 16 Ch (VB-Audio Virtual Cable) 2
# 31 Line 4 (Virtual Audio Cable) 2
# 32 Line 2 (Virtual Audio Cable) 2
# 33 Speaker/HP (Realtek High Definition Audio) 2
# 34 Line 1 (Virtual Audio Cable) 2
# 35 Line 3 (Virtual Audio Cable) 2
# 36 Speakers (VB-Audio Virtual Cable) 2
# 37 Line 2 (Virtual Audio Cable) 0
# 38 Line 1 (Virtual Audio Cable) 0
# 39 Microphone Array (Realtek High Definition Audio) 0
# 40 Line 3 (Virtual Audio Cable) 0
# 41 CABLE Output (VB-Audio Virtual Cable) 0
# 42 Line 4 (Virtual Audio Cable) 0
# 43 Mic 1 (Virtual Cable 1) 0
# 44 Line Out (Virtual Cable 1) 8
# 45 Mic 2 (Virtual Cable 2) 0
# 46 Line Out (Virtual Cable 2) 8
# 47 Mic 3 (Virtual Cable 3) 0
# 48 Line Out (Virtual Cable 3) 8
# 49 Mic 4 (Virtual Cable 4) 0
# 50 Line Out (Virtual Cable 4) 8
# 51 CABLE Output (VB-Audio Point) 0
# 52 Output (VB-Audio Point) 16
# 53 Input (VB-Audio Point) 0
# 54 Microphone Array (Realtek HD Audio Mic input) 0
# 55 Speakers (Realtek HD Audio output) 2


#play_audio_voice("http://127.0.0.1:5000/uploads/audio/20250813_200653_demo.mp3", 10)





# --------------------------
# Example usage:
# First run the device list code to find your VAC index
# play_audio_to_vac("your_audio.wav", 4)
