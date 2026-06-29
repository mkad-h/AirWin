from __future__ import annotations

from typing import Optional

try:
    from pycaw.pycaw import AudioUtilities

    _PYCAW_OK = True
except Exception:
    _PYCAW_OK = False


class OutputMuter:
    def __init__(self):
        self._endpoint = None
        self._original_mute: Optional[int] = None

    @property
    def available(self) -> bool:
        return _PYCAW_OK

    def mute(self) -> bool:
        if not _PYCAW_OK:
            return False
        try:
            self._endpoint = AudioUtilities.GetSpeakers().EndpointVolume
            self._original_mute = self._endpoint.GetMute()
            self._endpoint.SetMute(1, None)
            return True
        except Exception:
            self._endpoint = None
            self._original_mute = None
            return False

    def restore(self) -> None:
        if self._endpoint is not None and self._original_mute is not None:
            try:
                self._endpoint.SetMute(self._original_mute, None)
            except Exception:
                pass
        self._endpoint = None
        self._original_mute = None
