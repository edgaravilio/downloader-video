import re
from typing import Optional
import urllib.request
from io import BytesIO
from PIL import Image

def validate_url(url: str) -> bool:
    """
    Valida si una cadena es una URL básica usando expresiones regulares.
    Acepta formatos http:// y https://.
    
    Args:
        url (str): URL a validar.
        
    Returns:
        bool: True si la URL es válida, False en caso contrario.
    """
    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return re.match(regex, url) is not None

def format_time(seconds: int) -> str:
    """
    Convierte un valor de tiempo en segundos a un formato de cadena legible HH:MM:SS o MM:SS.
    
    Args:
        seconds (int): Segundos totales.
        
    Returns:
        str: Cadena formateada.
    """
    if not isinstance(seconds, int) or seconds < 0:
        return "00:00"
        
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def format_size(bytes_size: int) -> str:
    """
    Convierte bytes a formato humano (KB, MB, GB).
    
    Args:
        bytes_size (int): Tamaño en bytes.
        
    Returns:
        str: Tamaño formateado (e.g., '14.5 MB').
    """
    if not isinstance(bytes_size, (int, float)) or bytes_size < 0:
        return "0.0 B"
        
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0

def load_image_from_url(url: str) -> Optional[Image.Image]:
    """
    Descarga una imagen desde una URL y la devuelve como un objeto Image de PIL.
    Maneja excepciones de red de forma simple, retornando None.
    
    Args:
        url (str): URL de la imagen.
        
    Returns:
        Optional[Image.Image]: Objeto imagen de PIL, o None si hay un error.
    """
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            image_data = response.read()
        return Image.open(BytesIO(image_data))
    except Exception as e:
        print(f"Error cargando imagen desde {url}: {e}")
        return None
