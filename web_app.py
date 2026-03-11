import os
import uuid
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS

from core.utils import validate_url, format_time
from core.downloader import VideoDownloader
from core.queue_manager import QueueManager

app = Flask(__name__)
CORS(app)

downloader = VideoDownloader()
queue_manager = QueueManager(downloader)

# Folder where web downloads will be stored temporally
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_url():
    data = request.json
    url = data.get('url')
    process_playlist = data.get('process_playlist', True)
    
    if not url or not validate_url(url):
        return jsonify({"error": "URL inválida o vacía."}), 400
        
    try:
        info = downloader.extract_info(url, process_playlist=process_playlist)
        if info.get('_type') == 'playlist':
            # Es una playlist
            entries = info.get('entries', [])
            playlist_items = []
            for item in entries:
                if item and item.get('url'):
                    playlist_items.append({
                        'title': item.get('title'),
                        'url': item.get('url'),
                        'duration': format_time(item.get('duration', 0))
                    })
                    
            # Formatos por defecto para la lista entera
            formats = [
                {'id': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'display': 'Video: Mejor calidad (MP4)', 'ext': 'mp4'},
                {'id': 'bestaudio_mp3', 'display': 'Audio: Mejor calidad (MP3)', 'ext': 'mp3'},
                {'id': 'bestaudio_m4a', 'display': 'Audio: Mejor calidad (M4A)', 'ext': 'm4a'}
            ]
            
            # Extraer mejor miniatura si existe
            thumbnail_url = info.get('thumbnail', '')
            if not thumbnail_url and info.get('thumbnails'):
                thumbnail_url = info['thumbnails'][-1].get('url', '')
            if not thumbnail_url and entries:
                first = entries[0]
                thumbnail_url = first.get('thumbnail', '')
                if not thumbnail_url and first.get('thumbnails'):
                    thumbnail_url = first['thumbnails'][-1].get('url', '')
                    
            if not thumbnail_url:
                thumbnail_url = 'https://via.placeholder.com/640x360?text=Lista+de+Reproduccion'
            
            return jsonify({
                "is_playlist": True,
                "title": info.get('title', 'Lista de reproducción desconocida'),
                "channel": info.get('uploader', 'Varios autores'),
                "thumbnail": thumbnail_url,
                "items": playlist_items,
                "formats": formats
            })
        else:
            formats = downloader.get_supported_formats(info)
            return jsonify({
                "is_playlist": False,
                "title": info.get('title', 'Desconocido'),
                "channel": info.get('uploader', 'Desconocido'),
                "duration": format_time(info.get('duration', 0)),
                "thumbnail": info.get('thumbnail', ''),
                "formats": formats
            })
    except Exception as e:
        return jsonify({"error": f"No se pudo analizar el video: {str(e)}"}), 500

@app.route('/api/select_folder', methods=['GET'])
def select_folder():
    # Solo intentar si hay un entorno gráfico (evita errores en Docker/Linux)
    if os.environ.get('DISPLAY') or os.name == 'nt':
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder_path = filedialog.askdirectory(title="Seleccionar carpeta de descarga")
            root.destroy()
            return jsonify({"folder": folder_path})
        except Exception:
            pass
    return jsonify({"folder": None, "web_mode": True})

@app.route('/api/download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    download_folder = data.get('download_folder', DOWNLOAD_DIR)
    title = data.get('title', 'Video Desconocido')
    group_id = data.get('group_id', 'default')
    
    if not url or not format_id:
        return jsonify({"error": "Faltan datos (URL o Formato)."}), 400
        
    download_id = queue_manager.add_item(url, format_id, title, download_folder, group_id)
    return jsonify({"download_id": download_id})

@app.route('/api/status/<download_id>', methods=['GET'])
def get_status(download_id):
    status = queue_manager.get_status(download_id)
    if status.get("error"):
        return jsonify(status), 404
    return jsonify(status)

@app.route('/api/cancel/<download_id>', methods=['POST'])
def cancel_download(download_id):
    queue_manager.cancel_item(download_id)
    return jsonify({"success": True})

@app.route('/api/pause/<download_id>', methods=['POST'])
def pause_download(download_id):
    queue_manager.pause_item(download_id)
    return jsonify({"success": True})

@app.route('/api/resume/<download_id>', methods=['POST'])
def resume_download(download_id):
    queue_manager.resume_item(download_id)
    return jsonify({"success": True})

# --- APIs Globales de Playlist / Cola ---

@app.route('/api/pause_all', methods=['POST'])
def pause_all():
    queue_manager.pause_all()
    return jsonify({"success": True})

@app.route('/api/resume_all', methods=['POST'])
def resume_all():
    queue_manager.resume_all()
    return jsonify({"success": True})

@app.route('/api/cancel_all', methods=['POST'])
def cancel_all():
    queue_manager.cancel_all()
    return jsonify({"success": True})

@app.route('/api/clear_finished', methods=['POST'])
def clear_finished():
    queue_manager.clear_finished_items()
    return jsonify({"success": True})

@app.route('/api/queue_state', methods=['GET'])
def get_queue_state():
    with queue_manager.lock:
        items_dict = {k: v.to_dict() for k, v in queue_manager.items.items()}
        return jsonify({
            "is_global_paused": queue_manager.is_global_paused,
            "items": items_dict
        })

@app.route('/api/cleanup/<download_id>', methods=['POST'])
def cleanup_download(download_id):
    # En esta versión el cleanup lo dejamos como No-Op o lo abstraemos a algo diferente 
    # si usamos la carpeta final directo.
    return jsonify({"success": True})

import mimetypes

@app.route('/api/download_file/<download_id>', methods=['GET'])
@app.route('/api/download_file/<download_id>/<filename>', methods=['GET'])
def download_file(download_id, filename=None):
    state = queue_manager.get_status(download_id)
    if not state or state.get("status") != "completed" or not state.get("file_path"):
        return "Archivo no disponible.", 404
        
    file_path = state["file_path"]
    if os.path.exists(file_path):
        actual_filename = os.path.basename(file_path)
        print(f"DEBUG: Intentando descargar archivo: {actual_filename} (Ruta: {file_path})")
        # Detectar el mimetype real según la extensión
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'video/mp4' # fallback
            
        # Limpiar el nombre para la cabecera standard (solo ASCII)
        import re
        from urllib.parse import quote
        safe_filename = re.sub(r'[^\x00-\x7f]', '', actual_filename).replace('"', '')
        if not safe_filename or safe_filename.isspace():
            safe_filename = "video.mp4"

        # Codificar el nombre real para la cabecera extendida filename*
        encoded_filename = quote(actual_filename)

        response = send_file(
            file_path, 
            as_attachment=True, 
            download_name=actual_filename,
            mimetype=mime_type
        )
        
        # Seteamos la cabecera de forma segura para evitar el UnicodeEncodeError en el servidor
        response.headers["Content-Disposition"] = f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{encoded_filename}"
        return response
    else:
        return "Archivo no encontrado en el disco.", 404

if __name__ == '__main__':
    # Cloud Run usa la variable de entorno PORT
    port = int(os.environ.get("PORT", 8080))
    print(f"Servidor web iniciado. Carpeta descargas: {DOWNLOAD_DIR}")
    # En producción (Cloud Run) se debe escuchar en 0.0.0.0
    app.run(debug=False, host='0.0.0.0', port=port)
