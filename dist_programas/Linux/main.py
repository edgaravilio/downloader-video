import sys
import os

# Asegurar que el directorio raíz está en el PYTHONPATH para que core e ui se importen bien
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import App

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
