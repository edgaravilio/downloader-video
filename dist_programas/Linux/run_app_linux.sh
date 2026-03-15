#!/bin/bash
echo "--- Video Downloader: Programa para Linux ---"

# 1. Verificar Python y Pip
if ! command -v python3 &> /dev/null
then
    echo "Error: Python3 no está instalado. Instálalo para continuar."
    exit
fi

# 2. Configurar Entorno
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

# 3. Lanzar aplicación
echo "Iniciando interfaz gráfica..."
python3 main.py
