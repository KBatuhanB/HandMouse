"""
Volume Controller Modülü
Windows ses ve media kontrolü için API wrapper.
"""

import time
from typing import Optional
import sys
from pathlib import Path

# Config'i import et
sys.path.append(str(Path(__file__).parent))
from config import Config

# Windows için ses kontrolü
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False
    print("⚠️  pycaw yüklü değil. Ses kontrolü çalışmayacak.")
    print("   Yüklemek için: pip install pycaw")

# Media kontrolleri için pyautogui kullanacağız
try:
    import pyautogui
    HAS_MEDIA_CONTROL = True
except ImportError:
    HAS_MEDIA_CONTROL = False
    print("⚠️  pyautogui yüklü değil. Media kontrolü çalışmayacak.")


class VolumeController:
    """
    Windows ses kontrol sınıfı.
    Ses seviyesi ve mute durumu yönetimi.
    """
    
    def __init__(self):
        """VolumeController sınıfını başlatır."""
        self.volume_interface = None
        self.last_volume_change = 0
        self.volume_cooldown = 0.1  # Daha hızlı tepki için düşürüldü
        self.volume_step = Config.VOLUME_STEP  # Ayarlanabilir adım
        
        if HAS_PYCAW:
            try:
                # Windows ses cihazını al
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                
                print("🔊 Volume Controller başlatıldı")
                current_volume = self.get_volume()
                is_muted = self.is_muted()
                print(f"   Mevcut ses seviyesi: {current_volume}/100")
                print(f"   Sessiz mod: {'Açık' if is_muted else 'Kapalı'}")
            except Exception as e:
                print(f"❌ Ses kontrolü başlatılamadı: {e}")
                self.volume_interface = None
        else:
            print("❌ Ses kontrolü kullanılamıyor (pycaw yok)")
    
    def is_available(self) -> bool:
        """
        Ses kontrolünün kullanılabilir olup olmadığını kontrol eder.
        
        Returns:
            True: Ses kontrolü kullanılabilir
        """
        return self.volume_interface is not None
    
    def get_volume(self) -> int:
        """
        Mevcut ses seviyesini alır (birimsel, 0-100 arası).
        
        Returns:
            Ses seviyesi (0-100 arası integer)
        """
        if not self.is_available():
            return 0
        
        try:
            # Scalar volume kullan (0.0-1.0 arası float)
            volume_scalar = self.volume_interface.GetMasterVolumeLevelScalar()
            # 0.0-1.0 -> 0-100 integer'a çevir
            volume_percent = int(round(volume_scalar * 100))
            return volume_percent
        except Exception as e:
            print(f"❌ Ses seviyesi okunamadı: {e}")
            return 0
    
    def set_volume(self, volume_percent: int) -> bool:
        """
        Ses seviyesini ayarlar (birimsel, 0-100 arası).
        
        Args:
            volume_percent: Ses seviyesi (0-100 arası integer)
            
        Returns:
            True: İşlem başarılı
        """
        if not self.is_available():
            return False
        
        try:
            # 0-100 integer arası sınırla
            volume_percent = max(0, min(100, volume_percent))
            
            # 0-100 integer -> 0.0-1.0 float'a çevir
            volume_scalar = volume_percent / 100.0
            
            # Scalar volume ayarla (linear, birimsel)
            self.volume_interface.SetMasterVolumeLevelScalar(volume_scalar, None)
            return True
        except Exception as e:
            print(f"❌ Ses ayarlanamadı: {e}")
            return False
    
    def volume_up(self, step: Optional[int] = None) -> bool:
        """
        Ses seviyesini arttırır.
        
        Args:
            step: Artış miktarı (varsayılan: Config.VOLUME_STEP)
            
        Returns:
            True: İşlem başarılı
        """
        current_time = time.time()
        
        # Cooldown kontrolü
        if current_time - self.last_volume_change < self.volume_cooldown:
            return False
        
        # Step belirtilmemişse Config'ten oku (güncel değer)
        if step is None:
            step = Config.VOLUME_STEP
        
        current = self.get_volume()
        new_volume = min(100, current + step)
        
        if self.set_volume(new_volume):
            self.last_volume_change = current_time
            print(f"🔊 Ses arttırıldı: {current} → {new_volume} (+{step} birim)")
            return True
        
        return False
    
    def volume_down(self, step: Optional[int] = None) -> bool:
        """
        Ses seviyesini azaltır.
        
        Args:
            step: Azalış miktarı (varsayılan: Config.VOLUME_STEP)
            
        Returns:
            True: İşlem başarılı
        """
        current_time = time.time()
        
        # Cooldown kontrolü
        if current_time - self.last_volume_change < self.volume_cooldown:
            return False
        
        # Step belirtilmemişse Config'ten oku (güncel değer)
        if step is None:
            step = Config.VOLUME_STEP
        
        current = self.get_volume()
        new_volume = max(0, current - step)
        
        if self.set_volume(new_volume):
            self.last_volume_change = current_time
            print(f"🔉 Ses azaltıldı: {current} → {new_volume} (-{step} birim)")
            return True
        
        return False
    
    def is_muted(self) -> bool:
        """
        Sessiz modun açık olup olmadığını kontrol eder.
        
        Returns:
            True: Sessiz mod açık
        """
        if not self.is_available():
            return False
        
        try:
            return bool(self.volume_interface.GetMute())
        except Exception as e:
            print(f"❌ Mute durumu okunamadı: {e}")
            return False
    
    def toggle_mute(self) -> bool:
        """
        Sessiz modu aç/kapa yapar.
        
        Returns:
            True: İşlem başarılı
        """
        if not self.is_available():
            return False
        
        try:
            current_mute = self.is_muted()
            self.volume_interface.SetMute(not current_mute, None)
            
            new_state = "Sessiz" if not current_mute else "Açık"
            print(f"🔇 Ses: {new_state}")
            return True
        except Exception as e:
            print(f"❌ Mute toggle hatası: {e}")
            return False
    
    def mute(self) -> bool:
        """
        Sesi kapatır (mute).
        
        Returns:
            True: İşlem başarılı
        """
        if not self.is_available():
            return False
        
        try:
            if not self.is_muted():
                self.volume_interface.SetMute(True, None)
                print("🔇 Ses kapatıldı")
            return True
        except Exception as e:
            print(f"❌ Mute hatası: {e}")
            return False
    
    def unmute(self) -> bool:
        """
        Sesi açar (unmute).
        
        Returns:
            True: İşlem başarılı
        """
        if not self.is_available():
            return False
        
        try:
            if self.is_muted():
                self.volume_interface.SetMute(False, None)
                print("🔊 Ses açıldı")
            return True
        except Exception as e:
            print(f"❌ Unmute hatası: {e}")
            return False
    
    def media_play_pause(self) -> bool:
        """
        Media oynatma/duraklatma (play/pause toggle).
        Müzik, video, YouTube vb. tüm media oynatıcıları için çalışır.
        
        Returns:
            True: İşlem başarılı
        """
        if not HAS_MEDIA_CONTROL:
            print("❌ Media kontrolü kullanılamıyor (pyautogui yok)")
            return False
        
        try:
            # Media play/pause tuşunu bas (çoğu klavyede vardır)
            # Windows'ta bu, aktif media oynatıcısını kontrol eder
            pyautogui.press('playpause')
            print("⏯️  Media Play/Pause")
            return True
        except Exception as e:
            print(f"❌ Media play/pause hatası: {e}")
            return False
    
    def media_next(self) -> bool:
        """
        Sonraki parça/video.
        
        Returns:
            True: İşlem başarılı
        """
        if not HAS_MEDIA_CONTROL:
            return False
        
        try:
            pyautogui.press('nexttrack')
            print("⏭️  Sonraki parça")
            return True
        except Exception as e:
            print(f"❌ Media next hatası: {e}")
            return False
    
    def media_previous(self) -> bool:
        """
        Önceki parça/video.
        
        Returns:
            True: İşlem başarılı
        """
        if not HAS_MEDIA_CONTROL:
            return False
        
        try:
            pyautogui.press('prevtrack')
            print("⏮️  Önceki parça")
            return True
        except Exception as e:
            print(f"❌ Media previous hatası: {e}")
            return False
