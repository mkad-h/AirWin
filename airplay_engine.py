from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Callable, List, Optional

import pyatv
from pyatv.const import Protocol
from pyatv.interface import BaseConfig, MediaMetadata

from audio_capture import AudioCaptureThread
from system_audio import OutputMuter


class AirPlayEngine:
    def __init__(self, log: Callable[[str], None]):
        self._log = log
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()

        self._atv = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._capture: Optional[AudioCaptureThread] = None
        self._stream_task: Optional[asyncio.Task] = None
        self._streaming = False
        self._muter = OutputMuter()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="AirPlayLoop")
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run_loop(self) -> None:
        try:
            import comtypes

            comtypes.CoInitialize()
        except Exception:
            comtypes = None
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        try:
            self._loop.run_forever()
        finally:
            if comtypes is not None:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass

    def shutdown(self) -> None:
        if self._loop is None:
            return
        fut = asyncio.run_coroutine_threadsafe(self._async_stop_stream(), self._loop)
        try:
            fut.result(timeout=8)
        except Exception:
            pass
        self._muter.restore()
        self._loop.call_soon_threadsafe(self._loop.stop)

    def _submit(self, coro) -> Future:
        assert self._loop is not None, "El motor no está iniciado"
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def scan(self, timeout: int = 5) -> Future:
        return self._submit(self._async_scan(timeout))

    def start_stream(
        self, config: BaseConfig, on_state: Callable[[str], None], mute_pc: bool = True
    ) -> Future:
        return self._submit(self._async_start_stream(config, on_state, mute_pc))

    def stop_stream(self) -> Future:
        return self._submit(self._async_stop_stream())

    def set_volume(self, level: float) -> Future:
        return self._submit(self._async_set_volume(level))

    @property
    def is_streaming(self) -> bool:
        return self._streaming

    async def _async_scan(self, timeout: int) -> List[BaseConfig]:
        self._log(f"Buscando dispositivos AirPlay (RAOP) durante {timeout}s…")
        results = await pyatv.scan(self._loop, timeout=timeout, protocol={Protocol.RAOP})
        self._log(f"Encontrados {len(results)} dispositivo(s) que aceptan audio.")
        return results

    async def _async_start_stream(
        self, config: BaseConfig, on_state: Callable[[str], None], mute_pc: bool
    ) -> None:
        await self._teardown()

        self._stream_task = asyncio.current_task()
        self._log(f"Conectando a «{config.name}» ({config.address})…")
        try:
            self._atv = await pyatv.connect(config, self._loop)
        except Exception as exc:
            self._log(f"Error al conectar: {exc}")
            self._stream_task = None
            on_state("error")
            return

        if mute_pc:
            if self._muter.mute():
                self._log("PC silenciado: el audio sale solo por el HomePod.")
            else:
                self._log(
                    "Aviso: no se pudo silenciar el PC automáticamente "
                    "(sonará también por los altavoces)."
                )

        self._reader = asyncio.StreamReader(limit=2**20)
        reader = self._reader

        def push_data(data: bytes) -> None:
            loop = self._loop
            if loop is not None and reader is not None:
                loop.call_soon_threadsafe(reader.feed_data, data)

        def capture_eof() -> None:
            loop = self._loop
            if loop is not None and reader is not None:
                loop.call_soon_threadsafe(_safe_feed_eof, reader)

        self._capture = AudioCaptureThread(
            on_data=push_data, on_error=self._log, on_eof=capture_eof
        )
        self._capture.start()

        metadata = MediaMetadata(title="Audio del PC (Windows)", artist="HomePod Streamer")

        self._streaming = True
        on_state("streaming")
        if self._capture.info:
            self._log(
                f"Capturando sin pérdida: {self._capture.info.name} "
                f"({self._capture.info.rate} Hz, {self._capture.info.channels} ch)"
            )
        self._log("Transmitiendo a AirPlay… (latencia ~2 s por diseño de AirPlay)")

        try:
            await self._atv.stream.stream_file(reader, metadata=metadata)
            self._log("La transmisión finalizó.")
        except asyncio.CancelledError:
            self._log("Transmisión detenida.")
        except Exception as exc:
            self._log(f"Error durante la transmisión: {exc}")
        finally:
            await self._teardown()
            on_state("stopped")

    async def _async_stop_stream(self) -> None:
        task = self._stream_task
        if self._capture is not None:
            self._capture.stop()
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except Exception:
                pass
        else:
            await self._teardown()

    async def _teardown(self) -> None:
        self._streaming = False

        cap = self._capture
        self._capture = None
        if cap is not None:
            cap.stop()
            try:
                await self._loop.run_in_executor(None, cap.join, 3.0)
            except Exception:
                pass

        atv = self._atv
        self._atv = None
        if atv is not None:
            try:
                close_tasks = atv.close()
                if close_tasks:
                    await asyncio.wait(close_tasks, timeout=5)
            except Exception:
                pass

        self._reader = None
        self._stream_task = None
        self._muter.restore()

    async def _async_set_volume(self, level: float) -> None:
        if self._atv is None:
            return
        try:
            await self._atv.audio.set_volume(float(level))
        except Exception as exc:
            self._log(f"No se pudo ajustar el volumen: {exc}")


def _safe_feed_eof(reader: asyncio.StreamReader) -> None:
    try:
        if not reader.at_eof():
            reader.feed_eof()
    except Exception:
        pass
