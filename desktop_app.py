import os
import sys
import threading
import socket
import webview
from web_app import app

def get_free_port():
    """ Obtiene un puerto libre para el servidor interno """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_flask(port):
    """ Ejecuta el servidor Flask en un hilo separado """
    # Desactivar logs de Flask para una experiencia limpia
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)

def main():
    port = get_free_port()
    
    # Iniciar Flask en background
    t = threading.Thread(target=run_flask, args=(port,), daemon=True)
    t.start()
    
    # Configurar la ventana de PyWebView con el diseño de alta calidad
    window = webview.create_window(
        'Video Downloader', 
        f'http://127.0.0.1:{port}',
        width=620,
        height=800,
        resizable=True,
        min_size=(500, 600)
    )
    
    # Iniciar la interfaz gráfica nativa que renderiza el HTML/CSS
    webview.start()

if __name__ == '__main__':
    main()
