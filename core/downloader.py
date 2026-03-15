import os
import sys
import shutil
import re
import tempfile
import concurrent.futures
import copy
import base64
import urllib.request
from typing import Callable, Dict, Any, Optional

import yt_dlp

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
        self.ffmpeg_path = self._get_ffmpeg_path()
        self.cookie_file = self._prepare_cookies()

    def _get_ffmpeg_path(self) -> str:
        """Detecta la ubicación de ffmpeg de forma dinámica y portable."""
        # 1. Buscar en sys._MEIPASS (PyInstaller)
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
            bundled_ffmpeg = os.path.join(base_dir, "bin", "ffmpeg.exe" if os.name == 'nt' else "ffmpeg")
            if os.path.exists(bundled_ffmpeg):
                return bundled_ffmpeg

        # 2. Buscar en directorio 'bin' local
        local_bin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
        local_ffmpeg = os.path.join(local_bin, "ffmpeg.exe" if os.name == 'nt' else "ffmpeg")
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg

        # 3. Buscar en el PATH del sistema
        path = shutil.which("ffmpeg")
        if path:
            return path
            
        # 4. Rutas comunes en Windows
        if os.name == 'nt':
            nt_paths = [
                r"C:\Users\Edgar\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            ]
            for p in nt_paths:
                if os.path.exists(p):
                    return p
                    
        return 'ffmpeg'

    def _prepare_cookies(self) -> Optional[str]:
        """
        Lee cookies desde la variable de entorno YOUTUBE_COOKIES y las guarda en un archivo temporal.
        """
        cookies_content = os.environ.get('YOUTUBE_COOKIES')
        if not cookies_content:
            print("[VideoDownloader] No se encontró YOUTUBE_COOKIES en el entorno.")
            return None
            
        try:
            # Intentar decodificar si parece base64, si no, tratar como texto plano
            try:
                # Si no empieza por el encabezado Netscape, intentamos Base64
                if not cookies_content.startswith('# Netscape'):
                    decoded = base64.b64decode(cookies_content).decode('utf-8')
                    if '# Netscape' in decoded:
                        cookies_content = decoded.strip()
                        print("[VideoDownloader] Cookies decodificadas desde Base64 con éxito.")
            except Exception:
                pass

            # Robustecimiento: yt-dlp requiere formato Netscape estricto (tabs).
            # Si el env viene de consolas, los tabs pueden haberse convertido en espacios.
            # Vamos a reconstruir las líneas si parecen ser de cookies.
            lines = cookies_content.split('\n')
            final_lines = []
            for line in lines:
                if line.startswith('#') or not line.strip():
                    final_lines.append(line)
                    continue
                
                parts = re.split(r'\s+', line.strip())
                if len(parts) >= 7:
                    # Re-ensamblar con tabs exactos (Dominio, flag1, path, flag2, expiry, name, value)
                    # Tomamos el valor como "todo lo que queda" por si tiene espacios
                    val = " ".join(parts[6:])
                    clean_line = "\t".join(parts[:6]) + "\t" + val
                    final_lines.append(clean_line)
                else:
                    final_lines.append(line)
            
            cookies_content = '\n'.join(final_lines)
            if not cookies_content.endswith('\n'):
                cookies_content += '\n'

            # Creamos un archivo temporal que persista durante la ejecución de la app
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            tmp.write(cookies_content)
            tmp.close()
            print(f"[VideoDownloader] Cookies guardadas en: {tmp.name} (Tamaño: {len(cookies_content)} bytes)")
            return tmp.name
        except Exception as e:
            print(f"[VideoDownloader] Error preparando cookies: {e}")
            return None

    def extract_info(self, url: str, process_playlist: bool = True) -> Dict[str, Any]:
        """
        Extrae información del video (título, formatos, duración, etc.) sin descargarlo.
        Lanza excepción si hay error o la URL es inválida para yt-dlp.
        """
        # ----------------------------
        # ----------------------------
        # --- BYPASS DE INTEGRIDAD (Nativo vía /app/ytdlp_plugins) ---
        
        # Usar un User-Agent de iPhone para que coincida con el cliente 'ios' predominante
        user_agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        
        # Detectar plataforma para ajustar cabeceras
        is_youtube = any(x in url.lower() for x in ['youtube.com', 'youtu.be'])
        is_instagram = any(x in url.lower() for x in ['instagram.com', 'instagr.am'])
        
        ydl_opts = {
            'quiet': False,
            'verbose': True,
            'no_warnings': True,
            'format': 'all',
            'skip_download': True,
            'nocheckcertificate': True,
            'cachedir': False,
            'geo_bypass': True,
            'user_agent': user_agent,
            'http_headers': {
                'Referer': 'https://www.youtube.com/' if is_youtube else ('https://www.instagram.com/' if is_instagram else 'https://www.google.com/'),
                'Accept-Language': 'en-GB,en-US,en;q=0.9',
            },
            'extractor_args': {
                'youtube': {
                    # android_vr es el único cliente que: no necesita JS signature,
                    # no necesita PO Token, y devuelve todos los formatos HD disponibles.
                    'player_client': ['android_vr', 'mweb'],
                }
            },
            'youtube_include_dash_manifest': True,
            'youtube_include_hls_manifest': True,
            'force_ipv4': True,
            'plugin_dirs': [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ytdlp_plugins')],
            'proxy': os.environ.get('YOUTUBE_PROXY'),
            'compat_opts': ['no-youtube-unavailable-videos', 'no-youtube-channel-redirect'],
        }
        
        print(f"[VideoDownloader] yt-dlp version: {yt_dlp.version.__version__}")
        if self.cookie_file:
            print("[VideoDownloader] Sesi\u00f3n Autenticada (Cookies): Activando bypass prioritario de cuenta.")
            ydl_opts['cookiefile'] = self.cookie_file
            # Con cookies, android_vr sigue siendo prioritario pero a\u00f1adimos android como respaldo
            ydl_opts['extractor_args']['youtube']['player_client'] = ['android_vr', 'ios', 'android']
        else:
            print("[VideoDownloader] Sesión Anónima: Usando clientes nativos de bypass.")
        
        po_token = os.environ.get('YT_DLP_PO_TOKEN') or os.environ.get('YOUTUBE_PO_TOKEN')
        visitor_data = os.environ.get('YOUTUBE_VISITOR_DATA')
        use_oauth2 = os.environ.get('YOUTUBE_OAUTH2', '').lower() == 'true'

        # Opción A: Generador Dinámico Local (bgutil-pot) - PRIORIDAD MÁXIMA
        if 'youtubepot-bgutilhttp' not in ydl_opts['extractor_args']:
            ydl_opts['extractor_args']['youtubepot-bgutilhttp'] = {}
        ydl_opts['extractor_args']['youtubepot-bgutilhttp']['base_url'] = 'http://127.0.0.1:4416'
        
        # Activar el uso del plugin en el extractor de youtube
        if 'youtube' not in ydl_opts['extractor_args']:
            ydl_opts['extractor_args']['youtube'] = {}
            
        ydl_opts['ffmpeg_location'] = self.ffmpeg_path
        
        bgutil_available = False
        try:
            urllib.request.urlopen('http://127.0.0.1:4416', timeout=1)
            bgutil_available = True
        except:
            pass

        if bgutil_available:
            ydl_opts['extractor_args']['youtube']['po_token'] = 'web+http://localhost:4416'
            ydl_opts['extractor_args']['youtube']['player_client'] = ['android', 'ios', 'mweb']
            print("[VideoDownloader] bgutil-pot disponible, usando clientes con PO Token.")
        elif po_token and visitor_data and po_token != 'potoken':
            print("[VideoDownloader] Usando PO Token estático de entorno.")
            ydl_opts['extractor_args']['youtube']['po_token'] = po_token
            ydl_opts['extractor_args']['youtube']['visitor_data'] = visitor_data
            ydl_opts['extractor_args']['youtube']['player_client'] = ['ios', 'android', 'android_vr']
        else:
            # En Cloud Run sin PO Token, intentamos ios primero que a veces da más que android_vr
            print("[VideoDownloader] bgutil-pot NO disponible, usando android_vr + ios.")
            ydl_opts['extractor_args']['youtube']['player_client'] = ['android_vr', 'ios']
        
        # Inyectar también los estáticos si existen como respaldo secundario
        if po_token and visitor_data and po_token != 'potoken':
            ydl_opts['extractor_args']['youtube']['visitor_data'] = visitor_data
        
        if use_oauth2:
            print("[VideoDownloader] OAuth2 activado. Iniciando flujo de sesión segura.")
            ydl_opts['username'] = 'oauth2'
            ydl_opts['password'] = ''
            # Permitir cache para persistir el token si es posible
            ydl_opts['cachedir'] = '/tmp/yt_dlp_cache'
            if not os.path.exists('/tmp/yt_dlp_cache'):
                os.makedirs('/tmp/yt_dlp_cache')
        if process_playlist:
            ydl_opts['extract_flat'] = 'in_playlist'
        else:
            ydl_opts['noplaylist'] = True
            
        print(f"[VideoDownloader] Analizando URL con Cascada de Inteligencia (PO Token: {'Sí' if po_token else 'No'})")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            err_msg = str(e).lower()
            if any(x in err_msg for x in ["bot", "sign in", "player response", "unplayable", "page needs to be reloaded", "format is not available"]):
                print(f"[VideoDownloader] Error de acceso ({err_msg}). Iniciando Cascada de Rescate Individual...")
                
                fallbacks = [
                    {'name': 'iOS (No Webpage)', 'client': ['ios'], 'skip': ['webpage'], 'use_cookies': True},
                    {'name': 'Web Remix (Music)', 'client': ['web_remix'], 'skip': ['webpage'], 'use_cookies': True},
                    {'name': 'Smart TV (Native)', 'client': ['tv'], 'skip': [], 'use_cookies': True},
                    {'name': 'mWeb (Safari)', 'client': ['mweb'], 'skip': ['webpage'], 'use_cookies': True},
                    {'name': 'Android TestSuite (Clean)', 'client': ['android_testsuite'], 'skip': ['webpage'], 'use_cookies': False},
                    {'name': 'Android Embedded (Bypass)', 'client': ['android_embedded'], 'skip': ['webpage'], 'use_cookies': True},
                    {'name': 'Web Desktop (Full)', 'client': ['web'], 'skip': [], 'use_cookies': True},
                    {'name': 'iOS Mobile (No Cookies)', 'client': ['ios'], 'skip': ['webpage'], 'use_cookies': False},
                ]
                
                for fb in fallbacks:
                    print(f"[VideoDownloader] Reintento Fallback: {fb['name']} (Cliente: {fb['client']})...")
                    fb_opts = copy.deepcopy(ydl_opts)
                    
                    # Asegurar inyección de PO Token en cada fallback (Estático o Dinámico)
                    if 'youtube' not in fb_opts['extractor_args']:
                        fb_opts['extractor_args']['youtube'] = {}
                        
                    if po_token and visitor_data:
                        fb_opts['extractor_args']['youtube']['po_token'] = po_token
                        fb_opts['extractor_args']['youtube']['visitor_data'] = visitor_data
                    else:
                        # Respaldo dinámico local
                        fb_opts['extractor_args']['youtube']['po_token'] = 'web+http://localhost:4416'
                        fb_opts['extractor_args']['youtube']['player_client'] = fb['client']
                    fb_opts['extractor_args']['youtube']['player_skip'] = fb['skip']
                    
                    if not fb['use_cookies'] and 'cookiefile' in fb_opts:
                        del fb_opts['cookiefile']
                    
                    fb_opts['check_formats'] = False  # No verificar formatos durante el rescate de info
                    fb_opts['format'] = 'all'         # Asegurar captura de todo lo disponible
                    
                    try:
                        with yt_dlp.YoutubeDL(fb_opts) as ydl_fb:
                            return ydl_fb.extract_info(url, download=False)
                    except Exception as fe:
                        print(f"[VideoDownloader] {fb['name']} falló: {str(fe)[:120]}")
                        continue
                
                # Si llegamos aquí nada funcionó, relanzamos el original
                raise e
            else:
                raise e

    def get_supported_formats(self, info: Dict[str, Any]) -> list:
        """
        Filtra y devuelve una lista de formatos mp4 disponibles.
        """
        formats = info.get('formats', [])
        print(f"[VideoDownloader] Formatos crudos encontrados: {len(formats)}")
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
                     print(f"[VideoDownloader] Formato detectado: {display_str} (h={h})")
                     
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

                # Determinar ruta de plugins
                plugin_dirs = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ytdlp_plugins')]
                
                ffmpeg_path = self.ffmpeg_path

                use_oauth2 = os.environ.get('YOUTUBE_OAUTH2', '').lower() == 'true'

                opts = {
                    'format': format_id,
                    'outtmpl': f"{dest_folder}/%(title)s.%(ext)s",
                    'progress_hooks': [progress_hook],
                    'quiet': False,
                    'verbose': True,
                    'plugin_dirs': plugin_dirs, # Inyección forzada en descarga
                    'no_warnings': False,
                    'noplaylist': True,
                    'ffmpeg_location': ffmpeg_path,
                    'nocheckcertificate': True,
                    'cachedir': False,
                    'geo_bypass': True,
                    'force_ipv4': True,
                    'extractor_args': {
                        'youtube': {
                            # android_vr: no necesita JS signature ni PO Token, devuelve HD
                            'player_client': ['android_vr', 'android', 'ios'],
                        }
                    },
                    'youtube_include_dash_manifest': True,
                    'youtube_include_hls_manifest': True,
                    'compat_opts': ['no-youtube-unavailable-videos', 'no-youtube-channel-redirect'],
                }
                 # Inyectar cookies obligatoriamente en Datacenter (GCP)
                if self.cookie_file:
                    print("[VideoDownloader] Aplicando sesión de usuario para la descarga definitiva.")
                    opts['cookiefile'] = self.cookie_file

                bgutil_available = False
                try:
                    urllib.request.urlopen('http://127.0.0.1:4416', timeout=1)
                    bgutil_available = True
                except:
                    pass

                if bgutil_available:
                    print("[VideoDownloader] bgutil-pot disponible, activando PO Token en descarga.")
                    opts['extractor_args']['youtubepot-bgutilhttp'] = {'base_url': ['http://127.0.0.1:4416']}
                    opts['extractor_args']['youtube']['po_token'] = 'web+http://localhost:4416'
                    opts['extractor_args']['youtube']['player_client'] = ['android', 'ios', 'mweb']
                else:
                    print("[VideoDownloader] bgutil-pot NO disponible, descargando con android_vr.")
                
                if use_oauth2:
                    opts['username'] = 'oauth2'
                    opts['cachedir'] = '/tmp/yt_dlp_cache'
                    if not os.path.exists('/tmp/yt_dlp_cache'):
                        os.makedirs('/tmp/yt_dlp_cache')

                # Caso especial para "Mejor Calidad (MP4)"
                if format_id == 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best':
                    opts['merge_output_format'] = 'mp4'
                    # Simplificación máxima para diagnóstico
                    opts['format'] = 'bestvideo+bestaudio/best'
                    
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
                
                try:
                    # Intentar descarga con la configuración primaria (enfocada en TV/iOS)
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info_result = ydl.extract_info(url, download=True)
                        final_path = ydl.prepare_filename(info_result)
                except Exception as e:
                    err_msg = str(e).lower()
                    if any(x in err_msg for x in ["bot", "sign in", "player response", "unplayable", "page needs to be reloaded", "format is not available"]):
                        print(f"[VideoDownloader] Bloqueo o falta de formato en descarga. Iniciando Cascada de Rescate de GVS...")
                        
                        fallback_clients = [
                            {'name': 'Android TestSuite', 'client': ['android_testsuite']},
                            {'name': 'Android Embedded', 'client': ['android_embedded']},
                            {'name': 'Web Embedded', 'client': ['web_embedded']},
                            {'name': 'Smart TV', 'client': ['tv']},
                        ]
                        
                        for fc in fallback_clients:
                            print(f"[VideoDownloader] Reintentando descarga como: {fc['name']}...")
                            fb_opts = copy.deepcopy(opts)
                            fb_opts['extractor_args']['youtube']['player_client'] = fc['client']
                            # Flexibilizar formato en rescate: intentar el sugerido, pero caer a 'best' si no está en este cliente
                            fb_opts['format'] = f"{format_id}/bestvideo+bestaudio/best"
                            
                            try:
                                with yt_dlp.YoutubeDL(fb_opts) as ydl_fb:
                                    info_result = ydl_fb.extract_info(url, download=True)
                                    final_path = ydl_fb.prepare_filename(info_result)
                                    break # Éxito
                            except Exception:
                                # Último intento desesperado: bajar 'best' sin merge
                                try:
                                    print(f"[VideoDownloader] Intento de emergencia 'best' absoluto para {fc['name']}...")
                                    fb_opts_ultra = copy.deepcopy(fb_opts)
                                    fb_opts_ultra['format'] = 'best'
                                    if 'merge_output_format' in fb_opts_ultra: del fb_opts_ultra['merge_output_format']
                                    with yt_dlp.YoutubeDL(fb_opts_ultra) as ydl_ultra:
                                        info_result = ydl_ultra.extract_info(url, download=True)
                                        final_path = ydl_ultra.prepare_filename(info_result)
                                        break
                                except Exception:
                                    continue
                        else:
                            # Si salimos del loop sin break, el fallback falló
                            raise e
                    else:
                        raise e
                    
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

