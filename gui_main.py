"""
Hand Mouse - GUI Başlatıcı
Modern arayüz ile Hand Mouse Controller.
"""

import sys
from pathlib import Path

# Proje modüllerini import et
sys.path.append(str(Path(__file__).parent / 'src'))

from src.gui_app import main

if __name__ == "__main__":
    main()
