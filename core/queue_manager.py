import threading
import uuid
import os
from typing import Dict, Any, Callable

class DownloadItem:
    def __init__(self, url: str, format_id: str, title: str, download_folder: str, group_id: str = "default"):
        self.id = str(uuid.uuid4())
        self.url = url
        self.format_id = format_id
        self.title = title
        self.download_folder = download_folder
        self.group_id = group_id  # Puede ser el ID de la playlist
        self.status = "pending" # pending, downloading, paused, processing, completed, error, cancelled
        self.progress = 0.0
        self.speed = "-- MB/s"
        self.eta = "ETA: --:--"
        self.message = "En cola..."
        self.file_path = None
        self.filename = None

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "format_id": self.format_id,
            "title": self.title,
            "status": self.status,
            "progress": self.progress,
            "speed": self.speed,
            "eta": self.eta,
            "message": self.message,
            "file_path": self.file_path,
            "filename": self.filename,
            "group_id": self.group_id
        }

class QueueManager:
    def __init__(self, downloader):
        self.downloader = downloader
        self.items: Dict[str, DownloadItem] = {}
        self.lock = threading.RLock()
        
        # Estado Global de la cola
        self.is_global_paused = False
        
        # Max descargas concurrentes
        self.max_concurrent = downloader.executor._max_workers
        self.active_count = 0

    def add_item(self, url: str, format_id: str, title: str, download_folder: str, group_id: str = "default") -> str:
        item = DownloadItem(url, format_id, title, download_folder, group_id)
        with self.lock:
            self.items[item.id] = item
        self._pump()
        return item.id

    def get_status(self, item_id: str) -> dict:
        with self.lock:
            item = self.items.get(item_id)
            if item:
                return item.to_dict()
            return {"error": "Item not found"}

    def _pump(self):
        """Revisa la cola y lanza descargas pendientes si hay cupo y no está globalmente pausado."""
        with self.lock:
            # Recontar activos reales
            self.active_count = sum(1 for it in self.items.values() if it.status == "downloading" or it.status == "processing")
            
            if self.is_global_paused:
                return

            # Mientras haya cupo, buscar items 'pending'
            for item in self.items.values():
                if self.active_count >= self.max_concurrent:
                    break
                
                if item.status == "pending":
                    self._start_item(item)
                    self.active_count += 1

    def _start_item(self, item: DownloadItem):
        item.status = "downloading"
        item.message = "Iniciando descarga..."

        def on_progress(data: dict):
            if item.status in ["paused", "cancelled", "error"]:
                return # Ignorar eventos viejos si ya cambió estado maestro
            
            item.progress = data.get('percent', 0.0) * 100
            item.speed = data.get('speed', item.speed)
            item.eta = data.get('eta', item.eta)
            item.message = data.get('message', item.message)
            if data.get('status') == 'processing':
                item.status = 'processing'

        def on_complete(file_path):
            if item.status not in ["paused", "cancelled", "error"]:
                item.status = "completed"
                item.progress = 100.0
                item.message = "¡Completado!"
                item.file_path = file_path
                item.filename = os.path.basename(file_path)
            self._on_item_finish()

        def on_error(error_msg):
            # yt-dlp arroja error al forzar la cancelación/pausa; filtramos según nuestro estado deseado.
            if item.status == "cancelled":
                item.message = "Descarga cancelada."
                self._cleanup_parts(item)
            elif item.status == "paused":
                item.message = "Pausado"
            else:
                item.status = "error"
                item.message = error_msg
            self._on_item_finish()

        self.downloader.download_video_async(
            url=item.url,
            format_id=item.format_id,
            dest_folder=item.download_folder,
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
            download_id=item.id
        )

    def _on_item_finish(self):
        """Se llama cuando un hilo termina, sin importar el motivo."""
        with self.lock:
            # Reevaluar la cola para arrancar al siguiente si aplica
            self._pump()

    # --- Acciones Individuales ---
    def pause_item(self, item_id: str):
        with self.lock:
            item = self.items.get(item_id)
            if not item: return

            if item.status == "downloading" or item.status == "processing":
                item.status = "paused"
                item.message = "Pausando..."
                item.speed = "-- MB/s"
                item.eta = "ETA: --:--"
                self.downloader.pause_download(item_id)
            elif item.status == "pending":
                item.status = "paused"
                item.message = "Pausado"

    def resume_item(self, item_id: str):
        with self.lock:
            item = self.items.get(item_id)
            if not item: return
            
            if item.status in ["paused", "error"]:
                item.status = "pending"
                item.message = "Reanudando (En cola)..."
                # Si el usuario fuerza reanudar individualmente saltamos el candado global
                self.is_global_paused = False 
                
                # Remover posible flag de pausa/cancel del downloader core
                try:
                    self.downloader.paused_downloads.discard(item_id)
                    self.downloader.canceled_downloads.discard(item_id)
                except: pass
                
        self._pump()
        
    def cancel_item(self, item_id: str):
        with self.lock:
            item = self.items.get(item_id)
            if not item: return
            
            if item.status in ["downloading", "processing"]:
                item.status = "cancelled"
                item.message = "Cancelando..."
                self.downloader.cancel_download(item_id)
            elif item.status in ["pending", "paused", "error"]:
                item.status = "cancelled"
                item.message = "Cancelado."
                # Limpiar cualquier fragmento .part posible si yt-dlp no lo ha tocado en memoria local
                self._cleanup_parts(item)
                
    # --- Acciones Globales (Playlist / All) ---
    def pause_all(self):
        with self.lock:
            self.is_global_paused = True
            for item in self.items.values():
                if item.status not in ["completed", "cancelled"]:
                    self.pause_item(item.id)

    def resume_all(self):
        with self.lock:
            self.is_global_paused = False
            for item in self.items.values():
                if item.status in ["paused", "error"]:
                    item.status = "pending"
                    item.message = "En cola..."
                    try:
                        self.downloader.paused_downloads.discard(item.id)
                        self.downloader.canceled_downloads.discard(item.id)
                    except: pass
        self._pump()

    def cancel_all(self):
        with self.lock:
            for item in self.items.values():
                if item.status not in ["completed", "cancelled"]:
                    self.cancel_item(item.id)
                    # Forzar limpieza inmediata para los que no están activos
                    if item.status == "cancelled":
                        self._cleanup_parts(item)

    def _cleanup_parts(self, item: DownloadItem):
        """Intenta borrar restos de archivos (.part, .ytdl) si la descarga se cancela o falla."""
        if not item.title or not item.download_folder:
            return
            
        try:
            # Limpiar nombre para búsqueda (quitar caracteres que yt-dlp suele escapar o cambiar)
            # Buscamos archivos que comiencen con el título (truncado por seguridad)
            prefix = item.title[:50] 
            if os.path.exists(item.download_folder):
                for f in os.listdir(item.download_folder):
                    if f.startswith(prefix) and (f.endswith(".part") or f.endswith(".ytdl")):
                        full_path = os.path.join(item.download_folder, f)
                        try:
                            os.remove(full_path)
                            print(f"[QueueManager] Limpiado residuo: {f}")
                        except Exception as e:
                            print(f"[QueueManager] No se pudo borrar {f}: {e}")
        except Exception as e:
            print(f"[QueueManager] Error en limpieza de residuos: {e}")

    def clear_finished_items(self):
        """Elimina de la cola los items que ya terminaron (completados, cancelados o con error)."""
        with self.lock:
            # Creamos una lista de IDs a eliminar para no modificar el diccionario mientras iteramos
            to_remove = [item_id for item_id, item in self.items.items() 
                         if item.status in ["completed", "cancelled", "error"]]
            for item_id in to_remove:
                del self.items[item_id]
