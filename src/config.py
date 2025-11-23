"""
Konfigürasyon Ayarları
Bu modül, Hand Mouse projesindeki tüm ayarlanabilir parametreleri içerir.
"""

import json
import sys
import os
from pathlib import Path


class Config:
    """Uygulama konfigürasyon sınıfı"""
    
    # ==================== GENEL AYARLAR ====================
    DEBUG_MODE = False                  # Debug modu (log mesajları için)
    
    # ==================== KAMERA AYARLARI ====================
    CAMERA_INDEX = 0                   # Kullanılacak kamera ID'si (varsayılan: 0)
    CAMERA_WIDTH = 640                  # Kamera görüntü genişliği (piksel)
    CAMERA_HEIGHT = 480                 # Kamera görüntü yüksekliği (piksel)
    CAMERA_FPS = 60                     # Hedef FPS (kameranın desteklemesi gerekir)
    
    # ==================== MEDIAPIPE AYARLARI ====================
    DETECTION_CONFIDENCE = 0.5          # El algılama güven eşiği (düşürüldü = daha hızlı)
    TRACKING_CONFIDENCE = 0.5           # El takip güven eşiği (0.0 - 1.0)
    MAX_HANDS = 2                       # Maksimum algılanacak el sayısı (2 = sağ+sol)
    
    # ==================== MOUSE KONTROL AYARLARI ====================
    MOUSE_SMOOTHING = 2                 # EMA smoothing için buffer (artık kullanılmıyor ama uyumluluk için)
    MOUSE_SPEED = 3.0                   # Mouse hassasiyeti çarpanı (optimize edildi)
    SCREEN_MARGIN = 100                 # Ekran kenarlarından güvenli mesafe (piksel)
    
    # ==================== DİNAMİK EMA AYARLARI (Sürekli Fonksiyon) ====================
    # EMA değeri hıza göre sürekli hesaplanır (interpolasyon yerine matematiksel fonksiyon)
    
    EMA_MIN = 0.010000000000000009      # Minimum EMA alpha (çok yavaş hareket)
    EMA_MAX = 0.6000000000000001# Maksimum EMA alpha (çok hızlı hareket)
    
    SPEED_MIN = 10                      # Minimum hız eşiği (piksel/frame)
    SPEED_MAX = 350                     # Maksimum hız eşiği (piksel/frame)
    
    # EMA Fonksiyon Tipi: 'linear', 'exponential', 'sigmoid'
    EMA_FUNCTION = 'sigmoid'            # Sigmoid = Yumuşak geçişler, doğal hissiyat
    
    # Sigmoid fonksiyon parametreleri (EMA_FUNCTION = 'sigmoid' ise)
    SIGMOID_STEEPNESS = 0.05            # Eğrinin dikliği (0.03-0.1 arası önerilir)
    SIGMOID_MIDPOINT = 60               # Orta nokta hızı (piksel/frame)
    
    # ==================== KAMERA HAREKET ALANI (Dead Zone) ====================
    # Kameranın ortasındaki aktif alanı belirler (kenarları kırpar)
    # Minimum %1, maksimum %49 (0.01 - 0.49 arası)
    CAMERA_CROP_LEFT = 0.35                # Soldan kırpma oranı (örn: 0.05 = %5 kırp)
    CAMERA_CROP_RIGHT = 0.35                # Sağdan kırpma oranı (örn: 0.05 = %5 kırp)
    CAMERA_CROP_TOP = 0.35                # Üstten kırpma oranı (örn: 0.05 = %5 kırp)
    CAMERA_CROP_BOTTOM = 0.35                # Alttan kırpma oranı (örn: 0.05 = %5 kırp)
    
    # ==================== JEST ALGILAMA AYARLARI ====================
    PINCH_THRESHOLD = 20              # Parmak birleşme mesafesi eşiği (piksel) - artırıldı
    GESTURE_COOLDOWN = 0.5              # Jestler arası minimum bekleme süresi (saniye)
    STABLE_FRAMES = 10                   # Jest onayı için gereken stabil frame sayısı
    
    # ==================== SCROLL AYARLARI ====================
    SCROLL_SENSITIVITY = 20             # Scroll hassasiyeti (piksel hareket başına scroll miktarı)
    SCROLL_THRESHOLD = 15               # Minimum hareket eşiği scroll başlamadan önce (piksel)
    SCROLL_COOLDOWN = 0.05              # Scroll işlemleri arası minimum süre (saniye)
    
    # ==================== SES KONTROL AYARLARI ====================
    VOLUME_STEP = 4                     # Ses değişim adımı (1-10 arası birim, 5 = her seferinde 5 birim)
    VOLUME_COOLDOWN = 0.2               # Ses işlemleri arası minimum süre (saniye)
    
    # ==================== SESLİ YAZMA AYARLARI ====================
    SPEECH_ENABLED = True               # Sesli yazma sistemini aç/kapa
    SPEECH_LANGUAGE = 'tr-TR'           # Tanıma dili (tr-TR: Türkçe, en-US: İngilizce)
    SPEECH_MICROPHONE_INDEX = 3         # Mikrofon index (None = varsayılan, 0,1,2... = belirli mikrofon)
    SPEECH_AUTO_START = True            # Uygulama başlarken otomatik mikrofon başlatsın mı?
    SPEECH_AUTO_WRITE = True            # Sürekli yazma modu (konuşulanları hemen yaz)
    SPEECH_TIMEOUT = 5                  # Maksimum dinleme süresi (saniye)
    SPEECH_AUTO_ENTER = False           # Her cümleden sonra otomatik Enter basılsın mı?
    
    # ==================== GÖRSEL AYARLAR ====================
    SHOW_FPS = True                     # FPS gösterimini aç/kapa
    SHOW_LANDMARKS = True               # El noktalarını göster
    SHOW_GESTURE_TEXT = True            # Jest ismini ekranda göster
    FLIP_CAMERA = True                  # Kamerayı ayna gibi çevir (daha doğal)
    
    # ==================== RENKLER (BGR formatında) ====================
    COLOR_HAND_LANDMARKS = (0, 255, 0)  # El noktaları rengi (Yeşil)
    COLOR_HAND_CONNECTIONS = (255, 0, 0) # El bağlantıları rengi (Mavi)
    COLOR_GESTURE_TEXT = (0, 255, 255)  # Jest metni rengi (Sarı)
    COLOR_FPS_TEXT = (255, 255, 255)    # FPS metni rengi (Beyaz)
    COLOR_STATUS_TEXT = (0, 165, 255)   # Durum metni rengi (Turuncu)
    
    # ==================== LANDMARK İNDEKSLERİ ====================
    # MediaPipe Hand Landmarks (21 nokta)
    THUMB_TIP = 4                       # Başparmak ucu
    INDEX_TIP = 8                       # İşaret parmağı ucu
    MIDDLE_TIP = 12                     # Orta parmak ucu
    RING_TIP = 16                       # Yüzük parmağı ucu
    PINKY_TIP = 20                      # Serçe parmak ucu
    WRIST = 0                           # Bilek
    PALM_CENTER = 9                     # Avuç içi merkezi (orta parmak tabanı)


# ==================== AYARLARI YÜKLE (settings.json varsa) ====================
def _load_settings_on_startup():
    """Uygulama başlarken settings.json'dan ayarları yükle"""
    try:
        # settings.json path'ini belirle (EXE/normal mod)
        if getattr(sys, 'frozen', False):
            # EXE modunda - AppData kullan
            app_data = os.getenv('APPDATA')
            settings_path = Path(app_data) / 'HandMouse' / 'settings.json'
        else:
            # Normal modda - proje dizini
            settings_path = Path(__file__).parent.parent / 'settings.json'
        
        # Dosya varsa yükle
        if settings_path.exists():
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # Her ayarı Config sınıfına uygula
            for key, value in settings.items():
                if hasattr(Config, key):
                    setattr(Config, key, value)
    except Exception as e:
        pass  # Hata olsa bile varsayılan ayarlarla devam et


# Modül yüklendiğinde ayarları otomatik yükle
_load_settings_on_startup()
