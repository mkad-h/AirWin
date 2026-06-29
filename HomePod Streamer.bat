@echo off
REM Lanzador de doble clic para HomePod Streamer.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo No se encuentra el entorno virtual .venv
    echo Ejecuta primero:  python -m venv .venv  ^&^&  .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "%~dp0main.py"
