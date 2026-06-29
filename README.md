# AirWin Streamer

Tested on HomePod (Check other devices)

Send **all the audio from your Windows PC** to a **HomePod** using **AirPlay 2** over Wi-Fi, with a small windowed application.

##Requirements

- Windows 10/11
- PC and HomePod on the **same Wi-Fi network** (not a guest network or isolated VLAN)
- Python 3.10+ (tested with 3.12)


## Process

```powershell
cd C:\..\AirWin
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

## Use

Double click in **`HomePod Streamer.bat`**, or:

```powershell
.\.venv\Scripts\python main.py
```

1. The app automatically scans when you open it. Tap **🔄 Search** if your HomePod doesn't appear.
2. Select your HomePod from the list.
3. Leave **"Mute PC (HomePod only)"** checked so that the audio comes *only* through the HomePod and not the PC speakers. If you uncheck it, it will play through both.
4. Tap **▶ Start Streaming**. Now everything playing on your PC will go to your HomePod.
5. Adjust the HomePod's **volume** using the slider.
6. Tap **■ Stop** to finish (this automatically restores the PC's sound).

## Latency (important)

AirPlay adds approximately 2 seconds of latency by design (Apple buffers to sync multi-room audio). Result:

- Music/podcasts: perfect.

- Video/games: audio will lag approximately 2 seconds behind the video. This is due to the AirPlay protocol, not the software; it cannot be eliminated.

## Technical Stack

`pyatv` (AirPlay 2 / RAOP) · `PyAudioWPatch` (WASAPI loopback) · `pycaw` (mute del PC) ·
`customtkinter` (GUI). Todo software libre y gratuito.
