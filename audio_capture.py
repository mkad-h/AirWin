from __future__ import annotations

import struct
import threading
from typing import Callable, Optional

import pyaudiowpatch as pyaudio

_FRAMES_PER_BUFFER = 2048


class LoopbackInfo:
    def __init__(self, index: int, name: str, channels: int, rate: int):
        self.index = index
        self.name = name
        self.channels = channels
        self.rate = rate


def find_default_loopback(p: pyaudio.PyAudio) -> "LoopbackInfo":
    try:
        wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError as exc:
        raise RuntimeError("WASAPI no está disponible en este sistema.") from exc

    default_speakers = p.get_device_info_by_index(wasapi["defaultOutputDevice"])

    if not default_speakers.get("isLoopbackDevice", False):
        found = None
        for loopback in p.get_loopback_device_info_generator():
            if default_speakers["name"] in loopback["name"]:
                found = loopback
                break
        if found is None:
            raise RuntimeError(
                "No se encontró un dispositivo loopback para el altavoz por defecto. "
                "Asegúrate de tener un dispositivo de salida activo."
            )
        default_speakers = found

    channels = min(2, int(default_speakers["maxInputChannels"]) or 2)
    rate = int(default_speakers["defaultSampleRate"])
    return LoopbackInfo(
        index=int(default_speakers["index"]),
        name=str(default_speakers["name"]),
        channels=channels,
        rate=rate,
    )


def _streaming_wav_header(rate: int, channels: int, bits: int = 16) -> bytes:
    byte_rate = rate * channels * bits // 8
    block_align = channels * bits // 8
    return (
        b"RIFF"
        + struct.pack("<I", 0xFFFFFFFF)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<IHHIIHH", 16, 1, channels, rate, byte_rate, block_align, bits)
        + b"data"
        + struct.pack("<I", 0xFFFFFFF0)
    )


class AudioCaptureThread(threading.Thread):
    def __init__(
        self,
        on_data: Callable[[bytes], None],
        on_error: Callable[[str], None],
        on_eof: Callable[[], None],
    ):
        super().__init__(daemon=True, name="AudioCapture")
        self._on_data = on_data
        self._on_error = on_error
        self._on_eof = on_eof
        self._stop = threading.Event()
        self.info: Optional[LoopbackInfo] = None

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        p = pyaudio.PyAudio()
        stream = None
        try:
            info = find_default_loopback(p)
            self.info = info
            self._on_data(_streaming_wav_header(info.rate, info.channels))
            stream = p.open(
                format=pyaudio.paInt16,
                channels=info.channels,
                rate=info.rate,
                frames_per_buffer=_FRAMES_PER_BUFFER,
                input=True,
                input_device_index=info.index,
            )
            while not self._stop.is_set():
                pcm = stream.read(_FRAMES_PER_BUFFER, exception_on_overflow=False)
                if pcm:
                    self._on_data(pcm)
        except Exception as exc:
            self._on_error(f"Captura de audio: {exc}")
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            p.terminate()
            self._on_eof()
