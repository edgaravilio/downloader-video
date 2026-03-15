import yt_dlp
import sys
import os

def main():
    print("--- GENERADOR DE TOKEN OAUTH2 PARA YOUTUBE ---")
    print("Este script te ayudará a obtener un token de acceso seguro para que tu servidor en la nube")
    print("pueda descargar videos sin ser bloqueado por YouTube.")
    print("\nPASOS:")
    print("1. El script generará un código de 8 caracteres.")
    print("2. Deberás ir a https://www.google.com/device e ingresar ese código.")
    print("3. Una vez autorizado, los datos se guardarán en la caché de yt-dlp.")
    print("-" * 46)

    # Opciones para forzar el flujo OAuth2
    ydl_opts = {
        'username': 'oauth2',
        'quiet': False,
        'no_warnings': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['tv'],
            }
        },
    }

    try:
        # Video muy antiguo (Me at the zoo)
        test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" 
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("[INFO] Iniciando proceso de vinculación...")
            # Detectar la ruta de caché
            cache_dir = ydl.cache._get_root_dir()
            print(f"[INFO] Tu caché de yt-dlp está en: {cache_dir}")
            
            ydl.extract_info(test_url, download=False)
            
        print("\n" + "=" * 46)
        print("¡ÉXITO! El token ha sido generado.")
        print(f"Busca la carpeta de YouTube dentro de: {cache_dir}")
        print("Deberías ver archivos relacionados con 'oauth2'.")
        print("Sigue mis instrucciones en el chat para subirlo a la nube.")
        print("=" * 46)
        
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un problema: {e}")
        print("\nAsegúrate de tener instalada la última versión de yt-dlp:")
        print("pip install -U yt-dlp")

if __name__ == "__main__":
    main()
