# HomePod Streamer

Envía **todo el audio de tu PC con Windows** a un **HomePod** usando **AirPlay 2**
sobre WiFi, con una pequeña app de ventana.

## ⚠️ Por qué NO es por Bluetooth

El HomePod **no admite audio por Bluetooth**. No es una limitación de este programa
ni de las otras herramientas que probaste: **Apple deshabilita a propósito** el audio
Bluetooth (A2DP) en el HomePod. El chip Bluetooth solo se usa para la configuración
inicial por proximidad. **La única forma de enviarle audio es AirPlay sobre WiFi**, y
eso es exactamente lo que hace esta app.

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
cd C:\Users\8200\Documents\HomepodBlue
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

- 🎵 **Música / podcasts:** perfecto.
- 🎬 **Vídeo / juegos:** el audio irá ~2 s por detrás de la imagen. Es del protocolo
  AirPlay, no del programa; no se puede eliminar.

## Solución de problemas

- **No aparece el HomePod:** confirma que está encendido y en la misma red WiFi que el
  PC. Algunos routers aíslan los dispositivos entre sí ("AP isolation"/red de invitados):
  desactívalo.
- **Conecta pero no suena:** asegúrate de que realmente esté reproduciéndose algo en el
  PC (el loopback solo captura cuando hay audio) y sube el volumen del HomePod.
- **Pide emparejamiento / da error de autenticación:** algunos HomePod configurados con
  "Permitir el control" restringido requieren emparejar. Avísame y añadimos el flujo de
  emparejamiento (`atvremote pair`).

## Pila técnica

`pyatv` (AirPlay 2 / RAOP) · `PyAudioWPatch` (WASAPI loopback) · `pycaw` (mute del PC) ·
`customtkinter` (GUI). Todo software libre y gratuito.

## Notas de la versión final

- **Audio sin pérdida (calidad CD):** se envía PCM/WAV en vivo en lugar de MP3, así que
  no hay artefactos de compresión. El límite lo pone AirPlay (44100 Hz / 16-bit).
- **El audio sale solo por el HomePod:** la app mutea la salida del PC mientras transmite
  (casilla activable) y la restaura al detener.
- **Fiabilidad tras varios usos:** se espera el cierre completo de la sesión RAOP
  (`atv.close()` devuelve tareas que hay que aguardar) y se libera el dispositivo de
  captura entre transmisiones, para poder iniciar/detener muchas veces sin que se degrade.
