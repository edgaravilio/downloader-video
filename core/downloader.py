import os
import sys
import re
from typing import Callable, Dict, Any, Optional
import yt_dlp
import tempfile
import concurrent.futures

class VideoDownloader:
    """
    Clase encargada de manejar la lógica de extracción de información y
    descarga de videos utilizando yt-dlp de forma asíncrona.
    Soporta cola de descargas y cancelación.
    """
    def __init__(self, max_concurrent=3):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent)
        self.canceled_downloads = set()
        self.paused_downloads = set()
        self.cookie_file = self._prepare_cookies()

    def _prepare_cookies(self) -> Optional[str]:
        """
        Lee cookies desde la variable de entorno YOUTUBE_COOKIES y las guarda en un archivo temporal.
        """
        cookies_content = os.environ.get('YOUTUBE_COOKIES')
        if not cookies_content:
            return None
            
        try:
            # Creamos un archivo temporal que persista durante la ejecución de la app
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            tmp.write(cookies_content)
            tmp.close()
            return tmp.name
        except Exception as e:
            print(f"Error preparando cookies: {e}")
            return None

    def extract_info(self, url: str, process_playlist: bool = True) -> Dict[str, Any]:
        """
        Extrae información del video (título, formatos, duración, etc.) sin descargarlo.
        Lanza excepción si hay error o la URL es inválida para yt-dlp.
        
        Args:
            url (str): URL del video.
            process_playlist (bool): Determina si se extre la información plana de la lista o si se restringe puramente al video que pertenece la URL.
            
        Returns:
            dict: Diccionario principal devuelto por yt_dlp.
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        if self.cookie_file:
            ydl_opts['cookiefile'] = self.cookie_file
        
        if process_playlist:
            ydl_opts['extract_flat'] = 'in_playlist'
        else:
            ydl_opts['noplaylist'] = True
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info

    def get_supported_formats(self, info: Dict[str, Any]) -> list:
        """
        Filtra y devuelve una lista de formatos mp4 disponibles.
        """
        formats = info.get('formats', [])
        # Filtrar solo formatos de video (que tengan tanto video) y preferiblemente mp4 u otra extensión común
        valid_formats = []
        for f in formats:
             if f.get('vcodec') != 'none': # Tiene video
                 # Extraemos etiqueta de formato y nota (ej. 1080p, 720p)
                 format_note = f.get('format_note', 'Unknown')
                 ext = f.get('ext', 'mp4')
                 fps = f.get('fps', '')
                 format_id = f.get('format_id')
                 
                 # Evitar duplicados simples guiandonos por height si es posible
                 h = f.get('height')
                 if h:
                     # Guardar info legible para UI y el id para yt_dlp
                     display_str = f"{h}p ({ext})" if not fps else f"{h}p {fps}fps ({ext})"
                     # Combinamos con bestaudio para asegurar que tenga sonido incluso en 1080p+
                     combined_id = f"{format_id}+bestaudio[ext=m4a]/bestaudio/best"
                     valid_formats.append({
                         'id': combined_id,
                         'display': display_str,
                         'ext': ext,
                         'height': h
                     })
                     
        # Ordenamos por resolución (height) descendente
        valid_formats.sort(key=lambda x: x['height'], reverse=True)
        
        # Eliminar display strings duplicados, dejando la mejor opción
        unique_formats = []
        seen = set()
        for f in valid_formats:
            if f['display'] not in seen:
                seen.add(f['display'])
                unique_formats.append(f)
                
        # Always add a 'Best audio + video' default format at the top
        unique_formats.insert(0, {'id': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'display': 'Video: Mejor calidad (MP4)', 'ext': 'mp4'})
        # Add audio only options
        unique_formats.insert(1, {'id': 'bestaudio_mp3', 'display': 'Audio: Mejor calidad (MP3)', 'ext': 'mp3'})
        unique_formats.insert(2, {'id': 'bestaudio_m4a', 'display': 'Audio: Mejor calidad (M4A)', 'ext': 'm4a'})
        return unique_formats

    def download_video_async(
        self, 
        url: str, 
        format_id: str, 
        dest_folder: str, 
        on_progress: Callable[[Dict[str, Any]], None],
        on_complete: Callable[[str], None],
        on_error: Callable[[str], None],
        download_id: str = None
    ):
        """
        Inicia la descarga poniéndola en la cola del executor.
        
        Args:
            url (str): URL del video
            format_id (str): ID de yt_dlp o 'bestvideo+bestaudio/best'
            dest_folder (str): Carpeta donde se guardará (debe existir o ser creada antes)
            on_progress (función): Callback a llamar en cada actualización. Firma: (dict_datos)
            on_complete (función): Callback a llamar al finalizar exitosamente. Firma: (ruta_final)
            on_error (función): Callback a llamar en caso de error. Firma: (mensaje_error)
            download_id (str): Identificador único para poder cancelar.
        """

        def download_thread():
            try:
                def progress_hook(d):
                    if download_id and download_id in self.canceled_downloads:
                        raise ValueError("Descarga cancelada por el usuario")
                    if download_id and download_id in self.paused_downloads:
                        raise ValueError("Descarga pausada")
                        
                    if d['status'] == 'downloading':
                        # Porcentaje
                        percent_str = d.get('_percent_str', '0%')
                        # Limpiar códigos ANSI del string (yt-dlp a veces los incluye)
                        percent_str = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).strip()
                        try:
                            percent = float(percent_str.replace('%', '')) / 100.0
                        except ValueError:
                            percent = 0.0
                            
                        # Velocidad y ETA
                        speed = d.get('_speed_str', 'N/A')
                        speed = re.sub(r'\x1b\[[0-9;]*m', '', speed).strip()
                        
                        eta = d.get('_eta_str', 'N/A')
                        eta = re.sub(r'\x1b\[[0-9;]*m', '', eta).strip()
                        
                        status_msg = f"Descargando: {percent_str} (Velocidad: {speed} | Faltan: {eta})"
                        on_progress({
                            'status': 'downloading',
                            'percent': percent,
                            'speed': speed,
                            'eta': eta,
                            'message': status_msg
                        })
                        
                    elif d['status'] == 'finished':
                        on_progress({
                            'status': 'processing',
                            'percent': 1.0,
                            'speed': '',
                            'eta': '',
                            'message': "Procesando archivo final..."
                        })

                # Determinar ruta de ffmpeg
                ffmpeg_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin')
                if getattr(sys, 'frozen', False):
                    ffmpeg_dir = os.path.join(sys._MEIPASS, 'bin')

                opts = {
                    'format': format_id,
                    'outtmpl': f"{dest_folder}/%(title)s.%(ext)s",
                    'progress_hooks': [progress_hook],
                    'quiet': True,
                    'no_warnings': True,
                    'noplaylist': True,
                    'ffmpeg_location': ffmpeg_dir,
                }
                
                if self.cookie_file:
                    opts['cookiefile'] = self.cookie_file
                
                # Caso especial para "Mejor Calidad (MP4)"
                if format_id == 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best':
                    opts['merge_output_format'] = 'mp4'
                    # Asegurar que intente bajar la maxima calidad de video (vp9 o h264 superior a 1080p si existe) y la una como mp4
                    opts['format'] = 'bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
                    
                # Extras generales para otros formatos de video que requieran merge
                elif '+' in format_id:
                     opts['merge_output_format'] = 'mp4'
                
                # Handling Audio-only formats via postprocessors
                if format_id == 'bestaudio_mp3':
                    opts['format'] = 'bestaudio/best'
                    opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '320', # Forzamos a 320kbps (antes estaba en 192)
                    }]
                elif format_id == 'bestaudio_m4a':
                    opts['format'] = 'bestaudio/best'
                    opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'm4a',
                        'preferredquality': '0', # máxima de origen
                    }]
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    # El nombre real puede cambiar por el outtmpl, usamos prepare_filename para saber la ruta real
                    final_path = ydl.prepare_filename(info)
                    
                    # Si hubo merge, la extencion cambia
                    if opts.get('merge_output_format'):
                        base, _ = os.path.splitext(final_path)
                        final_path = f"{base}.{opts['merge_output_format']}"
                    elif format_id in ['bestaudio_mp3', 'bestaudio_m4a']:
                        base, _ = os.path.splitext(final_path)
                        final_path = f"{base}.{opts['postprocessors'][0]['preferredcodec']}"

                on_complete(final_path)
                
            except Exception as e:
                # Filtrar el mensaje si es cancelación o pausa nuestra
                msg = str(e)
                if hasattr(self, 'canceled_downloads') and download_id in self.canceled_downloads:
                    msg = "Descarga cancelada."
                    self.canceled_downloads.remove(download_id)
                elif hasattr(self, 'paused_downloads') and download_id in self.paused_downloads:
                    msg = "Descarga pausada"
                    self.paused_downloads.remove(download_id)
                on_error(msg)

        self.executor.submit(download_thread)

    def cancel_download(self, download_id: str):
        if download_id:
            self.canceled_downloads.add(download_id)

    def pause_download(self, download_id: str):
        if download_id:
            self.paused_downloads.add(download_id)

