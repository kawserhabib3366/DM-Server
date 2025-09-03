

# 🛠️ Full Setup Guide: Chrome ↔ VAC ↔ Python Audio Routing





## 🔹 Part 1: Enable ALSA Loopback (VAC)

### 1.1 Install ALSA utilities
```bash
sudo apt update
sudo apt install alsa-utils
```

### 1.2 Load the loopback kernel module
```bash
sudo modprobe snd-aloop
```

### 1.3 Make it persistent across reboots
```bash
echo snd-aloop | sudo tee /etc/modules-load.d/snd-aloop.conf
echo "options snd-aloop index=0" | sudo tee /etc/modprobe.d/snd-aloop.conf
```

### 1.4 Add your user to the `audio` group
```bash
sudo usermod -aG audio $USER
```
Then **log out and back in** or reboot.

### 1.5 Verify loopback device
```bash
aplay -l
arecord -l
```
You should see:
```
card 0: Loopback [Loopback], device 0: Loopback PCM
card 0: Loopback [Loopback], device 1: Loopback PCM
```

---

## 🔹 Part 2: Configure ALSA Routing

### 2.1 Create `.asoundrc` in your home directory
```bash
nano ~/.asoundrc
```

Paste this:
```ini
pcm.loop_capture {
    type hw
    card 0
    device 0
}

pcm.loop_playback {
    type hw
    card 0
    device 1
}

pcm.loop_asym {
    type asym
    playback.pcm "loop_playback"
    capture.pcm  "loop_capture"
}

pcm.!default loop_asym
ctl.!default loop_asym
```

This makes `loop_asym` the default device for both playback and capture.

---

## 🔹 Part 3: Python Integration




### 3.1 Use PyAudio to detect VAC
```python
import pyaudio

def find_vac_devices():
    audio = pyaudio.PyAudio()
    vac_devices = []

    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        name = info['name'].lower()
        if 'loopback' in name or 'virtual' in name or 'vac' in name:
            vac_devices.append({
                'index': i,
                'name': info['name'],
                'max_input_channels': info['maxInputChannels'],
                'max_output_channels': info['maxOutputChannels'],
                'default_sample_rate': info['defaultSampleRate']
            })

    audio.terminate()
    return vac_devices
```



### 3.2 Set environment variables for your agent
```bash
export INPUT_VAC=0   # hw:0,0
export OUTPUT_VAC=1  # hw:0,1
```

### 3.3 Use these in your Python agent
```python
audio_interface = VACAudioInterface(
    input_device_index=int(os.getenv("INPUT_VAC")),
    output_device_index=int(os.getenv("OUTPUT_VAC"))
)
```

---

## 🔹 Part 4: Route Chrome Audio Through VAC





 Test the Full Loop

### ✅ Chrome → Python
Play audio in Google Voice. Your Python script should receive it via `hw:0,1`.

### ✅ Python → Chrome
Generate audio in Python and write it to `hw:0,0`. Chrome will treat it as microphone input.

