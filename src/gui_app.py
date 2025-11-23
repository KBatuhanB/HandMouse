"""
GUI Uygulaması - Hand Mouse Kontrol Paneli
CustomTkinter kullanarak modern arayüz.
"""

import customtkinter as ctk
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk
import threading
import time
from typing import Optional
import sys
from pathlib import Path
import importlib

# Proje modüllerini import et
sys.path.append(str(Path(__file__).parent.parent))
from src.config import Config
from src.hand_detector import HandDetector
from src.mouse_controller import MouseController
from src.gesture_recognizer import GestureRecognizer
from src.volume_controller import VolumeController
from src.speech_to_text import SpeechToText
from src.overlay_display import OverlayDisplay
from src.config_manager import ConfigManager
from src import config as config_module  # Reload için modül referansı


class HandMouseGUI:
    """Ana GUI sınıfı"""
    
    def __init__(self):
        """GUI'yi başlat"""
        # Tema ayarla
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Ana pencere
        self.root = ctk.CTk()
        self.root.title("🖐️ Hand Mouse Controller")
        self.root.geometry("1400x800")
        
        # Uygulama durumu
        self.is_running = False
        self.is_paused = False
        # self.show_overlay kaldırıldı - overlay_var kullanılıyor
        
        # Hand Mouse bileşenleri
        self.camera = None
        self.hand_detector = None
        self.mouse_controller = None
        self.gesture_recognizer = None
        self.volume_controller = None
        self.speech_to_text = None
        self.overlay = None
        
        # Thread kontrolü
        self.process_thread = None
        self.running_flag = False
        
        # Config Manager
        self.config_manager = ConfigManager()
        
        # Kamera görüntüsü
        self.camera_label = None
        self.current_frame = None
        
        # UI oluştur
        self.create_widgets()
        
    def create_widgets(self):
        """UI bileşenlerini oluştur"""
        # Ana grid layout (2 sütun)
        self.root.grid_columnconfigure(0, weight=2)  # Sol taraf (kamera)
        self.root.grid_columnconfigure(1, weight=1)  # Sağ taraf (kontroller)
        self.root.grid_rowconfigure(0, weight=1)
        
        # ============ SOL PANEL - KAMERA ============
        self.left_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Başlık
        title = ctk.CTkLabel(
            self.left_frame, 
            text="📹 Kamera Görüntüsü",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=10)
        
        # Kamera alanı
        self.camera_label = ctk.CTkLabel(self.left_frame, text="")
        self.camera_label.pack(padx=10, pady=10, expand=True, fill="both")
        
        # Durum bilgisi
        self.status_label = ctk.CTkLabel(
            self.left_frame,
            text="▶️ Başlatmak için 'Başlat' butonuna basın",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(pady=10)
        
        # ============ SAĞ PANEL - KONTROLLER ============
        self.right_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Başlık ve Yardım butonu için frame
        title_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        title_frame.pack(pady=15, fill="x", padx=15)
        
        # Başlık
        title = ctk.CTkLabel(
            title_frame,
            text="⚙️ Kontrol Paneli",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(side="left")
        
        # Yardım butonu
        help_button = ctk.CTkButton(
            title_frame,
            text="ℹ️ Yardım",
            command=self.show_help,
            width=80,
            height=30,
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        help_button.pack(side="right")
        
        # ========== ANA KONTROLLER ==========
        controls_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        controls_frame.pack(fill="x", padx=15, pady=10)
        
        # Başlat/Durdur butonu
        self.start_button = ctk.CTkButton(
            controls_frame,
            text="▶️ BAŞLAT",
            command=self.toggle_start,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_button.pack(fill="x", pady=5)
        
        # Oynat/Duraklat butonu
        self.pause_button = ctk.CTkButton(
            controls_frame,
            text="⏸️ DURAKLAT",
            command=self.toggle_pause,
            height=40,
            font=ctk.CTkFont(size=14),
            state="disabled"
        )
        self.pause_button.pack(fill="x", pady=5)
        
        # Overlay toggle
        self.overlay_var = ctk.BooleanVar(value=True)
        self.overlay_check = ctk.CTkCheckBox(
            controls_frame,
            text="Ekran Panelini Göster",
            variable=self.overlay_var,
            command=self.toggle_overlay,
            font=ctk.CTkFont(size=13)
        )
        self.overlay_check.pack(pady=10)
        
        # Ayırıcı
        separator = ctk.CTkFrame(self.right_frame, height=2, fg_color="gray")
        separator.pack(fill="x", padx=15, pady=15)
        
        # ========== AYARLAR SEKMELERİ (SCROLLABLE) ==========
        # Scrollable frame içine tabview alıyoruz
        self.settings_scroll = ctk.CTkScrollableFrame(
            self.right_frame,
            fg_color="transparent"
        )
        self.settings_scroll.pack(fill="both", expand=True, padx=15, pady=(10,5))
        
        self.tabview = ctk.CTkTabview(self.settings_scroll, height=400)
        self.tabview.pack(fill="both", expand=True)
        
        # Sekmeler
        self.tabview.add("🎥 Kamera")
        self.tabview.add("🖱️ Mouse")
        self.tabview.add("🎨 Görsel")
        self.tabview.add("🔊 Ses")
        self.tabview.add("🎤 Sesli Yazma")
        
        # Her sekmeyi doldur
        self.create_camera_tab()
        self.create_mouse_tab()
        self.create_visual_tab()
        self.create_audio_tab()
        self.create_speech_tab()
        
        # ========== KAYDET BUTONU (SABİT - EN ALTTA) ==========
        # Kaydet butonu scrollable frame'in DIŞINDA - her zaman görünür
        save_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        save_frame.pack(side="bottom", fill="x", padx=15, pady=10)
        
        # Kaydet butonu (tek buton - hem kalıcı hem anlık)
        self.save_button = ctk.CTkButton(
            save_frame,
            text="💾 KAYDET",
            command=self.save_settings,
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.save_button.pack(fill="x")
        
    def create_camera_tab(self):
        """Kamera ayarları sekmesi"""
        tab = self.tabview.tab("🎥 Kamera")
        
        # Kamera Seçimi
        ctk.CTkLabel(tab, text="Kamera:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,5), padx=10)
        
        # Kamera listesini al
        camera_list = self.get_available_cameras()
        
        if camera_list:
            # Dropdown için değerler (index: name formatında)
            camera_options = [f"{idx}: {name}" for idx, name in camera_list]
            
            # Mevcut seçili index'i bul
            current_idx = Config.CAMERA_INDEX
            # Mevcut index listede var mı kontrol et
            current_value = None
            for idx, name in camera_list:
                if idx == current_idx:
                    current_value = f"{idx}: {name}"
                    break
            
            # Bulunamadıysa ilkini seç
            if current_value is None:
                current_value = camera_options[0]
            
            self.camera_index_var = ctk.StringVar(value=current_value)
            camera_dropdown = ctk.CTkOptionMenu(
                tab,
                variable=self.camera_index_var,
                values=camera_options,
                width=400
            )
            camera_dropdown.pack(fill="x", padx=10, pady=5)
            
            # Yenile butonu
            refresh_camera_btn = ctk.CTkButton(
                tab,
                text="🔄 Yenile",
                command=self.refresh_cameras,
                width=100,
                height=25
            )
            refresh_camera_btn.pack(anchor="w", padx=10, pady=5)
            
            # Bilgi
            info_label = ctk.CTkLabel(
                tab,
                text="💡 Sistemi DURDUR → BAŞLAT yaparak yeni kamerayı aktif edin",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            info_label.pack(anchor="w", padx=10, pady=5)
        else:
            ctk.CTkLabel(tab, text="❌ Kamera bulunamadı!", text_color="red").pack(anchor="w", padx=10)
            self.camera_index_var = ctk.StringVar(value="0: Kamera bulunamadı")
        
        # FPS
        ctk.CTkLabel(tab, text="Hedef FPS:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(15,5))
        self.fps_var = ctk.IntVar(value=Config.CAMERA_FPS)
        ctk.CTkSlider(tab, from_=15, to=60, number_of_steps=9, variable=self.fps_var).pack(fill="x", padx=10)
        self.fps_label = ctk.CTkLabel(tab, text=f"{Config.CAMERA_FPS} FPS")
        self.fps_label.pack()
        self.fps_var.trace_add("write", lambda *args: self.fps_label.configure(text=f"{self.fps_var.get()} FPS"))
        
        # Dead Zone
        ctk.CTkLabel(tab, text="Dead Zone (Kenar Kırpma):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(15,5))
        self.deadzone_var = ctk.DoubleVar(value=Config.CAMERA_CROP_LEFT)
        ctk.CTkSlider(tab, from_=0.01, to=0.49, number_of_steps=48, variable=self.deadzone_var).pack(fill="x", padx=10)
        self.deadzone_label = ctk.CTkLabel(tab, text=f"{int(Config.CAMERA_CROP_LEFT*100)}%")
        self.deadzone_label.pack()
        self.deadzone_var.trace_add("write", lambda *args: self.deadzone_label.configure(text=f"{int(self.deadzone_var.get()*100)}%"))
        
        # Max Hands
        ctk.CTkLabel(tab, text="Maksimum El Sayısı:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(15,5))
        self.max_hands_var = ctk.IntVar(value=Config.MAX_HANDS)
        ctk.CTkSegmentedButton(tab, values=["1", "2"], variable=self.max_hands_var).pack(fill="x", padx=10)
        
    def create_mouse_tab(self):
        """Mouse ayarları sekmesi"""
        tab = self.tabview.tab("🖱️ Mouse")
        
        # Mouse Speed
        ctk.CTkLabel(tab, text="Mouse Hızı:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,5))
        self.mouse_speed_var = ctk.DoubleVar(value=Config.MOUSE_SPEED)
        ctk.CTkSlider(tab, from_=1.0, to=5.0, number_of_steps=40, variable=self.mouse_speed_var).pack(fill="x", padx=10)
        self.mouse_speed_label = ctk.CTkLabel(tab, text=f"{Config.MOUSE_SPEED:.1f}x")
        self.mouse_speed_label.pack()
        self.mouse_speed_var.trace_add("write", lambda *args: self.mouse_speed_label.configure(text=f"{self.mouse_speed_var.get():.1f}x"))
        
        # EMA Min/Max
        ctk.CTkLabel(tab, text="EMA Minimum:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(15,5))
        self.ema_min_var = ctk.DoubleVar(value=Config.EMA_MIN)
        ctk.CTkSlider(tab, from_=0.01, to=0.2, number_of_steps=19, variable=self.ema_min_var).pack(fill="x", padx=10)
        self.ema_min_label = ctk.CTkLabel(tab, text=f"{Config.EMA_MIN:.2f}")
        self.ema_min_label.pack()
        self.ema_min_var.trace_add("write", lambda *args: self.ema_min_label.configure(text=f"{self.ema_min_var.get():.2f}"))
        
        ctk.CTkLabel(tab, text="EMA Maximum:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(15,5))
        self.ema_max_var = ctk.DoubleVar(value=Config.EMA_MAX)
        ctk.CTkSlider(tab, from_=0.3, to=1.0, number_of_steps=14, variable=self.ema_max_var).pack(fill="x", padx=10)
        self.ema_max_label = ctk.CTkLabel(tab, text=f"{Config.EMA_MAX:.2f}")
        self.ema_max_label.pack()
        self.ema_max_var.trace_add("write", lambda *args: self.ema_max_label.configure(text=f"{self.ema_max_var.get():.2f}"))
        
        # EMA Function
        ctk.CTkLabel(tab, text="EMA Fonksiyonu:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(15,5))
        self.ema_func_var = ctk.StringVar(value=Config.EMA_FUNCTION)
        ctk.CTkSegmentedButton(tab, values=["linear", "exponential", "sigmoid"], variable=self.ema_func_var).pack(fill="x", padx=10)
        
    def create_visual_tab(self):
        """Görsel ayarlar sekmesi"""
        tab = self.tabview.tab("🎨 Görsel")
        
        # Checkbox'lar
        self.show_fps_var = ctk.BooleanVar(value=Config.SHOW_FPS)
        ctk.CTkCheckBox(tab, text="FPS Göster", variable=self.show_fps_var).pack(anchor="w", pady=5, padx=10)
        
        self.show_landmarks_var = ctk.BooleanVar(value=Config.SHOW_LANDMARKS)
        ctk.CTkCheckBox(tab, text="El Noktalarını Göster", variable=self.show_landmarks_var).pack(anchor="w", pady=5, padx=10)
        
        self.show_gesture_var = ctk.BooleanVar(value=Config.SHOW_GESTURE_TEXT)
        ctk.CTkCheckBox(tab, text="Jest Adını Göster", variable=self.show_gesture_var).pack(anchor="w", pady=5, padx=10)
        
        self.flip_camera_var = ctk.BooleanVar(value=Config.FLIP_CAMERA)
        ctk.CTkCheckBox(tab, text="Kamerayı Ayna Olarak Çevir", variable=self.flip_camera_var).pack(anchor="w", pady=5, padx=10)
        
    def create_audio_tab(self):
        """Ses ayarları sekmesi"""
        tab = self.tabview.tab("🔊 Ses")
        
        # Volume Step
        ctk.CTkLabel(tab, text="Ses Değişim Adımı:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10,5))
        self.volume_step_var = ctk.IntVar(value=Config.VOLUME_STEP)
        ctk.CTkSlider(tab, from_=1, to=10, number_of_steps=9, variable=self.volume_step_var).pack(fill="x", padx=10)
        self.volume_step_label = ctk.CTkLabel(tab, text=f"{Config.VOLUME_STEP} birim")
        self.volume_step_label.pack()
        self.volume_step_var.trace_add("write", lambda *args: self.volume_step_label.configure(text=f"{self.volume_step_var.get()} birim"))
        
    def create_speech_tab(self):
        """Sesli yazma ayarları sekmesi"""
        tab = self.tabview.tab("🎤 Sesli Yazma")
        
        # Bilgi başlığı
        header_label = ctk.CTkLabel(
            tab,
            text="🎤 Sesli Yazma Otomatik Aktif",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4CAF50"
        )
        header_label.pack(pady=(10,5), padx=10)
        
        # Microphone Selection
        ctk.CTkLabel(tab, text="Mikrofon:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(15,5), padx=10)
        
        # Mikrofon listesini al
        from src.speech_to_text import SpeechToText
        mic_list = SpeechToText.get_microphone_list()
        
        if mic_list:
            # Dropdown için değerler (index: name formatında)
            mic_options = [f"{idx}: {name}" for idx, name in mic_list]
            
            # Mevcut seçili index'i bul
            current_idx = Config.SPEECH_MICROPHONE_INDEX if Config.SPEECH_MICROPHONE_INDEX is not None else 0
            current_value = mic_options[current_idx] if current_idx < len(mic_options) else mic_options[0]
            
            self.speech_mic_var = ctk.StringVar(value=current_value)
            mic_dropdown = ctk.CTkOptionMenu(
                tab,
                variable=self.speech_mic_var,
                values=mic_options,
                width=400
            )
            mic_dropdown.pack(fill="x", padx=10, pady=5)
            
            # Yenile butonu
            refresh_btn = ctk.CTkButton(
                tab,
                text="🔄 Yenile",
                command=self.refresh_microphones,
                width=100,
                height=25
            )
            refresh_btn.pack(anchor="w", padx=10, pady=5)
            
            # Otomatik Seç butonu
            auto_detect_btn = ctk.CTkButton(
                tab,
                text="🔍 Otomatik Seç",
                command=self.auto_detect_microphone,
                width=150,
                height=30,
                fg_color="#FF6B35",
                hover_color="#E85D30"
            )
            auto_detect_btn.pack(anchor="w", padx=10, pady=5)
            
            # Bilgi label'ı
            info_label = ctk.CTkLabel(
                tab,
                text="💡 Otomatik Seç: Çalışan mikrofonu otomatik bulur (1-2 saniye/mikrofon)",
                font=ctk.CTkFont(size=10),
                text_color="gray"
            )
            info_label.pack(anchor="w", padx=10, pady=2)
        else:
            self.speech_mic_var = ctk.StringVar(value="0: Varsayılan Mikrofon")
            ctk.CTkLabel(tab, text="⚠️ Mikrofon bulunamadı", text_color="orange").pack(anchor="w", padx=10)
        
        # Language
        ctk.CTkLabel(tab, text="Dil:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(15,5), padx=10)
        self.speech_lang_var = ctk.StringVar(value=Config.SPEECH_LANGUAGE)
        ctk.CTkSegmentedButton(tab, values=["tr-TR", "en-US"], variable=self.speech_lang_var).pack(fill="x", padx=10)
        
        # Bilgi mesajı - Basitleştirilmiş
        info_frame = ctk.CTkFrame(tab, fg_color="#2B5278", corner_radius=8)
        info_frame.pack(fill="x", padx=10, pady=15)
        
        info_label = ctk.CTkLabel(
            info_frame,
            text="ℹ️ Mikrofon otomatik başlar ve sürekli dinler\n"
                 "� Konuştuğunuz her şey anında yazılır",
            font=ctk.CTkFont(size=11),
            justify="left"
        )
        info_label.pack(padx=10, pady=10)
        
        # Timeout - KALDIRILDI (artık sürekli dinliyor, gerekli değil)
        # Auto Enter checkbox - KALDIRILDI (artık her cümleden sonra boşluk ekleniyor)
    
    def get_available_cameras(self, max_test=10):
        """
        Mevcut kameraları tespit et ve isimlerini al.
        pygrabber'ın isimleri OpenCV index'leriyle uyuşmadığı için
        doğrudan test ederek eşleştirme yapıyoruz.
        
        Args:
            max_test: Test edilecek maksimum kamera sayısı
            
        Returns:
            List[tuple]: [(index, name), ...] formatında kamera listesi
        """
        available_cameras = []
        
        # Doğrudan OpenCV index'lerini test et
        print("� Kameralar test ediliyor...")
        
        for i in range(max_test):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # Kamera çalışıyor - backend'den isim almayı dene
                backend_name = cap.getBackendName()
                
                # Kamera özelliklerini al
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                
                # Basit isim oluştur (index + özellikler)
                camera_name = f"Kamera {i} ({width}x{height}@{fps}fps)"
                
                available_cameras.append((i, camera_name))
                print(f"   ✅ [{i}] {camera_name}")
                
                cap.release()
        
        if not available_cameras:
            print("   ❌ Hiç kamera bulunamadı!")
        
        return available_cameras
    
    def refresh_cameras(self):
        """Kamera listesini yenile"""
        camera_list = self.get_available_cameras()
        
        if camera_list:
            print(f"🔄 Kamera listesi yenilendi:")
            for idx, name in camera_list:
                print(f"   [{idx}] {name}")
            print("   Sistemi yeniden başlatın")
        else:
            print("❌ Hiç kamera bulunamadı!")
    
    def refresh_microphones(self):
        """Mikrofon listesini yenile"""
        from src.speech_to_text import SpeechToText
        mic_list = SpeechToText.get_microphone_list()
        
        if mic_list:
            mic_options = [f"{idx}: {name}" for idx, name in mic_list]
            # Dropdown'u güncelle (mevcut seçimi koru)
            current = self.speech_mic_var.get()
            
            # Yeni listeyi set et
            tab = self.tabview.tab("🎤 Sesli Yazma")
            # Not: CTkOptionMenu dinamik güncelleme desteklemiyor, restart gerekli
            print("🔄 Mikrofon listesi yenilendi - Sistemi yeniden başlatın")
    
    def auto_detect_microphone(self):
        """Çalışan mikrofonu otomatik tespit et"""
        from src.speech_to_text import SpeechToText
        from tkinter import messagebox
        import threading
        
        # Uyarı göster
        result = messagebox.askyesno(
            "Otomatik Mikrofon Tespiti",
            "🔍 Her mikrofon sırayla test edilecek.\n\n"
            "⚠️ Test sırasında:\n"
            "• Mikrofonunuza konuşun\n"
            "• Sessiz kalırsanız mikrofon atlanır\n"
            "• İşlem 1-2 saniye/mikrofon sürer\n\n"
            "Devam etmek istiyor musunuz?"
        )
        
        if not result:
            return
        
        # Thread'de çalıştır (GUI kitlenmemesi için)
        def detect_thread():
            print("\n" + "="*60)
            print("🔍 OTOMATİK MİKROFON TESPİTİ BAŞLIYOR...")
            print("💬 ŞİMDİ MİKROFONA KONUŞUN!")
            print("="*60 + "\n")
            
            working_mic_idx = SpeechToText.detect_working_microphone(test_duration=1.5)
            
            if working_mic_idx is not None:
                # Çalışan mikrofon bulundu!
                mic_list = SpeechToText.get_microphone_list()
                mic_name = next((name for idx, name in mic_list if idx == working_mic_idx), "Bilinmeyen")
                
                # Dropdown'u güncelle
                self.speech_mic_var.set(f"{working_mic_idx}: {mic_name}")
                
                # Kullanıcıya bildir
                self.root.after(0, lambda: messagebox.showinfo(
                    "Başarılı!",
                    f"✅ Çalışan mikrofon bulundu!\n\n"
                    f"📍 Mikrofon #{working_mic_idx}\n"
                    f"🎤 {mic_name}\n\n"
                    f"Sistemi DURDUR → BAŞLAT yaparak aktif edin."
                ))
                
                print(f"\n✅ Seçilen mikrofon: [{working_mic_idx}] {mic_name}")
                
            else:
                # Hiçbir mikrofonda ses algılanmadı
                self.root.after(0, lambda: messagebox.showwarning(
                    "Mikrofon Bulunamadı",
                    "❌ Hiçbir mikrofonda ses algılanamadı!\n\n"
                    "🔧 Kontrol et:\n"
                    "• Mikrofon doğru takılı mı?\n"
                    "• Windows ses ayarlarından mikrofon aktif mi?\n"
                    "• Mikrofon seviyesi yeterli mi?\n"
                    "• Test sırasında konuştunuz mu?"
                ))
        
        # Thread başlat
        threading.Thread(target=detect_thread, daemon=True).start()
        
    def toggle_start(self):
        """Sistemi başlat/durdur (tam kapanma-açılma ile yeni ayarları uygula)"""
        if self.is_running:
            # Durdur - Tam kapanma
            self.stop_system()
        else:
            # Başlat - Sıfırdan başlatma
            try:
                # ÖNEMLİ: Config modülünü yeniden yükle (settings.json'dan ayarları al)
                print("🔄 Config yeniden yükleniyor (settings.json'dan)...")
                
                # Config modülünü importla
                import importlib
                if 'src.config' in sys.modules:
                    # Modül varsa reload et
                    importlib.reload(sys.modules['src.config'])
                    print("   ✅ Config reload edildi")
                else:
                    # İlk import
                    import src.config
                    print("   ✅ Config import edildi")
                
                # Global Config'i güncelle
                global Config, HandDetector, MouseController, GestureRecognizer, VolumeController, SpeechToText, OverlayDisplay
                from src.config import Config
                
                print(f"✅ Config yüklendi - Dead Zone: %{int(Config.CAMERA_CROP_LEFT*100)}")
                
                # Diğer modülleri de yeniden yükle
                print("🔄 Diğer modüller yeniden yükleniyor...")
                
                from src.hand_detector import HandDetector
                from src.mouse_controller import MouseController
                from src.gesture_recognizer import GestureRecognizer
                from src.volume_controller import VolumeController
                from src.speech_to_text import SpeechToText
                from src.overlay_display import OverlayDisplay
                
                print("✅ Tüm modüller hazır")
                
                # Eğer kamera açıksa önce kapat
                if self.camera:
                    try:
                        self.camera.release()
                    except:
                        pass
                    self.camera = None
                    time.sleep(0.5)  # Kameranın kapanması için bekle
                
                # Kamerayı başlat
                self.camera = cv2.VideoCapture(Config.CAMERA_INDEX)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
                self.camera.set(cv2.CAP_PROP_FPS, Config.CAMERA_FPS)
                self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                if not self.camera.isOpened():
                    messagebox.showerror("Hata", "Kamera açılamadı!")
                    return
                
                # Modülleri başlat (yeni Config ile)
                self.hand_detector = HandDetector(
                    max_hands=Config.MAX_HANDS,
                    detection_confidence=Config.DETECTION_CONFIDENCE,
                    tracking_confidence=Config.TRACKING_CONFIDENCE
                )
                
                self.mouse_controller = MouseController(
                    camera_width=Config.CAMERA_WIDTH,
                    camera_height=Config.CAMERA_HEIGHT,
                    smoothing_factor=Config.MOUSE_SMOOTHING,
                    speed_multiplier=Config.MOUSE_SPEED
                )
                
                self.gesture_recognizer = GestureRecognizer(
                    pinch_threshold=Config.PINCH_THRESHOLD,
                    stable_frames=Config.STABLE_FRAMES
                )
                
                self.volume_controller = VolumeController()
                
                # Sesli yazma sistemi (güvenli başlatma)
                self.speech_to_text = None
                if Config.SPEECH_ENABLED:
                    try:
                        print("\n🎤 Sesli yazma sistemi başlatılıyor...")
                        self.speech_to_text = SpeechToText(
                            language=Config.SPEECH_LANGUAGE,
                            microphone_index=Config.SPEECH_MICROPHONE_INDEX
                        )
                        
                        if self.speech_to_text.is_available():
                            print("✅ Sesli yazma sistemi aktif!")
                        else:
                            print("⚠️ Sesli yazma sistemi kullanılamıyor (mikrofon/kütüphane eksik)")
                            self.speech_to_text = None
                    except Exception as e:
                        print(f"❌ Sesli yazma başlatılamadı: {e}")
                        import traceback
                        traceback.print_exc()
                        self.speech_to_text = None
                else:
                    print("ℹ️ Sesli yazma devre dışı (Config.SPEECH_ENABLED=False)")
                
                # Overlay başlat (eğer aktifse)
                if self.overlay_var.get():  # ✅ overlay_var kullan
                    self.overlay = OverlayDisplay(position='topright')
                    self.overlay.start()
                    time.sleep(0.3)
                
                print("✨ Sistem sıfırdan başlatıldı - Yeni ayarlar uygulandı!")
                
                # Thread başlat
                self.running_flag = True
                self.is_running = True
                self.is_paused = False
                self.process_thread = threading.Thread(target=self.process_loop, daemon=True)
                self.process_thread.start()
                
                # UI güncelle
                self.start_button.configure(text="⏹️ DURDUR", fg_color="red", hover_color="darkred")
                self.pause_button.configure(state="normal")
                self.status_label.configure(text="✅ Sistem Çalışıyor")
                
            except Exception as e:
                messagebox.showerror("Başlatma Hatası", str(e))
                import traceback
                traceback.print_exc()
    
    def stop_system(self):
        """Sistemi tamamen kapat (tüm modülleri yok et)"""
        print("🛑 Sistem kapatılıyor...")
        
        # Flag'leri ayarla
        self.running_flag = False
        self.is_running = False
        
        # UI'yi HEMEN güncelle
        self.start_button.configure(text="▶️ BAŞLAT", fg_color="green", hover_color="darkgreen")
        self.pause_button.configure(state="disabled")
        self.status_label.configure(text="⏹️ Sistem Durduruldu")
        self._update_label(None)  # Kamera kapalı mesajı göster
        
        # Cleanup işlemini 100ms sonra yap (UI güncellensin diye)
        self.root.after(100, self._cleanup_resources)
    
    def _cleanup_resources(self):
        """Sistem kaynaklarını temizle (main thread'de çalışır)"""
        try:
            print("🧹 Cleanup başlıyor...")
            
            # Thread'in bitmesini kontrol et (blocking join kullanma!)
            if self.process_thread and self.process_thread.is_alive():
                print("⏳ Thread hala çalışıyor, 200ms sonra tekrar kontrol...")
                # Thread hala çalışıyor - 200ms sonra tekrar dene
                self.root.after(200, self._cleanup_resources)
                return
            
            # Thread bitti, devam edebiliriz
            if self.process_thread:
                print("✅ Thread durduruldu")
                self.process_thread = None
            
            # Kamerayı kapat
            if self.camera:
                print("📷 Kamera kapatılıyor...")
                self.camera.release()
                self.camera = None
                print("✅ Kamera kapatıldı")
            
            # Overlay'i kapat
            if self.overlay:
                print("🔴 Overlay kapatılıyor...")
                self.overlay.stop()
                self.overlay = None
                print("✅ Overlay kapatıldı")
            
            # Sesli yazma sistemini temizle
            if self.speech_to_text:
                print("🎤 Sesli yazma kapatılıyor...")
                try:
                    self.speech_to_text.cleanup()
                except:
                    pass
                self.speech_to_text = None
                print("✅ Sesli yazma kapatıldı")
            
            # Tüm modülleri yok et (yeni başlatmada sıfırdan oluşturulacak)
            self.hand_detector = None
            self.mouse_controller = None
            self.gesture_recognizer = None
            self.volume_controller = None
            # speech_to_text zaten yukarıda None yapıldı
            
            print("🛑 Sistem tamamen kapatıldı - Tüm modüller yok edildi")
            print("✅ GUI açık - BAŞLAT butonuna basarak yeniden başlatabilirsiniz")
            
        except Exception as e:
            print(f"❌ Cleanup hatası: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_pause(self):
        """Oynat/Duraklat"""
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.pause_button.configure(text="▶️ DEVAM ET", fg_color="green", hover_color="darkgreen")
            self.status_label.configure(text="⏸️ Sistem Duraklatıldı")
        else:
            self.pause_button.configure(text="⏸️ DURAKLAT", fg_color=("gray75", "gray25"))
            self.status_label.configure(text="✅ Sistem Çalışıyor")
    
    def toggle_overlay(self):
        """Overlay göster/gizle"""
        # overlay_var zaten checkbox tarafından güncelleniyor
        
        if self.is_running:
            if self.overlay_var.get() and not self.overlay:  # ✅ overlay_var
                self.overlay = OverlayDisplay(position='topright')
                self.overlay.start()
            elif not self.overlay_var.get() and self.overlay:  # ✅ overlay_var
                self.overlay.stop()
                self.overlay = None
    
    def process_loop(self):
        """Ana işlem döngüsü (thread'de çalışır)"""
        # Durum değişkenleri
        self.hand_was_present = False
        self.double_click_performed = False
        self.is_scrolling = False
        self.fist_detected = False
        self.right_hand_paused = False  # Sağ el yumruk jesti pause (sadece mouse)
        self.global_paused = False
        self.global_pause_detected = False
        self.left_hand_enabled = False
        self.left_fist_detected = False
        self.last_left_gesture = None
        self.prev_volume_y = None
        self.is_volume_mode = False
        self.last_volume_time = 0
        self.mute_pinch_detected = False
        self.media_pinch_detected = False
        self.microphone_pinch_detected = False  # Mikrofon toggle için
        self.last_click_time = 0
        self.speech_in_progress = False
        
        # Sesli yazma için pending flag (thread başlatmadan)
        self.speech_pending = False
        self.speech_worker_running = False
        
        # Sesli yazma worker thread'i (sürekli çalışır, flag bekler)
        def speech_worker():
            while self.running_flag:
                if self.speech_pending and not self.speech_worker_running:
                    self.speech_worker_running = True
                    self.speech_pending = False
                    try:
                        self.speech_to_text.dictate_mode(auto_enter=Config.SPEECH_AUTO_ENTER)
                    except Exception as e:
                        print(f"❌ Sesli yazma hatası: {e}")
                    finally:
                        self.speech_worker_running = False
                time.sleep(0.05)  # 50ms check interval
        
        # Worker thread'i BAŞTAN başlat (bir kere)
        if self.speech_to_text:
            threading.Thread(target=speech_worker, daemon=True).start()
            
            # OTOMATIK MİKROFON BAŞLATMA (Config'de açıksa)
            if Config.SPEECH_AUTO_START:
                print("\n🎤 Mikrofon otomatik başlatılıyor...")
                self.speech_to_text.start_continuous_listening(auto_enter=Config.SPEECH_AUTO_ENTER)
        
        # FPS için
        prev_time = 0
        fps = 0
        
        while self.running_flag:
            if self.is_paused:
                time.sleep(0.1)
                continue
            
            success, frame = self.camera.read()
            if not success:
                break
            
            # Görüntüyü çevir
            if self.flip_camera_var.get():  # ✅ GUI değişkeni
                frame = cv2.flip(frame, 1)
            
            # El algıla
            self.hand_detector.update_image_shape(frame)
            frame = self.hand_detector.find_hands(frame, draw=self.show_landmarks_var.get())  # ✅ GUI değişkeni
            
            # El var mı kontrol et
            if self.hand_detector.is_hand_present():
                # El yeni mi göründü?
                if not self.hand_was_present:
                    self.mouse_controller.reset_smoothing()
                    self.gesture_recognizer.reset_gesture_history()
                    self.hand_was_present = True
                
                # Kaç el var?
                hand_count = self.hand_detector.get_hand_count()
                
                # GLOBAL PAUSE/RESUME KONTROLÜ
                if hand_count == 2:
                    left_hand_idx = self.hand_detector.get_hand_by_label("Left")
                    right_hand_idx = self.hand_detector.get_hand_by_label("Right")
                    
                    if left_hand_idx is not None and right_hand_idx is not None:
                        left_landmarks = self.hand_detector.get_all_landmarks(left_hand_idx)
                        right_landmarks = self.hand_detector.get_all_landmarks(right_hand_idx)
                        
                        is_global_pause = self.gesture_recognizer.is_global_pause_gesture(
                            left_landmarks, right_landmarks
                        )
                        
                        if is_global_pause and not self.global_pause_detected:
                            self.global_paused = not self.global_paused
                            self.global_pause_detected = True
                            
                            if self.global_paused:
                                print("⏸️  GLOBAL PAUSE: TÜM KONTROLLER DURDURULDU")
                                if self.mouse_controller.left_button_pressed:
                                    self.mouse_controller.left_release()
                                if self.mouse_controller.right_button_pressed:
                                    self.mouse_controller.right_release()
                                self.root.after(0, lambda: self.status_label.configure(
                                    text="Durum: GLOBAL PAUSE - İki elin işaret parmağını tekrar birleştir"
                                ))
                            else:
                                print("▶️  GLOBAL RESUME: TÜM KONTROLLER AKTİF")
                                self.root.after(0, lambda: self.status_label.configure(
                                    text="Durum: Çalışıyor"
                                ))
                        
                        elif not is_global_pause:
                            self.global_pause_detected = False
                
                # EL İŞLEMLERİ (sadece global pause yoksa)
                if not self.global_paused:
                    # SAĞ EL
                    right_hand_idx = self.hand_detector.get_hand_by_label("Right")
                    if right_hand_idx is not None:
                        landmarks = self.hand_detector.get_all_landmarks(right_hand_idx)
                        if landmarks:
                            self.process_right_hand(landmarks)
                    
                    # SOL EL
                    left_hand_idx = self.hand_detector.get_hand_by_label("Left")
                    if left_hand_idx is not None:
                        landmarks = self.hand_detector.get_all_landmarks(left_hand_idx)
                        if landmarks:
                            self.process_left_hand(landmarks)
            
            else:
                if self.hand_was_present:
                    self.hand_was_present = False
            
            # FPS hesapla
            current_time = time.time()
            fps = int(1 / (current_time - prev_time)) if prev_time > 0 else 0
            prev_time = current_time
            
            # FPS ve gesture bilgilerini kaydet (update_camera_display için)
            self._current_fps = fps
            self._current_gesture = self.gesture_recognizer.get_gesture_name() if hasattr(self.gesture_recognizer, 'get_gesture_name') else ""
            
            # Overlay güncelle
            self._update_overlay(fps)
            
            # Kamera görüntüsünü güncelle
            self.update_camera_display(frame)
            
            time.sleep(0.01)
    
    def process_right_hand(self, landmarks):
        """Sağ el ile mouse kontrolünü işler"""
        # Avuç içi merkezi
        wrist = landmarks[0]  # Config.WRIST
        palm_base = landmarks[9]  # Config.PALM_CENTER
        palm_x = (wrist[0] + palm_base[0]) // 2
        palm_y = (wrist[1] + palm_base[1]) // 2
        
        # Yumruk kontrolü (Pause/Resume - SADECE MOUSE KONTROLÜ)
        is_fist = self.gesture_recognizer.is_fist(landmarks)
        
        if is_fist and not self.fist_detected:
            self.right_hand_paused = not self.right_hand_paused  # Sadece mouse pause
            self.fist_detected = True
            
            if self.right_hand_paused:
                print("⏸️  SAĞ EL: Mouse kontrolü DURAKLADI (Kamera çalışmaya devam ediyor)")
                if self.mouse_controller.left_button_pressed:
                    self.mouse_controller.left_release()
                if self.mouse_controller.right_button_pressed:
                    self.mouse_controller.right_release()
                self.root.after(0, lambda: self.status_label.configure(
                    text="Durum: SAĞ EL Mouse Durakladı - Kamera aktif"
                ))
            else:
                print("▶️  SAĞ EL: Mouse kontrolü DEVAM EDİYOR")
                self.root.after(0, lambda: self.status_label.configure(text="Durum: Çalışıyor"))
        
        elif not is_fist:
            self.fist_detected = False
        
        # Mouse kontrolü (sadece pause değilse)
        if not self.right_hand_paused:  # right_hand_paused kontrolü
            # Scroll kontrolü
            is_scroll = self.gesture_recognizer.is_scroll_gesture(landmarks)
            
            if is_scroll:
                # Scroll modu
                self.gesture_recognizer.set_gesture_name("Scroll")
                index_tip = landmarks[8]
                scroll_y = index_tip[1]
                _, screen_scroll_y = self.mouse_controller.map_coordinates(index_tip[0], scroll_y)
                self.mouse_controller.scroll(screen_scroll_y)
                self.is_scrolling = True
                
                if self.mouse_controller.left_button_pressed:
                    self.mouse_controller.left_release()
                if self.mouse_controller.right_button_pressed:
                    self.mouse_controller.right_release()
            
            else:
                # Normal mod - mouse hareketi
                if self.is_scrolling:
                    self.mouse_controller.reset_scroll()
                    self.is_scrolling = False
                
                # Mouse hareketi
                self.mouse_controller.move_mouse(palm_x, palm_y)
                self.gesture_recognizer.set_gesture_name("Mouse Hareketi")
            
            # Tıklama işlemleri (scroll değilse)
            if not is_scroll:
                is_double_click = self.gesture_recognizer.is_double_click(landmarks)
                is_left_pinch = self.gesture_recognizer.is_left_click(landmarks)
                is_right_pinch = self.gesture_recognizer.is_right_click(landmarks)
                
                if is_double_click:
                    self.gesture_recognizer.set_gesture_name("Çift Tıklama")
                    if not self.double_click_performed:
                        if self.mouse_controller.left_button_pressed:
                            self.mouse_controller.left_release()
                        if self.mouse_controller.right_button_pressed:
                            self.mouse_controller.right_release()
                        
                        self.mouse_controller.double_click()
                        self.double_click_performed = True
                        print("✨ Çift tıklama yapıldı!")
                
                elif is_left_pinch:
                    self.gesture_recognizer.set_gesture_name("Sol Tıklama")
                    self.mouse_controller.left_press()
                    
                    if self.mouse_controller.right_button_pressed:
                        self.mouse_controller.right_release()
                    self.double_click_performed = False
                
                elif is_right_pinch:
                    self.gesture_recognizer.set_gesture_name("Sağ Tıklama")
                    self.mouse_controller.right_press()
                    if self.mouse_controller.left_button_pressed:
                        self.mouse_controller.left_release()
                    self.double_click_performed = False
                
                else:
                    if self.mouse_controller.left_button_pressed:
                        self.mouse_controller.left_release()
                    if self.mouse_controller.right_button_pressed:
                        self.mouse_controller.right_release()
                    self.double_click_performed = False
    
    def process_left_hand(self, landmarks):
        """Sol el ile ses kontrolünü işler"""
        # Yumruk kontrolü (Enable/Disable)
        is_fist = self.gesture_recognizer.is_fist(landmarks)
        
        if is_fist and not self.left_fist_detected:
            self.left_hand_enabled = not self.left_hand_enabled
            self.left_fist_detected = True
            
            if self.left_hand_enabled:
                print("🔊 SOL EL: Ses kontrolü ETKİNLEŞTİRİLDİ")
            else:
                print("🔇 SOL EL: Ses kontrolü DEVRE DIŞI")
                self.prev_volume_y = None
                self.is_volume_mode = False
        
        elif not is_fist:
            self.left_fist_detected = False
        
        # Ses ve media kontrolü (sadece etkinse)
        if self.left_hand_enabled and not is_fist:
            # MİKROFON JESTİ KALDIRILDI - Otomatik başlıyor artık
            
            # ÖNCELİK 1: 3 PARMAK KONTROLÜ (MUTE) - En spesifik jest
            is_mute_pinch = self.gesture_recognizer.is_mute_gesture(landmarks)
            
            # 2 parmak (media)
            is_media_pinch = self.gesture_recognizer.is_media_play_pause_gesture(landmarks)
            
            if is_mute_pinch and not self.mute_pinch_detected:
                self.gesture_recognizer.set_gesture_name("Sessiz/Aç")
                self.volume_controller.toggle_mute()
                self.mute_pinch_detected = True
                self.last_left_gesture = "mute"
                self.is_volume_mode = False
                self.prev_volume_y = None
                self.media_pinch_detected = False
            
            elif not is_mute_pinch:
                self.mute_pinch_detected = False
                
                if is_media_pinch and not self.media_pinch_detected:
                    self.gesture_recognizer.set_gesture_name("Oynat/Duraklat")
                    self.volume_controller.media_play_pause()
                    self.media_pinch_detected = True
                    self.last_left_gesture = "media"
                    self.is_volume_mode = False
                    self.prev_volume_y = None
                
                elif not is_media_pinch:
                    self.media_pinch_detected = False
                    
                    # Ses kontrol modu (sürekli otomatik)
                    if self.gesture_recognizer.is_volume_up_gesture(landmarks):
                        index_tip = landmarks[8]
                        current_y = index_tip[1]
                        
                        if self.prev_volume_y is None:
                            # İlk giriş - başlangıç pozisyonunu kaydet
                            self.prev_volume_y = current_y
                            self.is_volume_mode = True
                            self.last_left_gesture = "volume_mode"
                            self.gesture_recognizer.set_gesture_name("Ses Kontrolü")
                        else:
                            y_diff = self.prev_volume_y - current_y
                            
                            # Yön belirleme - bir kere hareket ettir, ses otomatik devam etsin
                            if y_diff > 10 and self.last_left_gesture != "volume_up_continuous":
                                # Yukarı hareket algılandı - artırma moduna geç
                                print("🔊 Yukarı hareket algılandı → Ses OTOMATIK ARTIYOR")
                                self.last_left_gesture = "volume_up_continuous"
                                self.gesture_recognizer.set_gesture_name("Ses Artırma")
                            
                            elif y_diff < -10 and self.last_left_gesture != "volume_down_continuous":
                                # Aşağı hareket algılandı - azaltma moduna geç
                                print("🔉 Aşağı hareket algılandı → Ses OTOMATIK AZALIYOR")
                                self.last_left_gesture = "volume_down_continuous"
                                self.gesture_recognizer.set_gesture_name("Ses Azaltma")
                            
                            # Mod belirlendiyse, otomatik devam et
                            if self.last_left_gesture == "volume_up_continuous":
                                self.volume_controller.volume_up()
                                self.gesture_recognizer.set_gesture_name("Ses Artırma")
                            elif self.last_left_gesture == "volume_down_continuous":
                                self.volume_controller.volume_down()
                                self.gesture_recognizer.set_gesture_name("Ses Azaltma")
                    
                    else:
                        # Jest bırakıldı - modu sıfırla
                        self.prev_volume_y = None
                        self.is_volume_mode = False
                        if self.last_left_gesture in ["volume_up_continuous", "volume_down_continuous"]:
                            print("⏹️  Ses kontrolü durduruldu")
                            self.gesture_recognizer.set_gesture_name("")
                        self.last_left_gesture = None
    
    def _update_overlay(self, fps):
        """Overlay display'i güncelle"""
        if not self.overlay:
            return
        
        # Sağ el durumu
        right_hand_idx = self.hand_detector.get_hand_by_label("Right")
        if right_hand_idx is not None:
            if self.global_paused:
                right_status = "GLOBAL PAUSE"
                right_color = "red"
            elif hasattr(self, 'right_hand_paused') and self.right_hand_paused:
                right_status = "MOUSE DURAKLADI"
                right_color = "orange"
            else:
                right_status = "AKTİF"
                right_color = "green"
        else:
            right_status = "YOK"
            right_color = "red"
        
        # Sol el durumu
        left_hand_idx = self.hand_detector.get_hand_by_label("Left")
        if left_hand_idx is not None:
            if self.global_paused:
                left_status = "GLOBAL PAUSE"
                left_color = "red"
            elif self.left_hand_enabled:
                left_status = "AKTİF (SES)"
                left_color = "green"
            else:
                left_status = "KAPALI"
                left_color = "orange"
        else:
            left_status = "YOK"
            left_color = "red"
        
        # Güncel jest
        current_gesture = self.gesture_recognizer.get_current_gesture_name()
        
        # Overlay'i güncelle
        self.overlay.update(
            fps=fps,
            right_hand=right_status,
            right_hand_color=right_color,
            left_hand=left_status,
            left_hand_color=left_color,
            global_pause=self.global_paused,
            current_gesture=current_gesture,
            speech_active=self.speech_to_text.is_continuous_active() if self.speech_to_text else False
        )
    
    def _trigger_speech_to_text(self):
        """Sesli yazma tetikleyici (arka plan thread'inde) - Optimize edilmiş"""
        # Güvenlik kontrolleri
        if not self.speech_to_text:
            print("❌ SpeechToText nesnesi yok!")
            return
        
        if not self.speech_to_text.is_available():
            print("❌ Mikrofon/kütüphane kullanılamıyor!")
            return
        
        if self.speech_in_progress:
            print("⚠️ Sesli yazma zaten devam ediyor, atlandı")
            return
        
        try:
            print("\n" + "="*60)
            print("🎙️ SESLİ YAZMA TETİKLENDİ (Sol Tıklama)")
            print("="*60)
            print(f"📋 Ayarlar:")
            print(f"   Enabled: {Config.SPEECH_ENABLED}")
            print(f"   Dil: {Config.SPEECH_LANGUAGE}")
            print(f"   Timeout: {Config.SPEECH_TIMEOUT}s")
            print(f"   Otomatik Enter: {Config.SPEECH_AUTO_ENTER}")
            print(f"   Auto Trigger: {Config.SPEECH_AUTO_TRIGGER}")
            print("="*60)
            
            self.speech_in_progress = True
            
            print("⏳ 0.5 saniye bekleniyor (imleç hazırlansın)...")
            time.sleep(0.5)
            
            print("🎤 Mikrofon dinlemeye başlıyor...")
            text = self.speech_to_text.listen_once(timeout=Config.SPEECH_TIMEOUT)
            
            if text:
                print(f"\n⌨️ Metin yazılıyor: '{text}'")
                self.speech_to_text.type_text(text, auto_enter=Config.SPEECH_AUTO_ENTER)
                print("✅ Sesli yazma tamamlandı!")
            else:
                print("❌ Metin alınamadı (timeout veya tanınmadı)")
            
            print("="*60 + "\n")
        
        except Exception as e:
            print("="*60)
            print(f"❌ SESLİ YAZMA HATASI: {e}")
            print(f"   Hata tipi: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            print("="*60 + "\n")
        finally:
            self.speech_in_progress = False
            print("🔴 Sesli yazma thread'i sonlandı\n")
    
    def update_camera_display(self, frame):
        """Kamera görüntüsünü GUI'de güncelle"""
        # Dead Zone göster - aktif alanı yeşil dikdörtgen ile işaretle
        h, w = frame.shape[:2]
        
        # Aktif alan sınırlarını hesapla
        active_left = int(w * Config.CAMERA_CROP_LEFT)
        active_right = int(w * (1 - Config.CAMERA_CROP_RIGHT))
        active_top = int(h * Config.CAMERA_CROP_TOP)
        active_bottom = int(h * (1 - Config.CAMERA_CROP_BOTTOM))
        
        # Frame'in kopyasını al (orijinali bozmamak için)
        frame_with_rect = frame.copy()
        
        # Yeşil dikdörtgen çiz (aktif alan = ekranınızı temsil eder)
        cv2.rectangle(frame_with_rect, 
                     (active_left, active_top), 
                     (active_right, active_bottom), 
                     (0, 255, 0),  # Yeşil renk (BGR)
                     3)  # Kalınlık
        
        # Dikdörtgenin içine açıklama metni ekle
        text = "EKRAN ALANI"
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, 0.7, 2)[0]
        text_x = active_left + 10
        text_y = active_top + 30
        
        # Metin arka planı (siyah kutu)
        cv2.rectangle(frame_with_rect,
                     (text_x - 5, text_y - text_size[1] - 5),
                     (text_x + text_size[0] + 5, text_y + 5),
                     (0, 0, 0),
                     -1)  # Dolu kutu
        
        # Metni yaz (yeşil)
        cv2.putText(frame_with_rect, text, (text_x, text_y),
                   font, 0.7, (0, 255, 0), 2)
        
        # Alt kısma Dead Zone yüzdesini yaz
        deadzone_percent = int(Config.CAMERA_CROP_LEFT * 100)
        info_text = f"Dead Zone: %{deadzone_percent}"
        cv2.putText(frame_with_rect, info_text, (10, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # FPS göster (eğer ayar aktifse)
        if hasattr(self, 'show_fps_var') and self.show_fps_var.get():
            # FPS bilgisini self içinden al (process_loop'ta set ediyoruz)
            fps = getattr(self, '_current_fps', 0)
            if fps > 0:
                fps_text = f"FPS: {fps}"
                cv2.putText(frame_with_rect, fps_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Jest adını göster (eğer ayar aktifse)
        if hasattr(self, 'show_gesture_var') and self.show_gesture_var.get():
            current_gesture = getattr(self, '_current_gesture', "")
            if current_gesture:
                gesture_text = f"Jest: {current_gesture}"
                gesture_size = cv2.getTextSize(gesture_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                gesture_x = w - gesture_size[0] - 10
                cv2.putText(frame_with_rect, gesture_text, (gesture_x, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # BGR'den RGB'ye çevir
        frame_rgb = cv2.cvtColor(frame_with_rect, cv2.COLOR_BGR2RGB)
        
        # PIL Image'e çevir
        image = Image.fromarray(frame_rgb)
        
        # Boyutlandır (800x600)
        image = image.resize((800, 600), Image.Resampling.LANCZOS)
        
        # PhotoImage'e çevir
        photo = ImageTk.PhotoImage(image)
        
        # Label'ı güncelle (main thread'de)
        self.root.after(0, lambda: self._update_label(photo))
    
    def _update_label(self, photo):
        """Label'ı güncelle (main thread)"""
        if photo:
            self.camera_label.configure(image=photo, text="")
            self.camera_label.image = photo  # Referansı tut
        else:
            self.camera_label.configure(image="", text="Kamera Kapalı")
    
    def apply_settings(self):
        """Ayarları Config'e uygula (yeniden başlatmada kullanılacak)"""
        # Kamera index'ini al (dropdown'dan)
        camera_str = self.camera_index_var.get()  # Format: "0: Kamera İsmi"
        try:
            camera_index = int(camera_str.split(":")[0].strip())  # "0: Kamera İsmi" -> 0
            Config.CAMERA_INDEX = camera_index
        except:
            Config.CAMERA_INDEX = 0
        
        Config.CAMERA_FPS = self.fps_var.get()
        Config.CAMERA_CROP_LEFT = self.deadzone_var.get()
        Config.CAMERA_CROP_RIGHT = self.deadzone_var.get()
        Config.CAMERA_CROP_TOP = self.deadzone_var.get()
        Config.CAMERA_CROP_BOTTOM = self.deadzone_var.get()
        Config.MAX_HANDS = self.max_hands_var.get()
        
        Config.MOUSE_SPEED = self.mouse_speed_var.get()
        Config.EMA_MIN = self.ema_min_var.get()
        Config.EMA_MAX = self.ema_max_var.get()
        Config.EMA_FUNCTION = self.ema_func_var.get()
        
        Config.SHOW_FPS = self.show_fps_var.get()
        Config.SHOW_LANDMARKS = self.show_landmarks_var.get()
        Config.SHOW_GESTURE_TEXT = self.show_gesture_var.get()
        Config.FLIP_CAMERA = self.flip_camera_var.get()
        
        Config.VOLUME_STEP = self.volume_step_var.get()
        
        # Sesli yazma - sadece dil ve mikrofon (diğerleri Config'de sabit)
        Config.SPEECH_LANGUAGE = self.speech_lang_var.get()
        
        # Mikrofon index'ini al (dropdown'dan)
        mic_str = self.speech_mic_var.get()  # Format: "0: Mikrofon Adı"
        try:
            mic_index = int(mic_str.split(":")[0].strip())
            Config.SPEECH_MICROPHONE_INDEX = mic_index
        except:
            Config.SPEECH_MICROPHONE_INDEX = None
        
        print("⚙️ Ayarlar Config'e yazıldı (yeniden başlatmada uygulanacak)")
    
    def save_settings(self):
        """Ayarları kalıcı olarak kaydet (settings.json)"""
        self.apply_settings()
        
        try:
            # Ayarları dictionary olarak topla
            settings = {
                'CAMERA_INDEX': Config.CAMERA_INDEX,
                'CAMERA_FPS': Config.CAMERA_FPS,
                'CAMERA_CROP_LEFT': Config.CAMERA_CROP_LEFT,
                'CAMERA_CROP_RIGHT': Config.CAMERA_CROP_RIGHT,
                'CAMERA_CROP_TOP': Config.CAMERA_CROP_TOP,
                'CAMERA_CROP_BOTTOM': Config.CAMERA_CROP_BOTTOM,
                'MAX_HANDS': Config.MAX_HANDS,
                'MOUSE_SPEED': Config.MOUSE_SPEED,
                'EMA_MIN': Config.EMA_MIN,
                'EMA_MAX': Config.EMA_MAX,
                'EMA_FUNCTION': Config.EMA_FUNCTION,
                'SHOW_FPS': Config.SHOW_FPS,
                'SHOW_LANDMARKS': Config.SHOW_LANDMARKS,
                'SHOW_GESTURE_TEXT': Config.SHOW_GESTURE_TEXT,
                'FLIP_CAMERA': Config.FLIP_CAMERA,
                'VOLUME_STEP': Config.VOLUME_STEP,
                'SPEECH_LANGUAGE': Config.SPEECH_LANGUAGE,
                'SPEECH_MICROPHONE_INDEX': Config.SPEECH_MICROPHONE_INDEX,
            }
            
            # settings.json'a kaydet (hem normal hem EXE modunda çalışır)
            if self.config_manager.save_settings(settings):
                # Ayrıca config.py'yi de güncelle (sadece normal modda çalışır)
                self.config_manager.update_config_file(settings)
                
                if self.is_running:
                    messagebox.showinfo("Kaydedildi", 
                        "💾 Ayarlar kalıcı olarak kaydedildi!\n\n"
                        "⚠️ Ayarların aktif olması için:\n"
                        "1. Uygulamayı tamamen KAPATIN\n"
                        "2. Uygulamayı yeniden AÇIN\n\n"
                        "✅ Yeni açılışta ayarlar yüklenecek")
                else:
                    messagebox.showinfo("Kaydedildi",
                        "💾 Ayarlar kalıcı olarak kaydedildi!\n\n"
                        "⚠️ Ayarların aktif olması için:\n"
                        "• Uygulamayı KAPATIN ve yeniden AÇIN\n\n"
                        "✅ Yeni açılışta ayarlar yüklenecek")
            else:
                messagebox.showerror("Hata", "Ayarlar kaydedilemedi!")
            
        except Exception as e:
            messagebox.showerror("Kayıt Hatası", f"Ayarlar kaydedilemedi:\n{str(e)}")
    
    def run(self):
        """GUI'yi çalıştır"""
        # Kapanma kontrolü
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def show_help(self):
        """Yardım penceresini göster - Tüm jestleri açıkla"""
        help_window = ctk.CTkToplevel(self.root)
        help_window.title("📖 El Hareketleri Rehberi")
        help_window.geometry("700x750")
        help_window.transient(self.root)
        help_window.grab_set()
        
        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(help_window, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Başlık
        title = ctk.CTkLabel(
            scroll_frame,
            text="🖐️ El Hareketleri Rehberi",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(0, 20))
        
        # SAĞ EL - Mouse Kontrolleri
        self._add_help_section(scroll_frame, "🖱️ SAĞ EL - Mouse Kontrolleri", [
            ("✋ Açık El", "Mouse hareket ettirir (avuç içi ile kontrol)"),
            ("👌 İşaret + Baş Parmak (Pinch)", "Sol tıklama (basılı tutma destekli)"),
            ("✌️ Orta + Yüzük Parmak (Pinch)", "Sağ tıklama"),
            ("🤟 3 Parmak Birlikte", "Çift tıklama (hızlı)"),
            ("☝️ İşaret + Orta Parmağı", "Scroll modu (yukarı/aşağı kaydırma)"),
            ("✊ Yumruk", "Mouse kontrolünü DURAKLAT/DEVAM (kamera çalışır)"),
        ])
        
        # SOL EL - Ses ve Medya Kontrolleri
        self._add_help_section(scroll_frame, "🔊 SOL EL - Ses ve Medya Kontrolleri", [
            ("✊ Yumruk", "Sol el kontrollerini AÇ/KAPAT"),
            ("", "⚠️ Önce yumruk yapıp kontrolleri açmalısınız!"),
            ("☝️ İşaret + Orta Parmağı Yukarı", "SES KONTROL MODU:"),
            ("   • Yukarı Hareket", "Ses sürekli ARTAR"),
            ("   • Aşağı Hareket", "Ses sürekli AZALIR"),
            ("👌 İşaret + Baş (2 Parmak)", "Medya oynat/duraklat"),
            ("🤟 İşaret + Orta + Baş (3 Parmak)", "Sesi aç/kapat (mute toggle)"),
        ])
        
        # İKİ EL - Global Kontrol
        self._add_help_section(scroll_frame, "🙌 İKİ EL - Global Kontrol", [
            ("👆👆 İki İşaret Parmağı Birleşince", "GLOBAL PAUSE - Tüm sistem durur"),
            ("   (Tekrar birleştirin)", "GLOBAL RESUME - Sistem devam eder"),
        ])
        
        # SESLI YAZMA
        self._add_help_section(scroll_frame, "🎤 SESLİ YAZMA SİSTEMİ", [
            ("🔴 Otomatik Aktif", "Mikrofon sistem başladığında otomatik açılır"),
            ("💬 Sürekli Dinleme", "Konuştuğunuz her şey anında yazılır"),
            ("⚙️ Ayarlar", "Mikrofon ve dil seçimi 'Sesli Yazma' sekmesinde"),
        ])
        
        # İPUÇLARI
        self._add_help_section(scroll_frame, "💡 İPUÇLARI", [
            ("📹 Yeşil Dikdörtgen", "Kamerada gördüğünüz yeşil alan = ekranınız"),
            ("🎯 Dead Zone", "Kenar kırpma ayarı - hassasiyeti artırır"),
            ("⏸️ Duraklatma", "Sağ el: Sadece mouse | Global: Her şey durur"),
            ("🔄 Ayar Değişikliği", "Kaydet → Uygulamayı kapat/aç"),
            ("📊 Overlay Panel", "Sağ üstte el durumlarını gösterir"),
        ])
        
        # Kapat butonu
        close_button = ctk.CTkButton(
            help_window,
            text="✅ Anladım",
            command=help_window.destroy,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        close_button.pack(pady=10)
    
    def _add_help_section(self, parent, title, items):
        """Yardım bölümü ekle"""
        # Bölüm başlığı
        section_frame = ctk.CTkFrame(parent, fg_color="#2B5278", corner_radius=10)
        section_frame.pack(fill="x", pady=(10, 5))
        
        section_title = ctk.CTkLabel(
            section_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        section_title.pack(padx=15, pady=10, anchor="w")
        
        # İçerik
        content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        content_frame.pack(fill="x", pady=(0, 15))
        
        for gesture, description in items:
            item_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            item_frame.pack(fill="x", pady=2)
            
            if gesture:  # Boş değilse
                gesture_label = ctk.CTkLabel(
                    item_frame,
                    text=gesture,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    width=200,
                    anchor="w"
                )
                gesture_label.pack(side="left", padx=(10, 5))
            
            desc_label = ctk.CTkLabel(
                item_frame,
                text=description,
                font=ctk.CTkFont(size=12),
                anchor="w",
                text_color="lightgray"
            )
            desc_label.pack(side="left", padx=(5 if gesture else 15, 10), fill="x", expand=True)
    
    def on_closing(self):
        """Pencere kapatılırken"""
        if self.is_running:
            if messagebox.askokcancel("Çıkış", "Sistem çalışıyor. Çıkmak istediğinizden emin misiniz?"):
                self.stop_system()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    """Ana giriş noktası"""
    app = HandMouseGUI()
    app.run()


if __name__ == "__main__":
    main()
