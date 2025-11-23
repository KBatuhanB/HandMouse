"""
Hand Mouse - Ana Uygulama
Kamera ile el hareketlerini kullanarak mouse kontrolü sağlar.

Yazar: Hand Mouse Projesi
Tarih: 2025
"""

import cv2
import time
import sys
import threading
from pathlib import Path
from typing import List, Tuple

# Proje modüllerini import et
sys.path.append(str(Path(__file__).parent / 'src'))

from src.hand_detector import HandDetector
from src.mouse_controller import MouseController
from src.gesture_recognizer import GestureRecognizer
from src.volume_controller import VolumeController
from src.overlay_display import OverlayDisplay
from src.speech_to_text import SpeechToText
from src.config import Config


class HandMouseApp:
    """
    Ana uygulama sınıfı.
    Tüm modülleri koordine eder ve ana döngüyü yönetir.
    """
    
    def __init__(self):
        """Uygulamayı başlatır ve modülleri yapılandırır."""
        print("=" * 60)
        print("🖐️  HAND MOUSE CONTROLLER")
        print("=" * 60)
        
        # Kamerayı başlat
        self.camera = cv2.VideoCapture(Config.CAMERA_INDEX)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
        self.camera.set(cv2.CAP_PROP_FPS, Config.CAMERA_FPS)  # FPS ayarla
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Buffer küçült (gecikme azalır)
        
        if not self.camera.isOpened():
            print("❌ HATA: Kamera açılamadı!")
            sys.exit(1)
        
        print(f"📷 Kamera başlatıldı (ID: {Config.CAMERA_INDEX})")
        print(f"   Hedef FPS: {Config.CAMERA_FPS}")
        
        # Modülleri başlat
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
        
        # Sesli Yazma (Speech to Text)
        self.speech_to_text = None
        if Config.SPEECH_ENABLED:
            # Config'den mikrofon index'ini al
            mic_index = getattr(Config, 'SPEECH_MICROPHONE_INDEX', None)
            self.speech_to_text = SpeechToText(
                language=Config.SPEECH_LANGUAGE,
                microphone_index=mic_index
            )
            if not self.speech_to_text.is_available():
                print("⚠️  Sesli yazma kullanılamıyor - devam ediliyor...")
                self.speech_to_text = None
        
        # Overlay Display (monitör üzerinde durum gösterimi)
        self.overlay = OverlayDisplay(position='topright')
        
        # FPS hesaplama değişkenleri
        self.prev_time = 0
        self.fps = 0
        
        # Uygulama durumu
        self.running = True
        self.hand_was_present = False
        
        # Çift tıklama durumu
        self.double_click_performed = False
        
        # Scroll durumu
        self.is_scrolling = False
        
        # Pause/Resume durumu
        self.is_paused = False
        self.fist_detected = False  # Yumruk toggle için
        
        # Global pause/resume durumu (iki elin işaret parmakları birleşince)
        self.global_paused = False
        self.global_pause_detected = False  # Toggle için
        
        # Sol el ses kontrolü durumu
        self.left_hand_enabled = False
        self.left_fist_detected = False
        self.last_left_gesture = None
        
        # Ses kontrolü için hareket takibi
        self.prev_volume_y = None  # Önceki Y pozisyonu
        self.is_volume_mode = False  # Ses kontrolü modu aktif mi?
        self.last_volume_time = 0  # Son ses değişikliği zamanı
        
        # Mute toggle için
        self.mute_pinch_detected = False  # Mute pinch yapıldı mı (toggle için)
        
        # Media play/pause toggle için
        self.media_pinch_detected = False  # Media pinch yapıldı mı (toggle için)
        
        # Mikrofon toggle için (serçe + başparmak)
        self.microphone_pinch_detected = False  # Mikrofon pinch yapıldı mı (toggle için)
        
        # Sesli yazma için pending flag (thread başlatmadan)
        self.speech_pending = False
        self.speech_worker_running = False
        
        # Sesli yazma worker thread'i (sürekli çalışır, flag bekler)
        def speech_worker():
            while self.running:
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
        
        print("=" * 60)
        print("✅ Tüm sistemler hazır!")
        print()
        print("📋 KONTROLLER:")
        print()
        print("🖱️  SAĞ EL - MOUSE KONTROLÜ:")
        print("   • Mouse Hareketi: Elinizi hareket ettirin (avuç içi takip)")
        print("   • Pause/Resume: Yumruk yap (tüm parmaklar kapalı) 👊")
        print("   • Sol Tıklama: Başparmak + İşaret parmağı birleştir")
        print("   • Sağ Tıklama: Başparmak + Orta parmak birleştir")
        print("   • Çift Tıklama: 3 parmak birleştir (Başparmak + İşaret + Orta)")
        print("   • Scroll: 2 parmak açık (İşaret + Orta) ve yukarı/aşağı hareket")
        print("   • Sürükle-Bırak: Pinch yap → hareket et → bırak")
        print()
        print("🔊 SOL EL - SES VE MEDIA KONTROLÜ:")
        print("   • Etkinleştir/Kapat: Yumruk yap 👊")
        print("   • Media Play/Pause: Başparmak + İşaret parmağı birleştir ⏯️")
        print("   • Mute/Unmute: 3 parmak birleştir (Baş + İşaret + Orta) 🤏")
        print("   • Ses Arttır: İşaret + Orta parmak ✌️ + Yukarı tut (sürekli)")
        print("   • Ses Azalt: İşaret + Orta parmak ✌️ + Aşağı tut (sürekli)")
        print()
        if self.speech_to_text:
            print("🎤 SESLİ YAZMA (YENİ SİSTEM):")
            print("   • MİKROFON AÇ/KAPAT: Sol el Serçe + Başparmak birleştir 🤏")
            print("   • Mikrofon açıldığında sürekli dinleme başlar")
            print("   • Konuştuğunuz her şey otomatik yazılır")
            print("   • Tekrar Serçe + Başparmak → Mikrofon KAPANIR")
            if Config.SPEECH_AUTO_ENTER:
                print("   • Mikrofon kapanınca otomatik ENTER basılır")
            print(f"   • Dil: {Config.SPEECH_LANGUAGE}")
            print()
        print("⌨️  DİĞER:")
        print("   • Çıkış: 'q' tuşuna basın")
        print()
        print("🌍 GLOBAL KONTROL:")
        print("   • TÜM KONTROLLER PAUSE/RESUME: İki elin işaret parmaklarını birleştir 👉👈")
        print("=" * 60)
        print()
        
        # Overlay'i başlat (monitör üzerinde durum gösterimi)
        self.overlay.start()
        time.sleep(0.5)  # Overlay penceresinin açılması için kısa bekleme
    
    def calculate_fps(self) -> int:
        """
        Frame rate hesaplar.
        
        Returns:
            FPS değeri
        """
        current_time = time.time()
        fps = 1 / (current_time - self.prev_time) if self.prev_time > 0 else 0
        self.prev_time = current_time
        return int(fps)
    
    def draw_ui_elements(self, frame: cv2.Mat):
        """
        Görüntü üzerine UI elementleri çizer.
        
        Args:
            frame: Çizim yapılacak görüntü
        """
        h, w, _ = frame.shape
        
        # Aktif alanı çiz (yeşil dikdörtgen)
        active_left = int(w * Config.CAMERA_CROP_LEFT)
        active_right = int(w * (1 - Config.CAMERA_CROP_RIGHT))
        active_top = int(h * Config.CAMERA_CROP_TOP)
        active_bottom = int(h * (1 - Config.CAMERA_CROP_BOTTOM))
        
        # Aktif alan çerçevesi (yarı saydam yeşil)
        cv2.rectangle(frame, (active_left, active_top), (active_right, active_bottom), 
                     (0, 255, 0), 2)
        
        # Köşelerde "Aktif Alan" yazısı
        cv2.putText(frame, "Aktif Alan", (active_left + 5, active_top + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # FPS göster
        if Config.SHOW_FPS:
            fps_text = f"FPS: {self.fps}"
            cv2.putText(frame, fps_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                       Config.COLOR_FPS_TEXT, 2)
        
        # GLOBAL PAUSE DURUMU (Ekranın ortasında büyük uyarı)
        if self.global_paused:
            # Yarı saydam kırmızı arka plan
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 100), -1)
            frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
            
            # Büyük uyarı metni
            pause_text = "GLOBAL PAUSE"
            text_size = cv2.getTextSize(pause_text, cv2.FONT_HERSHEY_SIMPLEX, 2, 4)[0]
            text_x = (w - text_size[0]) // 2
            text_y = h // 2
            
            # Beyaz arka plan
            cv2.rectangle(frame, 
                         (text_x - 20, text_y - text_size[1] - 20),
                         (text_x + text_size[0] + 20, text_y + 20),
                         (255, 255, 255), -1)
            
            # Kırmızı metin (kalın yapmak için thickness=4)
            cv2.putText(frame, pause_text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            
            # Alt mesaj
            resume_text = "Tekrar isaret parmaklarini birlestir"
            text_size2 = cv2.getTextSize(resume_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            text_x2 = (w - text_size2[0]) // 2
            text_y2 = text_y + 50
            cv2.putText(frame, resume_text, (text_x2, text_y2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # SAĞ EL DURUMU (Üst - Sağda)
        right_hand_idx = self.hand_detector.get_hand_by_label("Right")
        if right_hand_idx is not None:
            # Sağ el algılandı
            if self.global_paused:
                right_status = "SAG EL: GLOBAL PAUSE"
                right_color = (0, 0, 255)  # Kırmızı
            elif self.is_paused:
                right_status = "SAG EL: DURAKLADI"
                right_color = (0, 165, 255)  # Turuncu
            else:
                right_status = "SAG EL: AKTIF"
                right_color = (0, 255, 0)  # Yeşil
        else:
            right_status = "SAG EL: YOK"
            right_color = (0, 0, 255)  # Kırmızı
        
        # Sağ el durumunu sağ üstte göster
        cv2.putText(frame, right_status, (w - 280, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, right_color, 2)
        
        # SOL EL DURUMU (Üst - Sağda, ikinci satır)
        left_hand_idx = self.hand_detector.get_hand_by_label("Left")
        if left_hand_idx is not None:
            # Sol el algılandı
            if self.global_paused:
                left_status = "SOL EL: GLOBAL PAUSE"
                left_color = (0, 0, 255)  # Kırmızı
            elif self.left_hand_enabled:
                left_status = "SOL EL: AKTIF (SES)"
                left_color = (0, 255, 0)  # Yeşil
            else:
                left_status = "SOL EL: KAPALI"
                left_color = (0, 165, 255)  # Turuncu
        else:
            left_status = "SOL EL: YOK"
            left_color = (0, 0, 255)  # Kırmızı
        
        # Sol el durumunu sağ üstte göster (ikinci satır)
        cv2.putText(frame, left_status, (w - 280, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, left_color, 2)
        
        # Genel durum (Alt - Solda)
        if self.hand_detector.is_hand_present():
            hand_count = self.hand_detector.get_hand_count()
            status_text = f"{hand_count} El Algilandi"
            color = (0, 255, 0)  # Yeşil
        else:
            status_text = "El Bekleniyor..."
            color = Config.COLOR_STATUS_TEXT
        
        cv2.putText(frame, status_text, (10, h - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                   color, 2)
        
        # Jest göster
        if Config.SHOW_GESTURE_TEXT and self.hand_detector.is_hand_present():
            gesture_name = self.gesture_recognizer.get_current_gesture_name()
            cv2.putText(frame, f"Jest: {gesture_name}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                       Config.COLOR_GESTURE_TEXT, 2)
        
        # Çıkış talimatı
        cv2.putText(frame, "'q' - Cikis", (w - 120, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                   (255, 255, 255), 1)
    
    def process_frame(self, frame: cv2.Mat) -> cv2.Mat:
        """
        Tek bir frame'i işler: el algılama, jest tanıma, mouse kontrolü.
        
        Args:
            frame: İşlenecek görüntü
            
        Returns:
            İşlenmiş görüntü (çizimlerle birlikte)
        """
        # Görüntüyü çevir (ayna etkisi için)
        if Config.FLIP_CAMERA:
            frame = cv2.flip(frame, 1)
        
        # Görüntü boyutunu güncelle
        self.hand_detector.update_image_shape(frame)
        
        # El algıla ve çiz
        frame = self.hand_detector.find_hands(frame, draw=Config.SHOW_LANDMARKS)
        
        # El var mı kontrol et
        if self.hand_detector.is_hand_present():
            # El yeni mi göründü?
            if not self.hand_was_present:
                self.mouse_controller.reset_smoothing()
                self.gesture_recognizer.reset_gesture_history()
                self.hand_was_present = True
            
            # Kaç el var?
            hand_count = self.hand_detector.get_hand_count()
            
            # GLOBAL PAUSE/RESUME KONTROLÜ - İki el varsa kontrol et
            if hand_count == 2:
                left_hand_idx = self.hand_detector.get_hand_by_label("Left")
                right_hand_idx = self.hand_detector.get_hand_by_label("Right")
                
                if left_hand_idx is not None and right_hand_idx is not None:
                    left_landmarks = self.hand_detector.get_all_landmarks(left_hand_idx)
                    right_landmarks = self.hand_detector.get_all_landmarks(right_hand_idx)
                    
                    # İki elin işaret parmakları birleşiyor mu?
                    is_global_pause = self.gesture_recognizer.is_global_pause_gesture(
                        left_landmarks, right_landmarks
                    )
                    
                    if is_global_pause and not self.global_pause_detected:
                        # Global pause toggle
                        self.global_paused = not self.global_paused
                        self.global_pause_detected = True
                        
                        if self.global_paused:
                            print("⏸️  GLOBAL PAUSE: TÜM KONTROLLER DURDURULDU (sağ el + sol el)")
                            # Basılı tuşları bırak
                            if self.mouse_controller.left_button_pressed:
                                self.mouse_controller.left_release()
                            if self.mouse_controller.right_button_pressed:
                                self.mouse_controller.right_release()
                        else:
                            print("▶️  GLOBAL RESUME: TÜM KONTROLLER AKTİF")
                    
                    elif not is_global_pause:
                        # İşaret parmakları ayrıldı - flag sıfırla
                        self.global_pause_detected = False
            
            # EL İŞLEMLERİ (sadece global pause yoksa)
            if not self.global_paused:
                # SAĞ EL İŞLEMLERİ (Mouse Kontrolü)
                right_hand_idx = self.hand_detector.get_hand_by_label("Right")
                if right_hand_idx is not None:
                    landmarks = self.hand_detector.get_all_landmarks(right_hand_idx)
                    if landmarks:
                        self.process_right_hand(landmarks)
                
                # SOL EL İŞLEMLERİ (Ses Kontrolü)
                left_hand_idx = self.hand_detector.get_hand_by_label("Left")
                if left_hand_idx is not None:
                    landmarks = self.hand_detector.get_all_landmarks(left_hand_idx)
                    if landmarks:
                        self.process_left_hand(landmarks)
        
        else:
            # El kayboldu
            if self.hand_was_present:
                self.hand_was_present = False
        
        # OVERLAY'İ GÜNCELLE
        self._update_overlay()
        
        return frame
    
    def process_right_hand(self, landmarks: List[Tuple[int, int]]):
        """
        Sağ el ile mouse kontrolünü işler.
        
        Args:
            landmarks: Sağ elin 21 landmark koordinatı
        """
        # AVUÇ İÇİ MERKEZİNİ AL (mouse pozisyonu için)
        # Bilek (0) ve orta parmak tabanı (9) arasındaki orta nokta = avuç içi
        wrist = landmarks[Config.WRIST]
        palm_base = landmarks[Config.PALM_CENTER]
        
        # Avuç içi merkezi hesapla
        palm_x = (wrist[0] + palm_base[0]) // 2
        palm_y = (wrist[1] + palm_base[1]) // 2
        
        # Diğer landmark'lar
        thumb_tip = landmarks[Config.THUMB_TIP]
        index_tip = landmarks[Config.INDEX_TIP]
        middle_tip = landmarks[Config.MIDDLE_TIP]
        
        # YUMRUK JESTİ KONTROLÜ (Pause/Resume Toggle)
        is_fist = self.gesture_recognizer.is_fist(landmarks)
        
        if is_fist and not self.fist_detected:
            # Yumruk yapıldı - pause/resume toggle
            self.is_paused = not self.is_paused
            self.fist_detected = True
            
            if self.is_paused:
                print("⏸️  SAĞ EL: Mouse kontrolü DURAKLADI")
                # Basılı tuşları bırak
                if self.mouse_controller.left_button_pressed:
                    self.mouse_controller.left_release()
                if self.mouse_controller.right_button_pressed:
                    self.mouse_controller.right_release()
            else:
                print("▶️  SAĞ EL: Mouse kontrolü DEVAM EDİYOR")
        
        elif not is_fist:
            # Yumruk bırakıldı - flag sıfırla
            self.fist_detected = False
        
        # MOUSE KONTROLÜ (sadece pause değilse)
        if not self.is_paused:
            # SCROLL JESTİ KONTROLÜ (en yüksek öncelik - mouse hareketi engellenmeli)
            is_scroll = self.gesture_recognizer.is_scroll_gesture(landmarks)
            
            if is_scroll:
                # SCROLL MODU - Mouse hareketi KAPALI, sadece scroll
                # İşaret parmağının Y pozisyonunu kullan
                scroll_y = index_tip[1]  # Kamera koordinatı
                
                # Kamera Y'sini ekran Y'sine çevir (scroll için)
                _, screen_scroll_y = self.mouse_controller.map_coordinates(index_tip[0], scroll_y)
                
                # Scroll yap
                self.mouse_controller.scroll(screen_scroll_y)
                self.is_scrolling = True
                
                # Scroll sırasında basılı tuşları bırak
                if self.mouse_controller.left_button_pressed:
                    self.mouse_controller.left_release()
                if self.mouse_controller.right_button_pressed:
                    self.mouse_controller.right_release()
            
            else:
                # NORMAL MOD - Mouse hareketi AKTİF
                # Scroll modundan çıkıldıysa sıfırla
                if self.is_scrolling:
                    self.mouse_controller.reset_scroll()
                    self.is_scrolling = False
                
                # MOUSE HAREKETİ (scroll yoksa)
                # Avuç içi pozisyonuna göre mouse'u hareket ettir
                self.mouse_controller.move_mouse(palm_x, palm_y)
            
            # SONRA TIKLAMA İŞLEMLERİ (sadece scroll modunda değilse)
            if not is_scroll:
                # ÖNCELİK 1: Çift Tıklama (3 parmak - en spesifik)
                is_double_click = self.gesture_recognizer.is_double_click(landmarks)
                
                # ÖNCELİK 2: Sol Tıklama (Başparmak + İşaret parmağı pinch)
                is_left_pinch = self.gesture_recognizer.is_left_click(landmarks)
                
                # ÖNCELİK 3: Sağ Tıklama (Başparmak + Orta parmak pinch)
                is_right_pinch = self.gesture_recognizer.is_right_click(landmarks)
                
                # TIKLAMA YÖNETİMİ
                if is_double_click:
                    # 3 parmak birleşik - çift tıklama yap (bir kere)
                    if not self.double_click_performed:
                        # Önce basılı tüm tuşları bırak
                        if self.mouse_controller.left_button_pressed:
                            self.mouse_controller.left_release()
                        if self.mouse_controller.right_button_pressed:
                            self.mouse_controller.right_release()
                        
                        # Çift tıklama yap
                        self.mouse_controller.double_click()
                        self.double_click_performed = True
                        print("✨ Çift tıklama yapıldı!")
                
                elif is_left_pinch:
                    # Sol pinch aktif - tuşu bas ve basılı tut
                    self.mouse_controller.left_press()
                    
                    # Sağ tuş varsa bırak
                    if self.mouse_controller.right_button_pressed:
                        self.mouse_controller.right_release()
                    # Çift tıklama flag'ini sıfırla
                    self.double_click_performed = False
                
                elif is_right_pinch:
                    # Sağ pinch aktif - tuşu bas ve basılı tut
                    self.mouse_controller.right_press()
                    # Sol tuş varsa bırak
                    if self.mouse_controller.left_button_pressed:
                        self.mouse_controller.left_release()
                    # Çift tıklama flag'ini sıfırla
                    self.double_click_performed = False
                
                else:
                    # Pinch yok - basılı tuşları bırak
                    if self.mouse_controller.left_button_pressed:
                        self.mouse_controller.left_release()
                    if self.mouse_controller.right_button_pressed:
                        self.mouse_controller.right_release()
                    # Çift tıklama flag'ini sıfırla
                    self.double_click_performed = False
    
    def process_left_hand(self, landmarks: List[Tuple[int, int]]):
        """
        Sol el ile ses kontrolünü işler.
        
        Args:
            landmarks: Sol elin 21 landmark koordinatı
        """
        # YUMRUK JESTİ KONTROLÜ (Sol El Enable/Disable Toggle)
        is_fist = self.gesture_recognizer.is_fist(landmarks)
        
        if is_fist and not self.left_fist_detected:
            # Yumruk yapıldı - enable/disable toggle
            self.left_hand_enabled = not self.left_hand_enabled
            self.left_fist_detected = True
            
            if self.left_hand_enabled:
                print("🔊 SOL EL: Ses kontrolü ETKİNLEŞTİRİLDİ")
            else:
                print("🔇 SOL EL: Ses kontrolü DEVRE DIŞI")
                # Durumları sıfırla
                self.prev_volume_y = None
                self.is_volume_mode = False
        
        elif not is_fist:
            # Yumruk bırakıldı - flag sıfırla
            self.left_fist_detected = False
        
        # SES VE MEDIA KONTROLÜ (sadece etkinse)
        if self.left_hand_enabled and not is_fist:
            # MİKROFON JESTİ KALDIRILDI - Otomatik başlıyor artık
            
            # ÖNCELİK 1: 3 PARMAK KONTROLÜ (MUTE) - En spesifik jest
            is_mute_pinch = self.gesture_recognizer.is_mute_gesture(landmarks)
            
            # SONRA 2 PARMAK KONTROLÜ (MEDIA PLAY/PAUSE)
            is_media_pinch = self.gesture_recognizer.is_media_play_pause_gesture(landmarks)
            
            # Öncelik: 3 parmak > 2 parmak
            if is_mute_pinch and not self.mute_pinch_detected:
                # 3 parmak pinch yapıldı - mute toggle (bir kere)
                self.volume_controller.toggle_mute()
                self.mute_pinch_detected = True
                self.last_left_gesture = "mute"
                # Ses modunu sıfırla
                self.is_volume_mode = False
                self.prev_volume_y = None
                # Media flag'i de sıfırla
                self.media_pinch_detected = False
            
            elif not is_mute_pinch:
                # 3 parmak pinch bırakıldı - flag sıfırla
                self.mute_pinch_detected = False
                
                # 2 PARMAK MEDIA KONTROLÜ (sadece 3 parmak yoksa)
                if is_media_pinch and not self.media_pinch_detected:
                    # 2 parmak pinch yapıldı - media play/pause (bir kere)
                    self.volume_controller.media_play_pause()
                    self.media_pinch_detected = True
                    self.last_left_gesture = "media"
                    # Ses modunu sıfırla
                    self.is_volume_mode = False
                    self.prev_volume_y = None
                
                elif not is_media_pinch:
                    # 2 parmak pinch bırakıldı - flag sıfırla
                    self.media_pinch_detected = False
                    
                    # İŞARET + ORTA PARMAK AÇIK - SES KONTROL MODU (Sürekli)
                    # Sadece hiçbir pinch yoksa çalışır
                    if self.gesture_recognizer.is_volume_up_gesture(landmarks):
                        # İşaret parmağının Y pozisyonunu kullan
                        index_tip = landmarks[8]
                        current_y = index_tip[1]
                        
                        # İlk pozisyon ise kaydet
                        if self.prev_volume_y is None:
                            self.prev_volume_y = current_y
                            self.is_volume_mode = True
                            self.last_left_gesture = "volume_mode"
                        else:
                            # Mevcut pozisyona göre yukarı mı aşağı mı bakıyor?
                            # Referans nokta: İlk pozisyon
                            y_diff = self.prev_volume_y - current_y  # Yukarı = pozitif, Aşağı = negatif
                            
                            # Sürekli ses değiştirme (cooldown ile)
                            import time
                            current_time = time.time()
                            
                            # Her 0.15 saniyede bir ses değiştir (daha yavaş ama kontrollü)
                            if current_time - self.last_volume_time >= 0.15:
                                # Yukarı bakmaya devam ediyorsa (30 piksel üstünde)
                                if y_diff > 30:
                                    self.volume_controller.volume_up()
                                    self.last_volume_time = current_time
                                    if self.last_left_gesture != "volume_up_continuous":
                                        print("🔊 Yukarı → Ses sürekli ARTIYOR")
                                        self.last_left_gesture = "volume_up_continuous"
                                
                                # Aşağı bakmaya devam ediyorsa (30 piksel altında)
                                elif y_diff < -30:
                                    self.volume_controller.volume_down()
                                    self.last_volume_time = current_time
                                    if self.last_left_gesture != "volume_down_continuous":
                                        print("🔉 Aşağı → Ses sürekli AZALIYOR")
                                        self.last_left_gesture = "volume_down_continuous"
                    
                    else:
                        # Jest yok - durumları sıfırla
                        self.prev_volume_y = None
                        self.is_volume_mode = False
                        if self.last_left_gesture in ["volume_up_continuous", "volume_down_continuous"]:
                            print("⏹️  Ses kontrolü durduruldu")
                        self.last_left_gesture = None
    
    def run(self):
        """Ana uygulama döngüsü."""
        # Kamera penceresini ayarla
        window_name = 'Hand Mouse Controller'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        # Kamera pencere boyutunu küçült (640x480 -> 320x240)
        camera_display_width = 320
        camera_display_height = 240
        cv2.resizeWindow(window_name, camera_display_width, camera_display_height)
        
        # Pencereyi alt ortaya konumlandır
        import platform
        if platform.system() == 'Windows':
            try:
                import win32gui
                import win32con
                import win32api
                
                # Pencereyi bul
                time.sleep(0.2)  # Pencere oluşması için kısa bekleme
                hwnd = win32gui.FindWindow(None, window_name)
                
                if hwnd:
                    # Ekran boyutunu al
                    screen_width = win32api.GetSystemMetrics(0)
                    screen_height = win32api.GetSystemMetrics(1)
                    
                    # Alt orta pozisyon hesapla
                    x = (screen_width - camera_display_width) // 2
                    y = screen_height - camera_display_height - 50  # 50 piksel yukarıda (taskbar için)
                    
                    # Pencereyi konumlandır
                    win32gui.SetWindowPos(
                        hwnd, 
                        win32con.HWND_TOPMOST,  # Her zaman üstte
                        x, y, 
                        camera_display_width, camera_display_height,
                        win32con.SWP_SHOWWINDOW
                    )
                    
                    # Şeffaflık ekle (0-255, 150 = %59 opak, daha şeffaf)
                    styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    styles = styles | win32con.WS_EX_LAYERED
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, styles)
                    win32gui.SetLayeredWindowAttributes(hwnd, 0, 150, win32con.LWA_ALPHA)
                    
                    print(f"📺 Kamera penceresi ayarlandı: {camera_display_width}x{camera_display_height}, Alt-Orta, Şeffaf")
            except Exception as e:
                print(f"⚠️  Pencere ayarları uygulanamadı: {e}")
        
        try:
            while self.running:
                # Frame oku
                success, frame = self.camera.read()
                
                if not success:
                    print("⚠️  Kameradan görüntü alınamadı!")
                    break
                
                # FPS hesapla
                self.fps = self.calculate_fps()
                
                # Frame'i işle
                frame = self.process_frame(frame)
                
                # UI elementlerini çiz
                self.draw_ui_elements(frame)
                
                # Görüntüyü göster
                cv2.imshow(window_name, frame)
                
                # Klavye kontrolü
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Çıkış yapılıyor...")
                    self.running = False
                elif key == ord(' '):
                    # Space tuşu ile duraklatma/devam (gelecek özellik)
                    pass
        
        except KeyboardInterrupt:
            print("\n⚠️  Program kullanıcı tarafından durduruldu")
        
        except Exception as e:
            print(f"\n❌ HATA: {str(e)}")
        
        finally:
            self.cleanup()
    
    def _update_overlay(self):
        """Overlay display'i günceller."""
        # Sağ el durumu
        right_hand_idx = self.hand_detector.get_hand_by_label("Right")
        if right_hand_idx is not None:
            if self.global_paused:
                right_status = "GLOBAL PAUSE"
                right_color = "red"
            elif self.is_paused:
                right_status = "DURAKLADI"
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
            fps=self.fps,
            right_hand=right_status,
            right_hand_color=right_color,
            left_hand=left_status,
            left_hand_color=left_color,
            global_pause=self.global_paused,
            current_gesture=current_gesture,
            speech_active=self.speech_to_text.is_continuous_active() if self.speech_to_text else False
        )
    
    def cleanup(self):
        """Kaynakları temizle ve kapat."""
        print("\n🧹 Kaynaklar temizleniyor...")
        
        # Sesli yazmayı kapat
        if hasattr(self, 'speech_to_text') and self.speech_to_text:
            try:
                self.speech_to_text.cleanup()
            except Exception as e:
                print(f"⚠️  Sesli yazma kapatma hatası: {e}")
        
        # Overlay'i kapat ve thread'in bitmesini bekle
        if hasattr(self, 'overlay'):
            try:
                self.overlay.stop()
                # Overlay thread'inin kapanması için kısa bekleme
                time.sleep(0.3)
            except Exception as e:
                print(f"⚠️  Overlay kapatma hatası: {e}")
        
        # Kamerayı kapat
        if hasattr(self, 'camera'):
            try:
                self.camera.release()
            except Exception as e:
                print(f"⚠️  Kamera kapatma hatası: {e}")
        
        # OpenCV pencerelerini kapat
        try:
            cv2.destroyAllWindows()
            # Pencerelerin kapanması için kısa bekleme
            time.sleep(0.1)
        except Exception as e:
            print(f"⚠️  Pencere kapatma hatası: {e}")
        
        print("✅ Program sonlandırıldı")


def main():
    """Ana giriş noktası."""
    try:
        app = HandMouseApp()
        app.run()
    except Exception as e:
        print(f"❌ Başlatma hatası: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
