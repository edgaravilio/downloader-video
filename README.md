# 📹 Video Downloader

![Status](https://img.shields.io/badge/Status-Beta-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-orange)
![UI](https://img.shields.io/badge/UI-Glassmorphism-purple)

Una solución integral y multiplataforma diseñada para una experiencia buena de descarga de contenido multimedia. Soporta YouTube, Instagram, Facebook y más de 1000 sitios a través de una interfaz de escritorio nativa o una aplicación web sofisticada.

---

## ✨ Características Destacadas

*   **💎 Estética Premium**: Interfaz moderna basada en *Glassmorphism* (esmerilado) compatible con Desktop y Mobile.
*   **🚀 Potencia Multihilo**: Descargas simultáneas con gestión de cola avanzada (pausar, cancelar, reanudar).
*   **🎬 Calidad Extrema**: Soporte nativo para 4K, HD 1080p, 60 FPS y extracción de audio MP3 de alta fidelidad.
*   **🛠️ Arquitectura Híbrida**: Ejecútalo como programa nativo (.exe/app) o despliégalo en la nube (Cloud Run/Docker).
*   **🕵️ Bypass Inteligente**: Sistema de cascada de clientes (iOS, Android, TV) para evadir bloqueos por bot o integridad.

---

## 📂 Organización del Proyecto

El repositorio está estructurado para facilitar su uso en distintos entornos:

*   **`core/`**: El motor de inteligencia basado en `yt-dlp` y utilitarios.
*   **`ui/`**: Componentes visuales para la aplicación de escritorio nativa.
*   **`templates/`**: Frontend web moderno (HTML/CSS/JS) con diseño glassmorphism.
*   **`RELEASE/`**: Guías rápidas y paquetes listos para usar en cada sistema operativo.
*   **`Dockerfile`**: Configuración lista para desplegar en servicios de contenedores (Cloud).

---

## 🚀 Guía de Inicio Rápido

### 1. Instalación Local
```bash
# Clone el repositorio
git clone https://github.com/tu-usuario/downloader-video.git
cd downloader-video

# Cree un entorno virtual
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows

# Instale dependencias
pip install -r requirements.txt
```

### 2. Ejecutar Versión Escritorio
```bash
python main.py
```

### 3. Ejecutar Versión Web (Local)
```bash
pip install -r requirements-web.txt
python web_app.py
```
> Accede a `http://localhost:8080`

---

---

## 🖥️ Soporte Multiplataforma (Windows, Linux, MacOS)

El proyecto incluye paquetes pre-configurados para que el usuario final no tenga que instalar dependencias complejas si así lo desea.

### 🐧 Linux & 🍎 MacOS
Para sistemas basados en Unix, el proyecto proporciona scripts de ejecución automática (`.sh`).
*   **Requisitos**: Tener Python 3.8+ instalado.
*   **Ejecución**:
    1. Dirígete a `RELEASE/2. Version ESCRITORIO (App Nativa)/[Sistema]/`.
    2. Ejecuta el script: `bash run_app_linux.sh` o `bash run_app_mac.sh`.
    *   *Nota*: El script instalará automáticamente las dependencias en un entorno temporal la primera vez.

### 🪟 Windows
Para Windows, se proporcionan binarios ejecutables `.exe` que no requieren instalación previa.
*   **Descarga**: Debido a que los ejecutables superan el límite de tamaño de archivos de Git (100MB), estos se encuentran alojados en la sección de **[Releases](https://github.com/edgaravilio/downloader-video/releases)** de este repositorio.
*   **Versiones disponibles**:
    1.  **Portable (Web)**: Ideal para uso rápido en el navegador.
    2.  **Nativo (Desktop)**: Aplicación con ventana propia profesional.

---

## 📂 Organización de Lanzamiento (Releases)

Para facilitar la distribución, el repositorio contiene las siguientes carpetas de *scripts*:

*   **`RELEASE/`**: Carpeta principal con instrucciones y scripts de arranque para Linux/Mac.
*   **`dist_portable/`** & **`dist_programas/`**: Contienen los archivos de soporte necesarios para las versiones compiladas.
*   **📦 Binarios (.exe)**: Visita la sección de Releases en GitHub para descargar los archivos listos para ejecutar.

---

## 📦 Compilación a Binarios Nativo

Si desea generar sus propios archivos ejecutables, puede usar los archivos `.spec` incluidos:
*   **Windows**: `pyinstaller VideoDownloader_Desktop_Hybrid.spec`
*   **Linux/Mac**: Los scripts de automatización en `RELEASE/` se encargan de preparar el entorno si prefiere no compilar.

---

## ⚖️ Disclaimer
Esta herramienta ha sido creada únicamente con fines educativos y para uso personal. El autor no se hace responsable del uso indebido de este software ni de las infracciones a los términos de servicio de terceros sitios.

---
*Diseñado por Antigravity AI - [edgaravilio](https://github.com/edgaravilio)*
