#!/bin/bash
echo "--- Video Downloader: Programa para MacOS ---"

# 1. Verificar Python
if ! command -v python3 &> /dev/null
then
    echo "Error: Python3 no está instalado."
    exit
fi

# 2. Configurar Entorno
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements-web.txt
pip install pywebview

# 3. Lanzar
python3 desktop_app.py
