import sys
import os
import logging

# Configuración básica de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Asegurar que el directorio raíz está en el PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ui.app import App
except ImportError as e:
    logger.error(f"Error al importar dependencias: {e}. Asegúrate de ejecutar 'pip install -r requirements.txt'")
    sys.exit(1)

def main():
    try:
        logger.info("Iniciando Video Downloader (App Nativa)...")
        app = App()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Error fatal en la aplicación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
