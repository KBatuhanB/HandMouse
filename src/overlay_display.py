"""
Overlay Display Modülü
Ekran üzerinde her zaman görünen, tıklanamayan (click-through) bilgi paneli.
"""

import tkinter as tk
from typing import Dict, Optional
import threading
import platform

# Windows API için
if platform.system() == 'Windows':
    try:
        import win32gui
        import win32con
        import win32api
        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
        print("⚠️  pywin32 yüklü değil. Click-through çalışmayabilir.")
else:
    HAS_WIN32 = False


class OverlayDisplay:
    """
    Ekran üzerinde şeffaf overlay penceresi.
    Her zaman en üstte kalır ve durum bilgilerini gösterir.
    """
    
    def __init__(self, position: str = 'topright'):
        """
        OverlayDisplay sınıfını başlatır.
        
        Args:
            position: Pencerenin konumu ('topright', 'topleft', 'bottomright', 'bottomleft')
        """
        self.position = position
        self.window = None
        self.labels = {}
        self.is_running = False
        
        # Renkler (hex formatında)
        self.colors = {
            'bg': '#1a1a1a',           # Koyu gri arka plan
            'text': '#ffffff',         # Beyaz metin
            'green': '#00ff00',        # Yeşil (aktif)
            'red': '#ff0000',          # Kırmızı (yok/hata)
            'orange': '#ffa500',       # Turuncu (duraklı)
            'yellow': '#ffff00',       # Sarı (uyarı)
            'cyan': '#00ffff',         # Cyan (bilgi)
        }
        
        # Durum verileri
        self.status_data = {
            'fps': 0,
            'right_hand': 'YOK',
            'right_hand_color': 'red',
            'left_hand': 'YOK',
            'left_hand_color': 'red',
            'global_pause': False,
            'current_gesture': 'Bekleniyor...',
            'speech_active': False,
        }
        
        print("📺 Overlay Display hazırlanıyor...")
    
    def start(self):
        """Overlay penceresini başlatır (ayrı thread'de)."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Tkinter'ı ayrı thread'de çalıştır
        self.thread = threading.Thread(target=self._run_window, daemon=True)
        self.thread.start()
        
        print("✅ Overlay Display başlatıldı (monitör üzerinde)")
    
    def _run_window(self):
        """Tkinter penceresini oluşturur ve çalıştırır."""
        # Ana pencere oluştur
        self.window = tk.Tk()
        self.window.title("Hand Mouse - Status")
        
        # Pencere boyutu
        width = 350
        height = 330
        
        # Pencere konumunu belirle
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        if self.position == 'topright':
            x = screen_width - width - 10
            y = 10
        elif self.position == 'topleft':
            x = 10
            y = 10
        elif self.position == 'bottomright':
            x = screen_width - width - 10
            y = screen_height - height - 50
        else:  # bottomleft
            x = 10
            y = screen_height - height - 50
        
        # Pencere özelliklerini ayarla
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.configure(bg=self.colors['bg'])
        
        # Her zaman en üstte
        self.window.attributes('-topmost', True)
        
        # Şeffaflık (0.0 - 1.0, 0.9 = %90 opak)
        self.window.attributes('-alpha', 0.96)
        
        # Pencere çerçevesini kaldır (başlık çubuğu yok)
        self.window.overrideredirect(True)
        
        # UI elementlerini oluştur
        self._create_ui()
        
        # Windows'ta click-through yap (mouse geçsin, tıklanamaz olsun)
        if HAS_WIN32:
            self.window.update()  # Pencereyi render et
            # HWND'yi tkinter üzerinden al
            hwnd = int(self.window.wm_frame(), 16)
            
            # Mevcut stil ayarlarını al
            styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            # WS_EX_LAYERED ve WS_EX_TRANSPARENT ekle
            styles = styles | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            # Yeni stilleri uygula
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, styles)
            # Şeffaflığı ayarla (0-255, 245 = %96)
            win32gui.SetLayeredWindowAttributes(hwnd, 0, 120, win32con.LWA_ALPHA)
            print("✅ Click-through aktif - Mouse altındaki pencerelerle etkileşir")
        
        # Pencereyi çalıştır
        self.window.mainloop()
    
    def _create_ui(self):
        """UI elementlerini oluşturur."""
        # Başlık
        title_label = tk.Label(
            self.window,
            text="🖐️ HAND MOUSE CONTROLLER",
            font=('Consolas', 14, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['cyan']
        )
        title_label.pack(pady=10)
        
        # Ayırıcı çizgi
        separator1 = tk.Frame(self.window, height=2, bg=self.colors['cyan'])
        separator1.pack(fill='x', padx=10, pady=5)
        
        # FPS
        fps_frame = tk.Frame(self.window, bg=self.colors['bg'])
        fps_frame.pack(fill='x', padx=20, pady=3)
        
        tk.Label(
            fps_frame,
            text="FPS:",
            font=('Consolas', 11, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(side='left')
        
        self.labels['fps'] = tk.Label(
            fps_frame,
            text="0",
            font=('Consolas', 11),
            bg=self.colors['bg'],
            fg=self.colors['yellow']
        )
        self.labels['fps'].pack(side='right')
        
        # Sağ El Durumu
        right_frame = tk.Frame(self.window, bg=self.colors['bg'])
        right_frame.pack(fill='x', padx=20, pady=3)
        
        tk.Label(
            right_frame,
            text="SAĞ EL:",
            font=('Consolas', 11, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(side='left')
        
        self.labels['right_hand'] = tk.Label(
            right_frame,
            text="YOK",
            font=('Consolas', 11, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['red']
        )
        self.labels['right_hand'].pack(side='right')
        
        # Sol El Durumu
        left_frame = tk.Frame(self.window, bg=self.colors['bg'])
        left_frame.pack(fill='x', padx=20, pady=3)
        
        tk.Label(
            left_frame,
            text="SOL EL:",
            font=('Consolas', 11, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(side='left')
        
        self.labels['left_hand'] = tk.Label(
            left_frame,
            text="YOK",
            font=('Consolas', 11, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['red']
        )
        self.labels['left_hand'].pack(side='right')
        
        # Ayırıcı çizgi
        separator2 = tk.Frame(self.window, height=2, bg=self.colors['cyan'])
        separator2.pack(fill='x', padx=10, pady=10)
        
        # Global Pause Durumu
        self.labels['global_pause'] = tk.Label(
            self.window,
            text="",
            font=('Consolas', 12, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['red']
        )
        self.labels['global_pause'].pack(pady=5)
        
        # Güncel Jest
        gesture_frame = tk.Frame(self.window, bg=self.colors['bg'])
        gesture_frame.pack(fill='x', padx=20, pady=5)
        
        tk.Label(
            gesture_frame,
            text="Jest:",
            font=('Consolas', 10),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(side='left')
        
        self.labels['gesture'] = tk.Label(
            gesture_frame,
            text="Bekleniyor...",
            font=('Consolas', 10),
            bg=self.colors['bg'],
            fg=self.colors['yellow']
        )
        self.labels['gesture'].pack(side='right')
        
        # Alt bilgi
        info_label = tk.Label(
            self.window,
            text="'q' - Çıkış | İşaret parmakları - Pause",
            font=('Consolas', 8),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        info_label.pack(side='bottom', pady=5)
        
        # Sesli Yazma Durumu (EN ALTTA, belirgin)
        self.labels['speech'] = tk.Label(
            self.window,
            text="🎤 Hazır",
            font=('Consolas', 11, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['green']
        )
        self.labels['speech'].pack(side='bottom', pady=8)
    
    def update(self, **kwargs):
        """
        Overlay verilerini günceller.
        
        Args:
            **kwargs: Güncellenecek veriler (fps, right_hand, left_hand, vb.)
        """
        if not self.is_running or not self.window:
            return
        
        # Verileri güncelle
        for key, value in kwargs.items():
            if key in self.status_data:
                self.status_data[key] = value
        
        # UI'ı güncelle (thread-safe)
        try:
            self.window.after(0, self._update_ui)
        except:
            pass
    
    def _update_ui(self):
        """UI elementlerini günceller (main thread'de çalışmalı)."""
        try:
            # FPS
            if 'fps' in self.labels:
                self.labels['fps'].config(text=str(self.status_data['fps']))
            
            # Sağ El
            if 'right_hand' in self.labels:
                text = self.status_data['right_hand']
                color = self.colors[self.status_data['right_hand_color']]
                self.labels['right_hand'].config(text=text, fg=color)
            
            # Sol El
            if 'left_hand' in self.labels:
                text = self.status_data['left_hand']
                color = self.colors[self.status_data['left_hand_color']]
                self.labels['left_hand'].config(text=text, fg=color)
            
            # Global Pause
            if 'global_pause' in self.labels:
                if self.status_data['global_pause']:
                    self.labels['global_pause'].config(
                        text="⏸️ GLOBAL PAUSE",
                        fg=self.colors['red']
                    )
                else:
                    self.labels['global_pause'].config(text="")
            
            # Güncel Jest
            if 'gesture' in self.labels:
                self.labels['gesture'].config(
                    text=self.status_data['current_gesture']
                )
            
            # Sesli Yazma
            if 'speech' in self.labels:
                if self.status_data['speech_active']:
                    self.labels['speech'].config(
                        text="🎤 DİNLENİYOR...",
                        fg=self.colors['red']
                    )
                else:
                    self.labels['speech'].config(
                        text="🎤 Hazır",
                        fg=self.colors['green']
                    )
        except:
            pass
    
    def stop(self):
        """Overlay penceresini kapatır (thread-safe)."""
        self.is_running = False
        print("🔴 Overlay Display kapatılıyor...")
        
        # Pencereyi kendi thread'inde kapat
        if self.window:
            try:
                # after() kullanarak kendi thread'inde kapansın
                self.window.after(10, self._do_close)
            except:
                pass
    
    def _do_close(self):
        """Pencereyi kapatır (overlay thread'inde çalışır)."""
        try:
            if self.window:
                self.window.destroy()
                self.window = None
        except Exception as e:
            pass  # Sessizce devam et
    
    def _safe_close(self):
        """Pencereyi güvenli şekilde kapatır (Tkinter main thread'de çalışır)."""
        try:
            if self.window:
                # Sadece destroy kullan - quit() kullanma!
                self.window.destroy()
                self.window = None
        except:
            pass
