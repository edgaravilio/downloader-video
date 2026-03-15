#!/bin/bash
echo "--- Video Downloader: Iniciador para MacOS ---"

# 1. Verificar Python
if ! command -v python3 &> /dev/null
then
    echo "Error: Python3 no está instalado."
    exit
fi

# 2. Crear entorno virtual
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements-web.txt

# 3. Verificar FFmpeg (Homebrew es lo estándar en Mac)
if ! command -v ffmpeg &> /dev/null
then
    echo "FFmpeg no detectado. Si tienes Homebrew usa: 'brew install ffmpeg'"
    echo "O descarga el binario desde: https://evermeet.cx/ffmpeg/"
fi

# 4. Ejecutar
export PORT=8081
python3 web_app.py
