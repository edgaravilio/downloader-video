# Video Downloader 📹

Un programa de escritorio simple y funcional para descargar videos desde YouTube (y otros sitios soportados por `yt-dlp`) para uso personal. Cuenta con una interfaz moderna y atractiva construida en `CustomTkinter`.

## Características ✨

- Interfaz gráfica moderna (Dark Mode por defecto).
- Análisis de URL (obtiene título, miniatura y duración antes de descargar).
- Selector de calidad visual clara.
- Barra de progreso en tiempo real con status de velocidad y tiempo restante.
- Arquitectura limpia y modular.

## Requisitos Previos 🛠️

- Python 3.8+ instalado.
download.html- Opcional pero recomendado para mejor calidad de video y audio combinados: [FFmpeg](https://ffmpeg.org/) instalado y agregado al PATH del sistema.

## Instrucciones de Instalación y Ejecución 🚀

1. Clona o descarga este repositorio y abre una terminal en la carpeta raíz (`Downloader video`).
2. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta la aplicación de escritorio:
   ```bash
   python main.py
   ```

## Versión Web 🌐

Si prefieres usar la herramienta desde tu navegador sin instalar la interfaz gráfica pesada de escritorio, puedes lanzar el servidor web incluido (Flask).

1. Instala los requerimientos web además de los estándar:
   ```bash
   pip install -r requirements-web.txt
   ```
2. Inicia el servidor de backend local:
   ```bash
   python web_app.py
   ```
3. Abre tu navegador y dirígete a `http://127.0.0.getInstance()` (habitualmente `http://127.0.0.1:5000` o `http://localhost:5000`).
4. Desde allí podrás pegar la URL y el video se descargará en la carpeta `downloads/` dentro del proyecto. Opcionalmente podrás presionar "Guardar Archivo en PC" para descargarlo a través del navegador.

## Compilar a Ejecutable (.exe) 📦

Puedes empaquetar la aplicación en un solo archivo `.exe` para Windows y así no depender de ejecutar comandos en Python.

1. Asegúrate de instalar `pyinstaller`:
   ```bash
   pip install pyinstaller
   ```
2. Ejecuta el siguiente comando en la raíz del proyecto para crear el ejecutable:
   ```bash
   pyinstaller --noconsole --onefile main.py
   ```
   > **Nota:** Usamos `--noconsole` para evitar que aparezca la ventana negra de MS-DOS detrás de la interfaz gráfica, y `--onefile` para generar todo en un único `.exe`.
3. El archivo resultante `main.exe` lo encontrarás dentro de la carpeta `dist/`. ¡Ya puedes llevarlo a donde quieras!

## Estructura de Módulos 📂

El código está estructurado modularmente para priorizar estabilidad y mantenimiento:

- **`core/utils.py`:** Contiene funciones utilitarias y de validación puras (formateo de tiempo/tamaño, descarga en memoria de la miniatura, validación de URL con RegEx). Se encarga de procesos sin interfaz ni conexión a *yt-dlp*.
- **`core/downloader.py`:** Aísla toda la lógica de obtención de datos y descarga. Se apoya poderosamente en la librería `yt-dlp`. Maneja el threading de las descargas y el uso de *Callbacks* (`on_progress`, `on_complete`, `on_error`) para comunicarse de vuelta con la capa visual.
- **`ui/app.py`:** La capa frontal construida sobre `customtkinter`. Crea ventanas, botones y eventos estéticos. Nunca realiza llamadas de red pesadas en el thread principal para evitar *freezeo* de la pantalla.
- **`main.py`:** El clásico entry-point para arrancar el programa.
- **`requirements.txt`:** Lista exacta de las librerías necesarias con las que fue probado.

---
*Disclaimer: Esta herramienta está pensada estricta y únicamente para uso personal.*
