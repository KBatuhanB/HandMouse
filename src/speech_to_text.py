"""
Speech to Text Modülü
Sesli yazma için mikrofon dinleme ve metin dönüştürme.
"""

import time
from typing import Optional
import threading
import pyperclip  # Clipboard için

# Ses tanıma için
try:
    import speech_recognition as sr
    HAS_SPEECH = True
except ImportError:
    HAS_SPEECH = False
    print("⚠️  speech_recognition yüklü değil. Sesli yazma çalışmayacak.")
    print("   Yüklemek için: pip install SpeechRecognition pyaudio")

# Klavye girdisi için
try:
    import pyautogui
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

# Windows API (cursor pozisyon kontrolü için)
try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("⚠️  pywin32 yüklü değil. Cursor kontrol özelliği çalışmayacak.")
    print("   Yüklemek için: pip install pywin32")


class SpeechToText:
    """
    Sesli yazma sınıfı.
    Mikrofon ile ses kaydı alır ve metne çevirir.
    """
    
    def __init__(self, language: str = 'tr-TR', microphone_index: Optional[int] = None):
        """
        SpeechToText sınıfını başlatır.
        
        Args:
            language: Tanıma dili (tr-TR: Türkçe, en-US: İngilizce)
            microphone_index: Mikrofon device index (None = varsayılan, 0,1,2... = belirli mikrofon)
        """
        self.language = language
        self.microphone_index = microphone_index
        self.is_listening = False
        self.recognizer = None
        self.microphone = None
        
        # Sürekli dinleme için
        self.continuous_listening = False
        self.continuous_thread = None
        self.stop_continuous = threading.Event()
        self.writing_enabled = False  # YAZMA MODU (açık/kapalı toggle)
        
        print("="*60)
        print("🎤 SPEECH-TO-TEXT BAŞLATILIYOR...")
        print("="*60)
        
        if HAS_SPEECH:
            try:
                print("📦 speech_recognition kütüphanesi yüklü ✅")
                
                self.recognizer = sr.Recognizer()
                print("✅ Recognizer oluşturuldu")
                
                # Mikrofon cihazını listele
                try:
                    mic_list = sr.Microphone.list_microphone_names()
                    print(f"\n🎤 Bulunan mikrofonlar ({len(mic_list)} adet):")
                    for i, name in enumerate(mic_list):
                        if microphone_index is not None and i == microphone_index:
                            print(f"   {i}: {name} ← SEÇİLDİ")
                        elif microphone_index is None and i == 0:
                            print(f"   {i}: {name} ← VARSAYILAN")
                        else:
                            print(f"   {i}: {name}")
                except:
                    print("   ⚠️ Mikrofon listesi alınamadı")
                
                # Mikrofon oluştur (device_index parametresi ile)
                if microphone_index is not None:
                    print(f"\n📍 Mikrofon #{microphone_index} kullanılıyor...")
                    self.microphone = sr.Microphone(device_index=microphone_index)
                else:
                    print(f"\n📍 Varsayılan mikrofon kullanılıyor...")
                    self.microphone = sr.Microphone()
                    
                print("✅ Mikrofon nesnesi oluşturuldu")
                
                # Mikrofon ayarları - AGRESIF HASSASİYET
                self.recognizer.energy_threshold = 200  # Çok düşük = maksimum hassasiyet
                self.recognizer.dynamic_energy_threshold = True  # Otomatik ayarlama açık
                self.recognizer.dynamic_energy_adjustment_damping = 0.15  # Hızlı adaptasyon
                self.recognizer.dynamic_energy_ratio = 1.5  # Daha hassas eşik
                self.recognizer.pause_threshold = 0.5  # Daha kısa duraklama (hızlı tepki)
                self.recognizer.phrase_threshold = 0.1  # Minimum ses süresi (hemen başla)
                self.recognizer.non_speaking_duration = 0.3  # Sessizlik süresi (hızlı bitir)
                
                print(f"\n⚙️ Ayarlar (Maksimum Hassasiyet):")
                print(f"   Dil: {language}")
                print(f"   Mikrofon Index: {microphone_index if microphone_index is not None else 'Varsayılan'}")
                print(f"   Enerji eşiği: {self.recognizer.energy_threshold} (ÇOK DÜŞÜK = MAKSİMUM HASSASİYET)")
                print(f"   Dinamik eşik: {self.recognizer.dynamic_energy_threshold}")
                print(f"   Duraklama eşiği: {self.recognizer.pause_threshold}s (HIZLI)")
                print(f"   Phrase eşiği: {self.recognizer.phrase_threshold}s (HEMEN BAŞLA)")
                print(f"   Non-speaking: {self.recognizer.non_speaking_duration}s (HIZLI BİTİR)")
                
                print("\n✅ MİKROFON HAZIR!")
                print("="*60)
            except Exception as e:
                print(f"\n❌ MİKROFON BAŞLATILAMADI!")
                print(f"   Hata: {e}")
                print(f"   Hata tipi: {type(e).__name__}")
                print("="*60)
                self.recognizer = None
                self.microphone = None
        else:
            print("❌ speech_recognition YÜKLÜ DEĞİL!")
            print("   Yüklemek için: pip install SpeechRecognition pyaudio")
            print("="*60)
    
    @staticmethod
    def get_microphone_list():
        """
        Mevcut mikrofon cihazlarının listesini döndürür.
        
        Returns:
            List[tuple]: [(index, name), ...] formatında mikrofon listesi
        """
        if not HAS_SPEECH:
            return []
        
        try:
            mic_list = sr.Microphone.list_microphone_names()
            return [(i, name) for i, name in enumerate(mic_list)]
        except Exception as e:
            print(f"❌ Mikrofon listesi alınamadı: {e}")
            return []
    
    @staticmethod
    def is_cursor_in_text_field() -> bool:
        """
        Cursor'ın bir metin alanında (text input) olup olmadığını kontrol eder.
        
        Returns:
            True: Cursor metin alanında
            False: Cursor metin alanında değil
        """
        if not HAS_WIN32:
            # pywin32 yoksa her zaman True döndür (özelliği devre dışı bırak)
            return True
        
        try:
            # Cursor altındaki control'ü al
            cursor_pos = win32gui.GetCursorPos()
            point_hwnd = win32gui.WindowFromPoint(cursor_pos)
            
            if not point_hwnd:
                return False
            
            # Control'ün class name'ini al
            class_name = win32gui.GetClassName(point_hwnd)
            
            # Yaygın text input class'ları
            text_field_classes = [
                'Edit',           # Standart Windows Edit control
                'RICHEDIT',       # Rich Edit control (Word, OneNote vb)
                'RichEdit20W',    # Modern Rich Edit
                'RichEdit50W',    # Office Rich Edit
                'Chrome_RenderWidgetHostHWND',  # Chrome/Edge text input
                'MozillaWindowClass',           # Firefox
                'Internet Explorer_Server',     # IE
                'ConsoleWindowClass',           # Command prompt
                'CASCADIA_HOSTING_WINDOW_CLASS', # Windows Terminal
            ]
            
            # Class name kontrolü (büyük/küçük harf duyarsız)
            class_name_lower = class_name.lower()
            for text_class in text_field_classes:
                if text_class.lower() in class_name_lower:
                    return True
            
            # Edit veya Input içeren class'lar
            if 'edit' in class_name_lower or 'input' in class_name_lower:
                return True
            
            return False
            
        except Exception as e:
            # Hata durumunda False döndür (ses dinlemeyi başlatma)
            print(f"⚠️  Cursor kontrol hatası: {e}")
            return False
    
    @staticmethod
    def detect_working_microphone(test_duration: float = 1.0):
        """
        Çalışan mikrofonu otomatik tespit eder.
        Her mikrofonu sırayla test edip ses alan ilkini döndürür.
        
        Args:
            test_duration: Her mikrofon için test süresi (saniye)
            
        Returns:
            int or None: Çalışan mikrofonun index'i veya None
        """
        if not HAS_SPEECH:
            print("❌ speech_recognition yüklü değil!")
            return None
        
        print("="*60)
        print("🔍 OTOMATİK MİKROFON TESPİTİ")
        print("="*60)
        
        mic_list = SpeechToText.get_microphone_list()
        
        if not mic_list:
            print("❌ Mikrofon bulunamadı!")
            return None
        
        print(f"\n📋 {len(mic_list)} mikrofon test edilecek...")
        print(f"⏱️ Her test süresi: {test_duration} saniye\n")
        
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300  # Hassas
        recognizer.dynamic_energy_threshold = False  # Test için statik
        
        for idx, name in mic_list:
            try:
                print(f"🔍 Test ediliyor: [{idx}] {name}")
                
                # Bu mikrofonu aç
                mic = sr.Microphone(device_index=idx)
                
                with mic as source:
                    # Ortam gürültüsünü ölç
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    energy_before = recognizer.energy_threshold
                    
                    print(f"   Enerji eşiği: {energy_before}")
                    print(f"   Dinleniyor... ({test_duration}s)")
                    
                    try:
                        # Kısa süre dinle (timeout ile)
                        audio = recognizer.listen(source, timeout=test_duration, phrase_time_limit=test_duration)
                        
                        # Ses algılandı!
                        audio_size = len(audio.frame_data)
                        print(f"   ✅ SES ALGILANDI! ({audio_size} byte)")
                        print(f"   ✅ ÇALIŞAN MİKROFON BULUNDU!")
                        print("="*60)
                        
                        return idx
                        
                    except sr.WaitTimeoutError:
                        print(f"   ⏱️ Timeout - Ses yok")
                        
            except Exception as e:
                print(f"   ❌ Hata: {e}")
            
            print()  # Boş satır
        
        print("="*60)
        print("❌ Hiçbir mikrofonda ses algılanamadı!")
        print("\n💡 İpucu:")
        print("   - Mikrofonun doğru takıldığından emin ol")
        print("   - Windows ses ayarlarından mikrofon seviyesini artır")
        print("   - Test sırasında mikrofona konuş")
        print("="*60)
        
        return None
    
    def is_available(self) -> bool:
        """
        Sesli yazmanın kullanılabilir olup olmadığını kontrol eder.
        
        Returns:
            True: Sesli yazma kullanılabilir
        """
        return HAS_SPEECH and self.recognizer is not None and self.microphone is not None
    
    def listen_once(self, timeout: int = 5) -> Optional[str]:
        """
        Bir kez dinler ve metne çevirir (blocking).
        
        Args:
            timeout: Maksimum bekleme süresi (saniye)
            
        Returns:
            Tanınan metin veya None
        """
        if not self.is_available():
            print("❌ Mikrofon kullanılamıyor (is_available=False)")
            return None
        
        try:
            print("="*60)
            print("🎤 MİKROFON DİNLEME BAŞLADI")
            print(f"   📢 ŞİMDİ KONUŞUN! (Max {timeout} saniye)")
            print("="*60)
            
            with self.microphone as source:
                # Ortam gürültüsüne göre ayarla
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                
                # Eşiği sınırla
                if self.recognizer.energy_threshold > 800:
                    self.recognizer.energy_threshold = 800
                
                print(f"� Dinleniyor...")
                
                # Ses kaydı al
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=5  # 10 yerine 5 - daha hızlı
                )
                
                print("✅ Ses alındı, işleniyor...")
            
            # Google Speech Recognition ile metne çevir
            text = self.recognizer.recognize_google(audio, language=self.language)
            
            print(f"✅ Tanındı: '{text}'")
            print("="*60)
            return text
            
        except sr.WaitTimeoutError:
            print("⏱️  Timeout - ses algılanmadı")
            print("="*60)
            return None
        except sr.UnknownValueError:
            print("❌ Ses anlaşılamadı - daha net konuş")
            print("="*60)
            return None
        except sr.RequestError as e:
            print(f"❌ Google API hatası: {e}")
            print("="*60)
            return None
        except Exception as e:
            print(f"❌ Hata: {e}")
            print("="*60)
            return None
    
    def start_listening(self):
        """
        Sürekli dinleme modunu başlatır (non-blocking).
        Arka planda thread ile çalışır.
        """
        if not self.is_available():
            return False
        
        if self.is_listening:
            return False
        
        self.is_listening = True
        
        # Dinleme thread'i başlat
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        
        print("🎤 Sürekli dinleme başladı")
        return True
    
    def stop_listening(self):
        """Sürekli dinleme modunu durdurur."""
        if self.is_listening:
            self.is_listening = False
            print("🔇 Dinleme durduruldu")
    
    def _listen_loop(self):
        """Sürekli dinleme döngüsü (arka plan thread'i)."""
        while self.is_listening:
            text = self.listen_once(timeout=3)
            
            if text:
                # Metni yaz
                self.type_text(text)
    
    def type_text(self, text: str, auto_enter: bool = False):
        """
        Metni klavye girdisi olarak yazar.
        
        Args:
            text: Yazılacak metin
            auto_enter: Metin sonrası otomatik Enter basılsın mı?
        """
        if not HAS_KEYBOARD:
            print("="*60)
            print("❌ PYAUTOGUI YÜKLÜ DEĞİL!")
            print(f"   Metin (manuel): '{text}'")
            print("   Yüklemek için: pip install pyautogui")
            print("="*60)
            return
        
        try:
            print(f"⌨️  Yazılıyor: '{text}'")
            
            # CLIPBOARD YÖNTEMI: Çok daha hızlı!
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            
            # HER ZAMAN sonuna boşluk ekle
            pyautogui.press('space')
            
            # Otomatik Enter
            if auto_enter:
                pyautogui.press('enter')
            
            print("✅ Yazıldı!")
                
        except Exception as e:
            print(f"❌ Yazma hatası: {e}")
    
    def dictate_mode(self, auto_enter: bool = False):
        """
        Dikte modu - Bir kez dinle, yaz, bitir.
        Jest ile çağrılır - ESKİ SİSTEM (çalışıyordu, geri döndük).
        
        Args:
            auto_enter: Metin sonrası otomatik Enter basılsın mı?
        """
        if not self.is_available():
            print("❌ Mikrofon kullanılamıyor")
            return False
        
        # Kısa bekleme (jestten sonra hazır olsun)
        time.sleep(0.3)
        
        print("🎤 Dinleniyor... (5 saniye)")
        
        # Dinle ve yaz (blocking ama ayrı thread'deyiz)
        text = self.listen_once(timeout=5)
        
        if text:
            self.type_text(text, auto_enter=auto_enter)
            return True
        
        return False
    
    def get_status(self) -> str:
        """
        Mevcut durumu döndürür.
        
        Returns:
            Durum metni
        """
        if not self.is_available():
            return "Kullanılamaz"
        elif self.is_listening:
            return "Dinliyor 🎤"
        else:
            return "Hazır"
    
    def start_continuous_listening(self, auto_enter: bool = False):
        """
        Sürekli dinleme modunu başlatır.
        Mikrofon sürekli açık kalır ve konuşulanları yazıya döker.
        
        Args:
            auto_enter: Her cümleden sonra ENTER tuşuna bassın mı?
        """
        if self.continuous_listening:
            print("⚠️  Sürekli dinleme zaten aktif!")
            return
        
        if not self.is_available():
            print("❌ Mikrofon kullanılamıyor!")
            return
        
        print("="*60)
        print("🎤 SÜREKLI DİNLEME MODU BAŞLATILDI")
        print("="*60)
        
        # Config'den yazma modunu al
        from src.config import Config
        auto_write = Config.SPEECH_AUTO_WRITE if hasattr(Config, 'SPEECH_AUTO_WRITE') else False
        
        if auto_write:
            print("   ✅ YAZMA MODU: AÇIK (otomatik)")
            print("   📝 Konuştuğunuz her şey yazılacak!")
        else:
            print("   ⏸️  YAZMA MODU: KAPALI")
            print("   💡 Yazmak için toggle fonksiyonu çağırın")
        print("="*60)
        
        self.continuous_listening = True
        self.writing_enabled = auto_write  # Config'den al
        self.stop_continuous.clear()
        
        # Arka planda sürekli dinleme thread'i başlat
        self.continuous_thread = threading.Thread(
            target=self._continuous_listening_loop,
            args=(auto_enter,),
            daemon=True
        )
        self.continuous_thread.start()
    
    def toggle_writing_mode(self):
        """
        Yazma modunu açıp kapatır (toggle).
        Mikrofon hep dinler ama sadece bu True iken yazar.
        ATOM İŞLEM - Hiç bloklamaz, GUI dostu.
        
        Returns:
            bool: Yeni durum (True: Yazma açık, False: Yazma kapalı)
        """
        if not self.continuous_listening:
            return False
        
        # SADECE FLAG DEĞİŞTİR - başka hiçbir şey yapma (print yok, I/O yok)
        self.writing_enabled = not self.writing_enabled
        
        return self.writing_enabled
    
    def stop_continuous_listening(self, auto_enter: bool = False):
        """
        Sürekli dinleme modunu durdurur.
        
        Args:
            auto_enter: Kapatırken ENTER tuşuna bassın mı?
        """
        if not self.continuous_listening:
            return
        
        print("="*60)
        print("🔴 SÜREKLI DİNLEME MODU DURDURULUYOR...")
        print("="*60)
        
        self.continuous_listening = False
        self.stop_continuous.set()
        
        # Thread'in bitmesini bekle (max 2 saniye)
        if self.continuous_thread and self.continuous_thread.is_alive():
            self.continuous_thread.join(timeout=2.0)
        
        # Auto-enter aktifse ENTER bas
        if auto_enter and HAS_KEYBOARD:
            try:
                pyautogui.press('enter')
                print("✅ Enter tuşuna basıldı")
            except Exception as e:
                print(f"⚠️  Enter basılamadı: {e}")
        
        print("✅ SÜREKLI DİNLEME DURDU")
        print("="*60)
    
    def _continuous_listening_loop(self, auto_enter: bool):
        """
        Sürekli dinleme döngüsü (arka plan thread'inde çalışır).
        TAMAMEN NON-BLOCKING: Mikrofonu açmadan kapatmadan sürekli dinler.
        
        Args:
            auto_enter: Her cümleden sonra ENTER tuşuna bassın mı?
        """
        source = None
        try:
            # Mikrofonu aç (tek seferlik)
            source = self.microphone.__enter__()
            
            print("🎧 Ortam gürültüsü ayarlanıyor...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            
            # Eşiği çok yüksek olmasını engelle
            if self.recognizer.energy_threshold > 800:
                self.recognizer.energy_threshold = 800
                print(f"⚠️  Eşik çok yüksek! 800'e düşürüldü")
            
            print(f"✅ Ayarlanmış enerji eşiği: {self.recognizer.energy_threshold}")
            print("🎤 DİNLEME BAŞLADI - Konuşmaya başlayabilirsiniz!")
            print()
            
            while not self.stop_continuous.is_set():
                try:
                    # Hızlı tepki için kısa timeout
                    timeout_duration = 0.3  # 0.3 saniye - responsive
                    
                    # Timeout ile dinle
                    audio = self.recognizer.listen(source, timeout=timeout_duration, phrase_time_limit=6)
                    
                    # Ses algılandı - İŞLE (yazma moduna bakılmaksızın)
                    if not self.stop_continuous.is_set():
                        # Thread'de işle - ana döngüyü bloklamaz
                        process_thread = threading.Thread(
                            target=self._process_audio,
                            args=(audio, auto_enter),
                            daemon=True
                        )
                        process_thread.start()
                    # Yazma kapalıysa sesi görmezden gel (kaynak tasarrufu)
                
                except sr.WaitTimeoutError:
                    # Timeout - sadece devam et (çok sık olur, normal)
                    continue
                except Exception as e:
                    if not self.stop_continuous.is_set():
                        print(f"⚠️  Dinleme hatası: {e}")
                    continue  # Hata olsa bile devam et
        
        except Exception as e:
            print(f"❌ Sürekli dinleme hatası: {e}")
        finally:
            # Mikrofonu kapat (temizlik)
            if source:
                try:
                    self.microphone.__exit__(None, None, None)
                except:
                    pass
            print("🔴 Sürekli dinleme döngüsü sonlandı")
    
    def _process_audio(self, audio, auto_enter: bool):
        """
        Ses verisini metne çevirir ve yazar.
        UYARI: Bu fonksiyon ayrı thread'de çalışır, bloklanabilir.
        NOT: Sadece writing_enabled=True ise yazar!
        
        Args:
            audio: Ses verisi
            auto_enter: Yazdıktan sonra ENTER tuşuna bassın mı?
        """
        try:
            # Google Speech Recognition ile metne çevir (bu bloklanabilir ama ayrı thread'deyiz)
            text = self.recognizer.recognize_google(audio, language=self.language)
            
            if text:
                # SADECE YAZMA MODU AÇIKSA YAZ
                if self.writing_enabled:
                    # Metni yaz (MAKSIMUM HIZLI - Clipboard kullan)
                    if HAS_KEYBOARD:
                        try:
                            # CLIPBOARD YÖNTEMI: Çok daha hızlı!
                            # 1. Metni clipboard'a kopyala
                            pyperclip.copy(text)
                            # 2. Ctrl+V ile yapıştır (anında)
                            pyautogui.hotkey('ctrl', 'v')
                            
                            # HER ZAMAN sonuna boşluk ekle (kelimeler bitişik olmasın)
                            pyautogui.press('space')
                            
                            # Auto-enter aktifse ENTER da ekle
                            if auto_enter:
                                pyautogui.press('enter')
                        except Exception as e:
                            print(f"❌ Yazma hatası: {e}")
                # Yazma kapalıysa sessizce atla (print yok - performans için)
        
        except sr.UnknownValueError:
            # Ses anlaşılamadı - sessizce devam et (çok yaygın)
            pass
        except sr.RequestError as e:
            print(f"❌ Google API hatası: {e}")
        except Exception as e:
            print(f"❌ İşleme hatası: {e}")
    
    def is_continuous_active(self) -> bool:
        """
        Sürekli dinleme modu aktif mi?
        
        Returns:
            True: Sürekli dinleme aktif
            False: Kapalı
        """
        return self.continuous_listening
    
    def cleanup(self):
        """Kaynakları temizle."""
        # Önce sürekli dinlemeyi durdur
        if self.continuous_listening:
            self.stop_continuous_listening(auto_enter=False)
        
        self.stop_listening()
        print("🔴 Speech-to-Text kapatıldı")
