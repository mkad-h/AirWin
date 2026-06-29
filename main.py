from __future__ import annotations

import queue
from typing import Dict, List

import customtkinter as ctk
from pyatv.interface import BaseConfig

from airplay_engine import AirPlayEngine

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HomePod Streamer — Audio de Windows por AirPlay")
        self.geometry("640x560")
        self.minsize(560, 480)

        self._devices: Dict[str, BaseConfig] = {}
        self._log_queue: "queue.Queue[str]" = queue.Queue()

        self.engine = AirPlayEngine(log=self._enqueue_log)
        self.engine.start()

        self._build_ui()
        self._poll_log_queue()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.after(400, self._scan)

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 8}

        header = ctk.CTkLabel(
            self,
            text="HomePod Streamer",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        header.pack(anchor="w", **pad)

        subtitle = ctk.CTkLabel(
            self,
            text="Todo el audio del PC → HomePod por AirPlay 2 (misma red WiFi)",
            text_color=("gray40", "gray70"),
        )
        subtitle.pack(anchor="w", padx=16)

        dev_frame = ctk.CTkFrame(self)
        dev_frame.pack(fill="x", **pad)

        ctk.CTkLabel(dev_frame, text="Dispositivo:").pack(side="left", padx=(12, 8), pady=12)
        self.device_menu = ctk.CTkOptionMenu(
            dev_frame, values=["(sin dispositivos)"], width=300
        )
        self.device_menu.pack(side="left", pady=12)
        self.scan_btn = ctk.CTkButton(
            dev_frame, text="🔄 Buscar", width=100, command=self._scan
        )
        self.scan_btn.pack(side="left", padx=12, pady=12)

        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.pack(fill="x", **pad)

        self.start_btn = ctk.CTkButton(
            ctrl_frame, text="▶  Iniciar transmisión", command=self._start
        )
        self.start_btn.pack(side="left", padx=12, pady=12)

        self.stop_btn = ctk.CTkButton(
            ctrl_frame,
            text="■  Detener",
            command=self._stop,
            state="disabled",
            fg_color="#b03030",
            hover_color="#8a2525",
        )
        self.stop_btn.pack(side="left", padx=4, pady=12)

        self.mute_var = ctk.BooleanVar(value=True)
        self.mute_check = ctk.CTkCheckBox(
            ctrl_frame,
            text="Silenciar PC (solo HomePod)",
            variable=self.mute_var,
        )
        self.mute_check.pack(side="left", padx=12, pady=12)

        vol_frame = ctk.CTkFrame(self)
        vol_frame.pack(fill="x", **pad)

        ctk.CTkLabel(vol_frame, text="Volumen HomePod:").pack(side="left", padx=(12, 8), pady=12)
        self.vol_slider = ctk.CTkSlider(
            vol_frame, from_=0, to=100, number_of_steps=100, command=self._on_volume
        )
        self.vol_slider.set(40)
        self.vol_slider.pack(side="left", fill="x", expand=True, padx=8, pady=12)
        self.vol_label = ctk.CTkLabel(vol_frame, text="40%", width=44)
        self.vol_label.pack(side="left", padx=(0, 12), pady=12)

        self.status_label = ctk.CTkLabel(
            self, text="● Listo", text_color=("gray30", "gray70")
        )
        self.status_label.pack(anchor="w", padx=16)

        self.log_box = ctk.CTkTextbox(self, height=180)
        self.log_box.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        self.log_box.configure(state="disabled")

    def _enqueue_log(self, msg: str) -> None:
        self._log_queue.put(msg)

    def _poll_log_queue(self) -> None:
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self.log_box.configure(state="normal")
                self.log_box.insert("end", msg + "\n")
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(120, self._poll_log_queue)

    def _set_status(self, text: str, color) -> None:
        self.status_label.configure(text=text, text_color=color)

    def _scan(self) -> None:
        self.scan_btn.configure(state="disabled", text="Buscando…")
        self._set_status("● Buscando dispositivos…", "#d08a00")
        fut = self.engine.scan(timeout=5)
        fut.add_done_callback(lambda f: self.after(0, self._on_scan_done, f))

    def _on_scan_done(self, fut) -> None:
        self.scan_btn.configure(state="normal", text="🔄 Buscar")
        try:
            results: List[BaseConfig] = fut.result()
        except Exception as exc:
            self._enqueue_log(f"Error al escanear: {exc}")
            self._set_status("● Error al escanear", "#b03030")
            return

        self._devices = {}
        names: List[str] = []
        for conf in results:
            label = f"{conf.name}  ({conf.address})"
            self._devices[label] = conf
            names.append(label)

        if names:
            self.device_menu.configure(values=names)
            self.device_menu.set(names[0])
            self._set_status(f"● {len(names)} dispositivo(s) disponible(s)", "#2a8a2a")
        else:
            self.device_menu.configure(values=["(sin dispositivos)"])
            self.device_menu.set("(sin dispositivos)")
            self._set_status("● No se encontró ningún HomePod/AirPlay", "#b03030")
            self._enqueue_log(
                "No apareció ningún dispositivo. Revisa que el HomePod esté encendido "
                "y que el PC esté en la MISMA red WiFi (no en una VLAN de invitados)."
            )

    def _start(self) -> None:
        label = self.device_menu.get()
        conf = self._devices.get(label)
        if conf is None:
            self._enqueue_log("Selecciona primero un dispositivo válido.")
            return
        self.start_btn.configure(state="disabled")
        self.scan_btn.configure(state="disabled")
        self._set_status("● Conectando…", "#d08a00")
        self.engine.start_stream(
            conf, on_state=self._on_stream_state, mute_pc=bool(self.mute_var.get())
        )

    def _on_stream_state(self, state: str) -> None:
        self.after(0, self._apply_stream_state, state)

    def _apply_stream_state(self, state: str) -> None:
        if state == "streaming":
            self.stop_btn.configure(state="normal")
            self.start_btn.configure(state="disabled")
            self.scan_btn.configure(state="disabled")
            self._set_status("● Transmitiendo  ♪", "#2a8a2a")
            self._on_volume(self.vol_slider.get())
        elif state in ("stopped", "error"):
            self.stop_btn.configure(state="disabled")
            self.start_btn.configure(state="normal")
            self.scan_btn.configure(state="normal")
            color = "#b03030" if state == "error" else ("gray30", "gray70")
            self._set_status("● Error" if state == "error" else "● Detenido", color)

    def _stop(self) -> None:
        self.stop_btn.configure(state="disabled")
        self._set_status("● Deteniendo…", "#d08a00")
        self.engine.stop_stream()

    def _on_volume(self, value) -> None:
        pct = int(float(value))
        self.vol_label.configure(text=f"{pct}%")
        if self.engine.is_streaming:
            self.engine.set_volume(pct)

    def _on_close(self) -> None:
        try:
            self.engine.shutdown()
        except Exception:
            pass
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
