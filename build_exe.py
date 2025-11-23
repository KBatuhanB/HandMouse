"""
HandMouse EXE Builder
Bu script HandMouse uygulamasını tek bir .exe dosyasına derler.
"""

import PyInstaller.__main__
import sys
from pathlib import Path
import os

# Proje dizini
project_dir = Path(__file__).parent

# İkon oluştur
print("🎨 İkon kontrol ediliyor...")
icon_path = project_dir / "icon.ico"

if not icon_path.exists():
    print("⚠️  İkon bulunamadı, oluşturuluyor...")
    import subprocess
    subprocess.run([sys.executable, "create_icon.py"], check=True)

if icon_path.exists():
    print(f"✅ İkon bulundu: {icon_path}")
    icon_arg = f'--icon={icon_path}'
else:
    print("⚠️  İkon oluşturulamadı, ikonsuz devam ediliyor...")
    icon_arg = '--icon=NONE'

# PyInstaller argümanları
PyInstaller.__main__.run([
    'gui_main.py',                          # Ana dosya
    '--name=HandMouse',                     # Exe ismi
    '--onefile',                            # Tek dosya olarak derle
    '--windowed',                           # Konsol penceresi açma
    icon_arg,                               # İkon
    f'--add-data=src;src',                  # src klasörünü dahil et
    '--hidden-import=cv2',                  # OpenCV
    '--hidden-import=mediapipe',            # MediaPipe
    '--hidden-import=customtkinter',        # CustomTkinter
    '--hidden-import=pycaw',                # Pycaw
    '--hidden-import=comtypes',             # COM types
    '--hidden-import=pyautogui',            # PyAutoGUI
    '--hidden-import=pillow',               # PIL
    '--hidden-import=numpy',                # NumPy
    '--hidden-import=win32api',             # Win32
    '--hidden-import=win32con',             # Win32
    '--hidden-import=win32gui',             # Win32
    '--collect-all=mediapipe',              # MediaPipe dosyalarını topla
    '--collect-all=cv2',                    # OpenCV dosyalarını topla
    '--noconfirm',                          # Onay isteme
    '--clean',                              # Build klasörünü temizle
])

print("\n" + "="*60)
print("✅ EXE OLUŞTURULDU!")
print("="*60)
print(f"\n📁 Konum: {project_dir / 'dist' / 'HandMouse.exe'}")
print("\n🚀 Kullanım:")
print("   - dist/HandMouse.exe dosyasını çift tıklayarak çalıştırabilirsiniz")
print("   - Bu dosyayı istediğiniz yere kopyalayabilirsiniz")
print("   - Başka bir bilgisayarda da çalışır (Python yüklü olması gerekmez)")
print("\n" + "="*60)
