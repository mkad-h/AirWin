# AirWin Streamer

Envía **todo el audio de tu PC con Windows** a un **HomePod** usando **AirPlay 2**
sobre WiFi, con una pequeña app de ventana.

## Requisitos

- Windows 10/11
- El PC y el HomePod en la **misma red WiFi** (no una red de invitados ni VLAN aislada)
- Python 3.10+ (probado con 3.12)

## Cómo funciona

```
Altavoz por defecto de Windows
      │ (WASAPI loopback — sin "Stereo Mix" ni cables virtuales)
   PyAudioWPatch  ──PCM sin pérdida──▶  WAV de streaming en vivo
                                    │
                              asyncio.StreamReader
                                    │
                        pyatv  ──AirPlay 2 / RAOP (ALAC)──▶  HomePod
```

El audio viaja **sin pérdida** de extremo a extremo: se captura como PCM, se envía como
WAV en vivo y pyatv lo reempaqueta a ALAC (sin pérdida) hacia el HomePod. El techo de
calidad es el del propio AirPlay: **calidad CD (44100 Hz / 16-bit)**.

- `audio_capture.py` — captura el audio del sistema como PCM/WAV sin pérdida.
- `airplay_engine.py` — descubre dispositivos y transmite con `pyatv`.
- `system_audio.py` — mutea/restaura la salida del PC.
- `main.py` — la interfaz gráfica.

## Instalación

```powershell
cd C:\..\AirWin
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

## Uso

Doble clic en **`HomePod Streamer.bat`**, o bien:

```powershell
.\.venv\Scripts\python main.py
```

1. La app escanea automáticamente al abrir. Pulsa **🔄 Buscar** si tu HomePod no aparece.
2. Elige el HomePod en la lista.
3. Deja marcada **«Silenciar PC (solo HomePod)»** para que el audio salga *únicamente*
   por el HomePod y no por los altavoces del PC. Si la desmarcas, sonará por ambos.
4. Pulsa **▶ Iniciar transmisión**. Ahora todo lo que suene en el PC irá al HomePod.
5. Ajusta el **volumen** del HomePod con el deslizador.
6. **■ Detener** para terminar (restaura automáticamente el sonido del PC).

### ¿Cómo suena solo por el HomePod?
Windows captura el audio en el "loopback" *antes* de aplicar el mute del dispositivo,
así que la app puede **mutear tus altavoces** mientras el HomePod sigue recibiendo el
audio completo. Al detener (o cerrar la app) se restaura el estado de mute original.

## Latencia (importante)

AirPlay añade **~2 segundos** de retardo por diseño (Apple bufferiza para sincronizar
multi-room). Resultado:

-  **Música / podcasts:** perfecto.
-  **Vídeo / juegos:** el audio irá ~2 s por detrás de la imagen. Es del protocolo
  AirPlay, no del programa; no se puede eliminar.


## Pila técnica

`pyatv` (AirPlay 2 / RAOP) · `PyAudioWPatch` (WASAPI loopback) · `pycaw` (mute del PC) ·
`customtkinter` (GUI). Todo software libre y gratuito.
