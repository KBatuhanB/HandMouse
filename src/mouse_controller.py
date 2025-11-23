"""
Mouse Controller Modülü
pyautogui kullanarak mouse hareketleri ve tıklama işlemlerini yönetir.
"""

import pyautogui
import time
from typing import Tuple, Optional
from collections import deque
import platform
import sys
from pathlib import Path

# Config'i import et
sys.path.append(str(Path(__file__).parent))
from config import Config

# Windows için ek kütüphane
if platform.system() == 'Windows':
    try:
        import win32api
        import win32con
        USE_WIN32 = True
    except ImportError:
        USE_WIN32 = False
        print("⚠️  win32api yüklü değil, pyautogui kullanılacak")
else:
    USE_WIN32 = False


class MouseController:
    """
    Mouse kontrol sınıfı.
    Koordinat dönüşümü, hareket yumuşatma ve tıklama işlemlerini yönetir.
    """
    
    def __init__(self, 
                 camera_width: int,
                 camera_height: int,
                 smoothing_factor: int = 1,
                 speed_multiplier: float = 3):
        """
        MouseController sınıfını başlatır.
        
        Args:
            camera_width: Kamera görüntü genişliği (piksel)
            camera_height: Kamera görüntü yüksekliği (piksel)
            smoothing_factor: Hareket yumuşatma için kullanılacak frame sayısı
            speed_multiplier: Mouse hassasiyet çarpanı
        """
        # Ekran boyutlarını al
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Kamera boyutları
        self.camera_width = camera_width
        self.camera_height = camera_height
        
        # Hareket parametreleri
        self.speed_multiplier = speed_multiplier
        self.smoothing_factor = smoothing_factor
        
        # EMA ayarları (Config'ten kopyala, sonra güncellenebilir)
        self.ema_min = Config.EMA_MIN
        self.ema_max = Config.EMA_MAX
        self.ema_function = Config.EMA_FUNCTION
        
        # Koordinat yumuşatma için buffer (FIFO kuyruk)
        self.smooth_x = deque(maxlen=smoothing_factor)
        self.smooth_y = deque(maxlen=smoothing_factor)
        
        # Exponential Moving Average için (daha iyi performans)
        self.ema_x = None
        self.ema_y = None
        # Başlangıç alpha: Min ve Max'ın ortası
        self.ema_alpha = (self.ema_min + self.ema_max) / 2
        
        # Dinamik smoothing için hız takibi
        self.prev_screen_x = None
        self.prev_screen_y = None
        self.current_speed = 0
        
        # Güvenlik ayarları
        pyautogui.FAILSAFE = True  # Fareyi köşeye götürerek acil durdurma
        pyautogui.PAUSE = 0         # Gecikme KAPALI - maksimum hız için
        
        # Durum değişkenleri
        self.last_click_time = 0
        self.click_cooldown = 0.3  # Tıklamalar arası minimum süre (saniye)
        
        # Mouse button durumları (basılı tutma için)
        self.left_button_pressed = False
        self.right_button_pressed = False
        
        # Scroll durumu
        self.last_scroll_time = 0
        self.scroll_cooldown = 0.05  # Scroll işlemleri arası minimum süre
        self.prev_scroll_y = None  # Scroll için önceki Y pozisyonu
        
        # Aktif alan hesapla
        active_width_percent = (1 - Config.CAMERA_CROP_LEFT - Config.CAMERA_CROP_RIGHT) * 100
        active_height_percent = (1 - Config.CAMERA_CROP_TOP - Config.CAMERA_CROP_BOTTOM) * 100
        
        print(f"🖱️  Mouse Controller başlatıldı")
        print(f"   Ekran çözünürlüğü: {self.screen_width}x{self.screen_height}")
        print(f"   Kamera çözünürlüğü: {self.camera_width}x{self.camera_height}")
        print(f"   Aktif alan: %{active_width_percent:.0f} x %{active_height_percent:.0f} (ortada)")
        print(f"   Yumuşatma: Dinamik EMA ({self.ema_min}-{self.ema_max}) - {self.ema_function.upper()}")
    
    def map_coordinates(self, 
                       camera_x: int, 
                       camera_y: int) -> Tuple[int, int]:
        """
        Kamera koordinatlarını ekran koordinatlarına dönüştürür.
        Yeşil dikdörtgen = Ekranın kenarları
        
        Args:
            camera_x: Kamera X koordinatı
            camera_y: Kamera Y koordinatı
            
        Returns:
            (screen_x, screen_y) ekran koordinatları
        """
        # Yeşil dikdörtgenin sınırları
        rect_left = self.camera_width * Config.CAMERA_CROP_LEFT
        rect_right = self.camera_width * (1 - Config.CAMERA_CROP_RIGHT)
        rect_top = self.camera_height * Config.CAMERA_CROP_TOP
        rect_bottom = self.camera_height * (1 - Config.CAMERA_CROP_BOTTOM)
        
        rect_width = rect_right - rect_left
        rect_height = rect_bottom - rect_top
        
        # Basit mapping: Dikdörtgen = Ekran
        # Sol üst köşe (rect_left, rect_top) = Ekran (0, 0)
        # Sağ alt köşe (rect_right, rect_bottom) = Ekran (screen_width, screen_height)
        norm_x = (camera_x - rect_left) / rect_width
        norm_y = (camera_y - rect_top) / rect_height
        
        screen_x = int(norm_x * self.screen_width)
        screen_y = int(norm_y * self.screen_height)
        
        return (screen_x, screen_y)
    
    def calculate_speed(self, x: int, y: int) -> float:
        """
        Mouse'un hareket hızını hesaplar (piksel/frame).
        
        Args:
            x: Güncel X koordinatı
            y: Güncel Y koordinatı
            
        Returns:
            Hareket hızı (piksel/frame)
        """
        # İlk frame ise
        if self.prev_screen_x is None:
            self.prev_screen_x = x
            self.prev_screen_y = y
            return 0
        
        # Önceki pozisyona göre mesafe hesapla
        import math
        dx = x - self.prev_screen_x
        dy = y - self.prev_screen_y
        speed = math.sqrt(dx*dx + dy*dy)
        
        # Pozisyonu güncelle
        self.prev_screen_x = x
        self.prev_screen_y = y
        
        return speed
    
    def update_dynamic_ema(self, speed: float):
        """
        Hareket hızına göre EMA alpha değerini sürekli fonksiyonla hesaplar.
        
        3 Fonksiyon Tipi:
        - Linear: Doğrusal artış (basit, tahmin edilebilir)
        - Exponential: Üstel artış (hızlı tepki)
        - Sigmoid: S-eğrisi (en doğal, yumuşak geçişler)
        
        Args:
            speed: Hareket hızı (piksel/frame)
        """
        import math
        
        # Hızı normalize et (0.0 - 1.0 arası)
        normalized_speed = max(0.0, min(1.0, 
            (speed - Config.SPEED_MIN) / (Config.SPEED_MAX - Config.SPEED_MIN)
        ))
        
        # Fonksiyon tipine göre EMA hesapla
        if self.ema_function == 'linear':
            # Doğrusal interpolasyon (basit)
            ema_normalized = normalized_speed
        
        elif self.ema_function == 'exponential':
            # Üstel fonksiyon (hızlı tepki)
            # y = x^2 (daha yumuşak başlangıç, hızlı bitiş)
            ema_normalized = normalized_speed ** 2
        
        elif self.ema_function == 'sigmoid':
            # Sigmoid (lojistik) fonksiyon (en doğal)
            # S-eğrisi: Yavaş başlangıç, hızlı orta, yavaş bitiş
            # f(x) = 1 / (1 + e^(-k*(x - x0)))
            k = Config.SIGMOID_STEEPNESS
            x0 = Config.SIGMOID_MIDPOINT
            
            # Sigmoid'i orijinal hız değerine uygula (daha iyi sonuç)
            sigmoid_value = 1.0 / (1.0 + math.exp(-k * (speed - x0)))
            ema_normalized = sigmoid_value
        
        else:
            # Varsayılan: Linear
            ema_normalized = normalized_speed
        
        # EMA alpha değerini hesapla (min-max arasında)
        self.ema_alpha = self.ema_min + (self.ema_max - self.ema_min) * ema_normalized
        
        # Sınırları kontrol et
        self.ema_alpha = max(self.ema_min, min(self.ema_max, self.ema_alpha))
        
        # Hız takibi (EMA ile yumuşat)
        self.current_speed = 0.3 * speed + 0.7 * self.current_speed
    
    def smooth_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """
        Koordinatları yumuşatarak titreşimi azaltır.
        Dinamik Exponential Moving Average (EMA) kullanır - hıza göre otomatik ayarlama.
        
        Args:
            x: Ham X koordinatı
            y: Ham Y koordinatı
            
        Returns:
            (smoothed_x, smoothed_y) yumuşatılmış koordinatlar
        """
        # Hareket hızını hesapla
        speed = self.calculate_speed(x, y)
        
        # Hıza göre EMA alpha'yı dinamik ayarla
        self.update_dynamic_ema(speed)
        
        # İlk değer ise direkt ata
        if self.ema_x is None:
            self.ema_x = float(x)
            self.ema_y = float(y)
            return (x, y)
        
        # Exponential Moving Average formülü (dinamik alpha ile)
        # EMA = alpha * yeni_değer + (1 - alpha) * eski_EMA
        # alpha düşük = daha yumuşak ama biraz yavaş (yavaş hareket için)
        # alpha yüksek = daha hızlı ama biraz titrek (hızlı hareket için)
        self.ema_x = self.ema_alpha * x + (1 - self.ema_alpha) * self.ema_x
        self.ema_y = self.ema_alpha * y + (1 - self.ema_alpha) * self.ema_y
        
        return (int(self.ema_x), int(self.ema_y))
    
    def move_mouse(self, camera_x: int, camera_y: int):
        """
        Mouse'u belirtilen kamera koordinatına göre hareket ettirir.
        Koordinat dönüşümü ve yumuşatma uygular.
        Win32 API kullanarak maksimum hız sağlar.
        
        Args:
            camera_x: Kamera X koordinatı
            camera_y: Kamera Y koordinatı
        """
        # Koordinat dönüşümü yap
        screen_x, screen_y = self.map_coordinates(camera_x, camera_y)
        
        # Yumuşatma uygula (EMA - her zaman aktif)
        smooth_x, smooth_y = self.smooth_coordinates(screen_x, screen_y)
        
        # Mouse'u hareket ettir - Win32 API çok daha hızlı!
        if USE_WIN32:
            # Direkt Windows API kullan (en hızlı yöntem)
            win32api.SetCursorPos((smooth_x, smooth_y))
        else:
            # PyAutoGUI fallback (daha yavaş)
            pyautogui.moveTo(smooth_x, smooth_y, duration=0, _pause=False)
    
    def left_click(self) -> bool:
        """
        Sol tıklama yapar (cooldown kontrolü ile).
        DEPRECATED: Bunun yerine left_press ve left_release kullanın.
        
        Returns:
            True: Tıklama yapıldı, False: Cooldown aktif
        """
        current_time = time.time()
        
        # Cooldown kontrolü
        if current_time - self.last_click_time < self.click_cooldown:
            return False
        
        try:
            # Windows'ta doğrudan win32api kullan (daha güvenilir)
            if USE_WIN32:
                x, y = pyautogui.position()
                win32api.SetCursorPos((x, y))
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                print("✅ Sol tıklama (win32) gerçekleştirildi!")
            else:
                # PyAutoGUI kullan
                pyautogui.click(button='left', clicks=1, interval=0.1)
                print("✅ Sol tıklama (pyautogui) gerçekleştirildi!")
        except Exception as e:
            print(f"❌ Sol tıklama hatası: {e}")
            return False
        
        self.last_click_time = current_time
        return True
    
    def left_press(self) -> bool:
        """
        Sol mouse tuşunu basar (basılı tutar).
        
        Returns:
            True: İşlem başarılı
        """
        if self.left_button_pressed:
            return False  # Zaten basılı
        
        try:
            if USE_WIN32:
                x, y = pyautogui.position()
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            else:
                pyautogui.mouseDown(button='left')
            
            self.left_button_pressed = True
            print("🔵 Sol tuş basıldı (basılı tutuluyor)")
            return True
        except Exception as e:
            print(f"❌ Sol tuş basma hatası: {e}")
            return False
    
    def left_release(self) -> bool:
        """
        Sol mouse tuşunu bırakır.
        
        Returns:
            True: İşlem başarılı
        """
        if not self.left_button_pressed:
            return False  # Zaten bırakılmış
        
        try:
            if USE_WIN32:
                x, y = pyautogui.position()
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            else:
                pyautogui.mouseUp(button='left')
            
            self.left_button_pressed = False
            print("⚪ Sol tuş bırakıldı")
            return True
        except Exception as e:
            print(f"❌ Sol tuş bırakma hatası: {e}")
            return False
    
    def right_click(self) -> bool:
        """
        Sağ tıklama yapar (cooldown kontrolü ile).
        DEPRECATED: Bunun yerine right_press ve right_release kullanın.
        
        Returns:
            True: Tıklama yapıldı, False: Cooldown aktif
        """
        current_time = time.time()
        
        # Cooldown kontrolü
        if current_time - self.last_click_time < self.click_cooldown:
            return False
        
        try:
            # Windows'ta doğrudan win32api kullan (daha güvenilir)
            if USE_WIN32:
                x, y = pyautogui.position()
                win32api.SetCursorPos((x, y))
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
                print("✅ Sağ tıklama (win32) gerçekleştirildi!")
            else:
                # PyAutoGUI kullan
                pyautogui.click(button='right', clicks=1, interval=0.1)
                print("✅ Sağ tıklama (pyautogui) gerçekleştirildi!")
        except Exception as e:
            print(f"❌ Sağ tıklama hatası: {e}")
            return False
        
        self.last_click_time = current_time
        return True
    
    def right_press(self) -> bool:
        """
        Sağ mouse tuşunu basar (basılı tutar).
        
        Returns:
            True: İşlem başarılı
        """
        if self.right_button_pressed:
            return False  # Zaten basılı
        
        try:
            if USE_WIN32:
                x, y = pyautogui.position()
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
            else:
                pyautogui.mouseDown(button='right')
            
            self.right_button_pressed = True
            print("🔴 Sağ tuş basıldı (basılı tutuluyor)")
            return True
        except Exception as e:
            print(f"❌ Sağ tuş basma hatası: {e}")
            return False
    
    def right_release(self) -> bool:
        """
        Sağ mouse tuşunu bırakır.
        
        Returns:
            True: İşlem başarılı
        """
        if not self.right_button_pressed:
            return False  # Zaten bırakılmış
        
        try:
            if USE_WIN32:
                x, y = pyautogui.position()
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
            else:
                pyautogui.mouseUp(button='right')
            
            self.right_button_pressed = False
            print("⚪ Sağ tuş bırakıldı")
            return True
        except Exception as e:
            print(f"❌ Sağ tuş bırakma hatası: {e}")
            return False
    
    def scroll(self, y_position: int) -> bool:
        """
        Y pozisyonuna göre scroll yapar (yukarı/aşağı hareket algılar).
        
        Args:
            y_position: Elin Y koordinatı (ekran koordinatı)
            
        Returns:
            True: Scroll yapıldı
        """
        current_time = time.time()
        
        # Cooldown kontrolü
        if current_time - self.last_scroll_time < self.scroll_cooldown:
            return False
        
        # İlk pozisyon ise kaydet
        if self.prev_scroll_y is None:
            self.prev_scroll_y = y_position
            return False
        
        # Y farkını hesapla
        y_diff = self.prev_scroll_y - y_position  # Yukarı hareket = pozitif
        
        # Minimum hareket eşiğini kontrol et
        if abs(y_diff) < Config.SCROLL_THRESHOLD:
            return False
        
        # Scroll miktarını hesapla
        scroll_amount = int(y_diff / Config.SCROLL_SENSITIVITY)
        
        if scroll_amount != 0:
            try:
                if USE_WIN32:
                    # Win32 API ile scroll (120 birim = 1 scroll çark adımı)
                    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, scroll_amount * 120, 0)
                else:
                    # PyAutoGUI ile scroll
                    pyautogui.scroll(scroll_amount)
                
                # Pozisyonu güncelle
                self.prev_scroll_y = y_position
                self.last_scroll_time = current_time
                
                direction = "↑" if scroll_amount > 0 else "↓"
                print(f"🔄 Scroll {direction} ({scroll_amount})")
                return True
            except Exception as e:
                print(f"❌ Scroll hatası: {e}")
                return False
        
        return False
    
    def reset_scroll(self):
        """
        Scroll pozisyonunu sıfırlar.
        Scroll jesti bittiğinde çağrılmalı.
        """
        self.prev_scroll_y = None
    
    def double_click(self) -> bool:
        """
        Çift tıklama yapar (cooldown kontrolü ile).
        
        Returns:
            True: Tıklama yapıldı, False: Cooldown aktif
        """
        current_time = time.time()
        
        # Cooldown kontrolü
        if current_time - self.last_click_time < self.click_cooldown:
            return False
        
        # Çift tıklama yap
        pyautogui.doubleClick()
        self.last_click_time = current_time
        
        return True
    
    def reset_smoothing(self):
        """
        Yumuşatma buffer'ını temizler.
        El kaybolup tekrar göründüğünde çağrılmalı.
        """
        self.smooth_x.clear()
        self.smooth_y.clear()
    
    def set_click_cooldown(self, cooldown: float):
        """
        Tıklama cooldown süresini ayarlar.
        
        Args:
            cooldown: Yeni cooldown süresi (saniye)
        """
        self.click_cooldown = max(0.1, cooldown)
    
    def get_current_position(self) -> Tuple[int, int]:
        """
        Şu anki mouse pozisyonunu döndürür.
        
        Returns:
            (x, y) ekran koordinatları
        """
        return pyautogui.position()
