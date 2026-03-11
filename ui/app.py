import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.utils import validate_url, format_time, load_image_from_url
from core.downloader import VideoDownloader

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de ventana
        self.title("Video Downloader")
        self.geometry("600x650")
        self.resizable(False, False)
        
        # Tema moderno y oscuro por defecto
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # Instancia del gestor de descargas
        self.downloader = VideoDownloader()
        self.current_info = None
        self.current_formats = []
        
        # UI Setup
        self._create_widgets()

    def _create_widgets(self):
        # --- Título ---
        self.title_label = ctk.CTkLabel(self, text="Descargador de Videos", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(20, 10))
        
        # --- Frame URL ---
        self.url_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.url_frame.pack(fill="x", padx=20, pady=10)
        
        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="Pega la URL del video aquí (ej. YouTube, Twitter, etc.)", height=40)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.analyze_btn = ctk.CTkButton(self.url_frame, text="Analizar", command=self.on_analyze_clicked, width=100, height=40)
        self.analyze_btn.pack(side="right")
        
        # --- Frame Info del Video (oculto por defecto) ---
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.pack(fill="x", padx=20, pady=10)
        self.info_frame.pack_forget() # Lo ocultamos inicialmente
        
        self.thumbnail_label = ctk.CTkLabel(self.info_frame, text="")
        self.thumbnail_label.pack(pady=10)
        
        self.video_title_label = ctk.CTkLabel(self.info_frame, text="", font=ctk.CTkFont(weight="bold"), wraplength=500)
        self.video_title_label.pack(pady=(0, 5))
        
        self.video_duration_label = ctk.CTkLabel(self.info_frame, text="", text_color="gray")
        self.video_duration_label.pack(pady=(0, 10))
        
        # --- Frame de Opciones ---
        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.pack(fill="x", padx=20, pady=10)
        
        # Calidad
        self.quality_label = ctk.CTkLabel(self.options_frame, text="Calidad:")
        self.quality_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.quality_var = ctk.StringVar(value="")
        self.quality_menu = ctk.CTkOptionMenu(self.options_frame, variable=self.quality_var, values=[""], state="disabled")
        self.quality_menu.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Destino
        self.dest_label = ctk.CTkLabel(self.options_frame, text="Destino:")
        self.dest_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        
        # Por defecto la carpeta descargas del usuario
        default_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.dest_var = ctk.StringVar(value=default_dir)
        
        self.dest_entry = ctk.CTkEntry(self.options_frame, textvariable=self.dest_var, state="readonly", width=300)
        self.dest_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        self.dest_btn = ctk.CTkButton(self.options_frame, text="Explorar...", command=self.on_browse_clicked, width=80)
        self.dest_btn.grid(row=1, column=2, padx=10, pady=10)
        
        # Centrar columnas
        self.options_frame.columnconfigure(1, weight=1)
        
        # --- Área de Descarga y Progreso ---
        self.download_btn = ctk.CTkButton(self, text="Descargar Video", command=self.on_download_clicked, height=45, state="disabled", font=ctk.CTkFont(weight="bold"))
        self.download_btn.pack(fill="x", padx=40, pady=20)
        
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(fill="x", padx=40, pady=(0, 10))
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(self, text="Esperando URL...", text_color="gray")
        self.status_label.pack(pady=(0, 20))


    def on_browse_clicked(self):
        folder_selected = filedialog.askdirectory(initialdir=self.dest_var.get())
        if folder_selected:
            self.dest_var.set(folder_selected)

    def on_analyze_clicked(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Error", "Por favor ingresa una URL.")
            return
            
        if not validate_url(url):
            messagebox.showerror("Error", "URL inválida. Asegúrate de incluir http:// o https://")
            return
            
        self.status_label.configure(text="Analizando...", text_color="white")
        self.analyze_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self.info_frame.pack_forget() # Ocultar mientras analiza
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        
        # Ejecutar análisis en otro thread para no congelar la UI
        threading.Thread(target=self._analyze_task, args=(url,), daemon=True).start()

    def _analyze_task(self, url: str):
        try:
            info = self.downloader.extract_info(url)
            self.current_info = info
            self.current_formats = self.downloader.get_supported_formats(info)
            
            # Volver al thread principal para actualizar UI
            self.after(0, self._on_analyze_success)
        except Exception as e:
            self.after(0, self._on_analyze_error, str(e))

    def _on_analyze_success(self):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        
        self.analyze_btn.configure(state="normal")
        self.status_label.configure(text="Análisis completado.", text_color="green")
        
        # Actualizar Info Panel
        title = self.current_info.get('title', 'Video Desconocido')
        duration = self.current_info.get('duration', 0)
        thumb_url = self.current_info.get('thumbnail')
        
        self.video_title_label.configure(text=title)
        self.video_duration_label.configure(text=f"Duración: {format_time(duration)}")
        
        # Descargar y mostrar miniatura
        if thumb_url:
            self.status_label.configure(text="Cargando miniatura...")
            threading.Thread(target=self._load_thumbnail_task, args=(thumb_url,), daemon=True).start()
        else:
            self.thumbnail_label.configure(text="(Sin miniatura)")
            
        # Opciones de Calidad
        if self.current_formats:
            options = [f['display'] for f in self.current_formats]
            self.quality_menu.configure(values=options, state="normal")
            self.quality_var.set(options[0])
            self.download_btn.configure(state="normal")
        else:
            self.quality_menu.configure(values=["Sin formatos"], state="disabled")
            self.quality_var.set("Sin formatos")
            messagebox.showinfo("Formatos", "No se encontraron formatos de video descargables para esta URL.")
            
        self.info_frame.pack(fill="x", padx=20, pady=10, before=self.options_frame)

    def _load_thumbnail_task(self, url):
        img = load_image_from_url(url)
        if img:
            # Resize para la UI
            img.thumbnail((320, 180))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            self.after(0, lambda: self.thumbnail_label.configure(image=ctk_img, text=""))
            self.after(0, lambda: self.status_label.configure(text="Listo para descargar."))
        else:
            self.after(0, lambda: self.thumbnail_label.configure(text="(Error cargando miniatura)"))

    def _on_analyze_error(self, error_msg: str):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        
        self.analyze_btn.configure(state="normal")
        self.status_label.configure(text="Error al analizar la URL.", text_color="red")
        messagebox.showerror("Error de Análisis", f"No se pudo analizar el video.\nDetalles: {error_msg}")

    def on_download_clicked(self):
        url = self.url_entry.get().strip()
        dest = self.dest_var.get()
        selected_display = self.quality_var.get()
        
        if not os.path.exists(dest):
            messagebox.showerror("Error", "La carpeta de destino no existe.")
            return
            
        # Buscar el ID del formato seleccionado
        format_id = 'best'
        for f in self.current_formats:
            if f['display'] == selected_display:
                format_id = f['id']
                break
                
        # Bloquear UI
        self.analyze_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self.quality_menu.configure(state="disabled")
        self.dest_btn.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        
        self.progress_bar.set(0)
        self.status_label.configure(text="Iniciando descarga...", text_color="white")
        
        # Iniciar descarga asincrona
        self.downloader.download_video_async(
            url=url,
            format_id=format_id,
            dest_folder=dest,
            on_progress=self._on_download_progress,
            on_complete=self._on_download_complete,
            on_error=self._on_download_error
        )

    def _on_download_progress(self, data: dict):
        percent = data.get('percent', 0.0)
        status_msg = data.get('message', '')
        self.after(0, self.progress_bar.set, percent)
        self.after(0, self.status_label.configure, {"text": status_msg})

    def _on_download_complete(self, file_path: str):
        def _ui_updates():
            self._restore_ui_state()
            self.progress_bar.set(1.0)
            self.status_label.configure(text="¡Descarga completada!", text_color="green")
            messagebox.showinfo("Éxito", f"Video descargado correctamente en:\n{file_path}")
        self.after(0, _ui_updates)

    def _on_download_error(self, error_msg: str):
        def _ui_updates():
            self._restore_ui_state()
            self.status_label.configure(text="Error en la descarga.", text_color="red")
            messagebox.showerror("Error", f"Ha ocurrido un error durante la descarga:\n{error_msg}")
        self.after(0, _ui_updates)
        
    def _restore_ui_state(self):
        self.analyze_btn.configure(state="normal")
        self.download_btn.configure(state="normal")
        self.quality_menu.configure(state="normal")
        self.dest_btn.configure(state="normal")
        self.url_entry.configure(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()
