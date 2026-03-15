#!/bin/bash
echo "--- Video Downloader: Iniciador para Linux ---"

# 1. Verificar Python
if ! command -v python3 &> /dev/null
then
    echo "Error: Python3 no está instalado. Por favor instálalo (sudo apt install python3)."
    exit
fi

# 2. Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "Configurando entorno por primera vez..."
    python3 -m venv .venv
fi

# 3. Activar y actualizar
source .venv/bin/activate
pip install -r requirements-web.txt

# 4. Verificar FFmpeg
if ! command -v ffmpeg &> /dev/null
then
    echo "Aviso: FFmpeg no detectado. Intentando descargar versión portable..."
    mkdir -p bin
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -O bin/ffmpeg.tar.xz
    tar -xf bin/ffmpeg.tar.xz -C bin --strip-components 1
    export PATH="$PWD/bin:$PATH"
fi

# 5. Ejecutar
echo "Iniciando servidor en puerto 8081..."
export PORT=8081
python3 web_app.py
