"""
Gesture Recognizer Modülü
El landmark'larından jest tanıma ve yorumlama işlemleri.
"""

import math
import time
from typing import Optional, Tuple, List
from collections import deque


class GestureRecognizer:
    """
    Jest tanıma sınıfı.
    Parmak pozisyonlarından hareketle mouse komutlarını belirler.
    """
    
    def __init__(self, 
                 pinch_threshold: int = 40,
                 stable_frames: int = 3):
        """
        GestureRecognizer sınıfını başlatır.
        
        Args:
            pinch_threshold: Parmakların birleşme mesafesi eşiği (piksel)
            stable_frames: Jest onayı için gereken stabil frame sayısı
        """
        self.pinch_threshold = pinch_threshold
        self.stable_frames = stable_frames
        
        # Jest geçmişi (stabilite kontrolü için)
        self.gesture_history = deque(maxlen=stable_frames)
        
        # Son tespit edilen jest
        self.current_gesture = "none"
        self.last_gesture = "none"
        self.current_gesture_name = ""  # GUI için görüntülenecek jest adı
        
        # Jest zamanlaması
        self.last_gesture_time = 0
        self.gesture_cooldown = 0.3  # Jestler arası minimum süre
        
        print("✋ Gesture Recognizer başlatıldı")
        print(f"   Pinch eşiği: {pinch_threshold} piksel")
        print(f"   Stabil frame: {stable_frames}")
    
    def calculate_distance(self, 
                          point1: Tuple[int, int], 
                          point2: Tuple[int, int]) -> float:
        """
        İki nokta arasındaki Öklid mesafesini hesaplar.
        
        Args:
            point1: İlk nokta (x, y)
            point2: İkinci nokta (x, y)
            
        Returns:
            Noktalar arası mesafe (piksel)
        """
        x1, y1 = point1
        x2, y2 = point2
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    def detect_pinch(self, 
                    thumb_tip: Tuple[int, int], 
                    finger_tip: Tuple[int, int]) -> bool:
        """
        İki parmak ucu arasındaki mesafeye göre pinch (birleşme) algılar.
        Sadece parmak uçlarının Y pozisyonunu kontrol eder (parmak altı değil).
        
        Args:
            thumb_tip: Başparmak ucu koordinatı (x, y)
            finger_tip: Diğer parmak ucu koordinatı (x, y)
            
        Returns:
            True: Parmaklar birleşik, False: Ayrı
        """
        # Sadece parmak uçları arasındaki mesafeyi ölç
        distance = self.calculate_distance(thumb_tip, finger_tip)
        
        # Y pozisyonu kontrolü - parmaklar benzer yükseklikte mi?
        # Parmak altı ile karışmaması için Y farkı da kontrol edilmeli
        y_diff = abs(thumb_tip[1] - finger_tip[1])
        
        # Hem mesafe hem de Y farkı küçük olmalı (gerçek pinch)
        is_close_distance = distance < self.pinch_threshold
        is_similar_height = y_diff < 50  # Y ekseni farkı 50 pikselden az olmalı
        
        return is_close_distance and is_similar_height
    
    def is_double_click(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Çift tıklama jesti algılandı mı kontrol eder.
        3 parmak birleşmesi: Başparmak + işaret + orta parmak.
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: Çift tıklama jesti algılandı
        """
        if not landmarks or len(landmarks) < 21:
            return False
        
        # Parmakları al
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        
        # Her 3 parmak da birleşik olmalı
        thumb_index = self.detect_pinch(thumb_tip, index_tip)
        thumb_middle = self.detect_pinch(thumb_tip, middle_tip)
        
        return thumb_index and thumb_middle
    
    def is_scroll_gesture(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Scroll jesti algılandı mı kontrol eder.
        İşaret + Orta parmak açık (V işareti), diğerleri kapalı.
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: Scroll jesti algılandı
        """
        if not landmarks or len(landmarks) < 21:
            return False
        
        # Hangi parmaklar açık?
        fingers_up = self.get_fingers_up(landmarks)
        
        # İşaret (2) ve Orta (3) parmak açık olmalı
        # Başparmak, yüzük ve serçe kapalı olmalı
        has_index = 2 in fingers_up
        has_middle = 3 in fingers_up
        
        # Sadece bu 2 parmak açık olmalı (veya başparmak da açık olabilir)
        if has_index and has_middle:
            # Yüzük ve serçe kesinlikle kapalı olmalı
            has_ring = 4 in fingers_up
            has_pinky = 5 in fingers_up
            return not has_ring and not has_pinky
        
        return False
    
    def is_fist(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Yumruk jesti algılandı mı kontrol eder.
        Tüm parmaklar kapalı olmalı.
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: Yumruk jesti algılandı (tüm parmaklar kapalı)
        """
        if not landmarks or len(landmarks) < 21:
            return False
        
        # Hangi parmaklar açık?
        fingers_up = self.get_fingers_up(landmarks)
        
        # Hiçbir parmak açık olmamalı
        return len(fingers_up) == 0
    
    def is_mute_gesture(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Mute/Unmute jesti algılandı mı kontrol eder.
        Başparmak + İşaret parmak + Orta parmak birleştirme (3 parmak pinch).
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: Mute jesti algılandı
        """
        if not landmarks or len(landmarks) < 21:
            return False
        
        # Parmak uçlarını al
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        
        # Her 3 parmak da birleşik olmalı
        thumb_index = self.detect_pinch(thumb_tip, index_tip)
        thumb_middle = self.detect_pinch(thumb_tip, middle_tip)
        
        return thumb_index and thumb_middle
    
    def is_volume_up_gesture(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Ses arttırma jesti algılandı mı kontrol eder.
        İşaret + Orta parmak açık (scroll jesti ile aynı).
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: İşaret + Orta parmak açık
        """
        if not landmarks or len(landmarks) < 21:
            return False
        
        fingers_up = self.get_fingers_up(landmarks)
        
        # İşaret (2) ve Orta (3) parmak açık olmalı
        # Yüzük ve serçe kapalı olmalı
        has_index = 2 in fingers_up
        has_middle = 3 in fingers_up
        
        if has_index and has_middle:
            has_ring = 4 in fingers_up
            has_pinky = 5 in fingers_up
            return not has_ring and not has_pinky
        
        return False
    
    def is_volume_down_gesture(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Ses azaltma jesti algılandı mı kontrol eder.
        İşaret + Orta parmak açık (scroll jesti ile aynı).
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: İşaret + Orta parmak açık
        """
        # Volume up ile aynı jest, yön farkı ana kodda algılanacak
        return self.is_volume_up_gesture(landmarks)
    
    def is_media_play_pause_gesture(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Media oynat/durdur jesti algılandı mı kontrol eder.
        Başparmak + İşaret parmağı birleştirme (sol el için).
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: Media play/pause jesti algılandı
        """
        if not landmarks or len(landmarks) < 21:
            return False
        
        # Başparmak ve işaret parmağı uçlarını al
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        
        # Pinch kontrolü yap (sadece 2 parmak)
        return self.detect_pinch(thumb_tip, index_tip)
    
    def is_microphone_toggle_gesture(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Mikrofon aç/kapat toggle jesti algılandı mı kontrol eder.
        Başparmak + Serçe parmağı birleştirme (sol el için).
        
        ÖZEL ALGILAMA: Başparmak ve serçe normalde farklı yüksekliklerde olduğu için
        Y farkı kontrolü YAPILMAZ, sadece mesafe kontrol edilir.
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: Mikrofon toggle jesti algılandı
        """
        if not landmarks or len(landmarks) < 21:
            return False
        
        # Başparmak ve serçe parmağı uçlarını al
        thumb_tip = landmarks[4]   # Başparmak
        pinky_tip = landmarks[20]  # Serçe parmak
        
        # SADECE MESAFE KONTROLÜ (Y farkı kontrolü YOK - başparmak ve serçe için uygunsuz)
        distance = self.calculate_distance(thumb_tip, pinky_tip)
        
        # Daha geniş eşik kullan (başparmak-serçe mesafesi uzun olabilir)
        threshold = self.pinch_threshold + 20  # Normal threshold + 20 piksel
        
        is_close = distance < threshold
        
        return is_close
    
    def recognize_gesture(self, landmarks: List[Tuple[int, int]]) -> str:
        """
        21 landmark'tan jest tanır.
        
        Desteklenen jestler:
        - "fist": Yumruk (tüm parmaklar kapalı) - Pause/Resume toggle
        - "scroll": İşaret + Orta parmak açık (V işareti)
        - "double_click": Başparmak + işaret + orta parmak birleşmesi (3 parmak)
        - "left_click": Başparmak + işaret parmağı birleşmesi
        - "right_click": Başparmak + orta parmak birleşmesi
        - "move": Hiçbir şey (sadece hareket)
        
        Args:
            landmarks: 21 landmark koordinatı [(x, y), ...]
            
        Returns:
            Tanınan jestin adı
        """
        if not landmarks or len(landmarks) < 21:
            return "none"
        
        # Parmak uçlarını al
        thumb_tip = landmarks[4]      # Başparmak ucu
        index_tip = landmarks[8]      # İşaret parmağı ucu
        middle_tip = landmarks[12]    # Orta parmak ucu
        
        # ÖNEMLİ: Öncelik sırası (en spesifikten genel)
        
        # 1. Yumruk jesti (pause/resume için)
        if self.is_fist(landmarks):
            return "fist"
        
        # 2. Scroll jesti (işaret + orta parmak açık, pinch yok)
        if self.is_scroll_gesture(landmarks):
            return "scroll"
        
        # 3. Çift tıklama: Başparmak + işaret + orta parmak (3 parmak birlikte)
        if self.is_double_click(landmarks):
            return "double_click"
        
        # 4. Sol tıklama: Başparmak + işaret parmağı
        if self.detect_pinch(thumb_tip, index_tip):
            return "left_click"
        
        # 5. Sağ tıklama: Başparmak + orta parmak
        if self.detect_pinch(thumb_tip, middle_tip):
            return "right_click"
        
        # Varsayılan: Sadece hareket
        return "move"
    
    def get_stable_gesture(self, landmarks: List[Tuple[int, int]]) -> Optional[str]:
        """
        Jest tanır ve stabilite kontrolü yapar.
        Jest yalnızca belirli sayıda frame boyunca stabil kalırsa onaylanır.
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            Onaylanmış jest adı veya None (stabil değilse)
        """
        # Mevcut frame'de jesti tanı
        detected_gesture = self.recognize_gesture(landmarks)
        
        # Geçmişe ekle
        self.gesture_history.append(detected_gesture)
        
        # Tüm buffer dolmadıysa henüz yeterli veri yok
        if len(self.gesture_history) < self.stable_frames:
            return None
        
        # Tüm frame'lerde aynı jest var mı?
        if all(g == detected_gesture for g in self.gesture_history):
            # Jest değişti mi kontrol et
            if detected_gesture != self.last_gesture:
                self.current_gesture = detected_gesture
                self.last_gesture = detected_gesture
                return detected_gesture
        
        return None
    
    def is_left_click(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Sol tıklama jesti algılandı mı kontrol eder.
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: Sol tıklama algılandı
        """
        if not landmarks or len(landmarks) < 21:
            return False
        
        # Parmakları al
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        
        # Pinch kontrolü yap (Y pozisyonu da kontrol edilir)
        return self.detect_pinch(thumb_tip, index_tip)
    
    def is_right_click(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Sağ tıklama jesti algılandı mı kontrol eder.
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: Sağ tıklama algılandı
        """
        if not landmarks or len(landmarks) < 21:
            return False
        
        # Parmakları al
        thumb_tip = landmarks[4]
        middle_tip = landmarks[12]
        
        # Pinch kontrolü yap (Y pozisyonu da kontrol edilir)
        return self.detect_pinch(thumb_tip, middle_tip)
    
    def get_current_gesture_name(self) -> str:
        """
        Şu anki jestin okunabilir adını döndürür.
        
        Returns:
            Jest adı (UI için)
        """
        gesture_names = {
            "none": "Bekleniyor...",
            "move": "Hareket",
            "left_click": "Sol Tıklama",
            "right_click": "Sağ Tıklama",
            "double_click": "Çift Tıklama",
            "scroll": "Scroll",
            "fist": "Yumruk (Duraklat)"
        }
        
        return gesture_names.get(self.current_gesture, "Bilinmeyen")
    
    def reset_gesture_history(self):
        """
        Jest geçmişini temizler.
        El kaybolup tekrar göründüğünde çağrılmalı.
        """
        self.gesture_history.clear()
        self.current_gesture = "none"
        self.last_gesture = "none"
    
    def set_pinch_threshold(self, threshold: int):
        """
        Pinch eşiğini ayarlar.
        
        Args:
            threshold: Yeni eşik değeri (piksel)
        """
        self.pinch_threshold = max(10, min(threshold, 100))
    
    def is_finger_up(self, landmarks: List[Tuple[int, int]], finger_id: int) -> bool:
        """
        Belirli bir parmağın açık (yukarıda) olup olmadığını kontrol eder.
        
        Args:
            landmarks: 21 landmark koordinatı
            finger_id: Parmak ID'si (1=başparmak, 2=işaret, 3=orta, 4=yüzük, 5=serçe)
            
        Returns:
            True: Parmak açık, False: Parmak kapalı
        """
        if not landmarks or len(landmarks) < 21:
            return False
        
        # Parmak landmark indeksleri
        # Her parmak: [tip, dip, pip, mcp]
        finger_tips = [4, 8, 12, 16, 20]  # Parmak uçları
        finger_pips = [3, 6, 10, 14, 18]  # Parmak ortaları (PIP joints)
        
        if finger_id < 1 or finger_id > 5:
            return False
        
        tip_y = landmarks[finger_tips[finger_id - 1]][1]
        pip_y = landmarks[finger_pips[finger_id - 1]][1]
        
        # Başparmak için özel kontrol (yan hareketi)
        if finger_id == 1:
            tip_x = landmarks[finger_tips[0]][0]
            pip_x = landmarks[finger_pips[0]][0]
            return abs(tip_x - pip_x) > 30  # Yatay mesafe
        
        # Diğer parmaklar için: uç, orta noktadan yukarıdaysa açık
        return tip_y < pip_y - 10  # 10 piksel tolerans
    
    def get_fingers_up(self, landmarks: List[Tuple[int, int]]) -> List[int]:
        """
        Hangi parmakların açık olduğunu döndürür.
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            Açık parmakların ID listesi [1,2,3,4,5]
        """
        fingers_up = []
        for i in range(1, 6):
            if self.is_finger_up(landmarks, i):
                fingers_up.append(i)
        return fingers_up
    
    def is_pointing_gesture(self, landmarks: List[Tuple[int, int]]) -> bool:
        """
        Sadece işaret parmağı açık mı kontrol eder (işaret etme jesti).
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            True: Sadece işaret parmağı açık
        """
        fingers_up = self.get_fingers_up(landmarks)
        # Sadece işaret parmağı (2) açık olmalı
        return fingers_up == [2] or (2 in fingers_up and len(fingers_up) == 1)
    
    def get_finger_distances(self, landmarks: List[Tuple[int, int]]) -> dict:
        """
        Başparmak ile diğer parmaklar arasındaki mesafeleri hesaplar.
        Debug ve ayarlama için kullanışlıdır.
        
        Args:
            landmarks: 21 landmark koordinatı
            
        Returns:
            Parmak mesafeleri dictionary'si
        """
        if not landmarks or len(landmarks) < 21:
            return {}
        
        thumb_tip = landmarks[4]
        
        return {
            "thumb_index": self.calculate_distance(thumb_tip, landmarks[8]),
            "thumb_middle": self.calculate_distance(thumb_tip, landmarks[12]),
            "thumb_ring": self.calculate_distance(thumb_tip, landmarks[16]),
            "thumb_pinky": self.calculate_distance(thumb_tip, landmarks[20])
        }
    
    def is_global_pause_gesture(self, 
                               left_landmarks: List[Tuple[int, int]], 
                               right_landmarks: List[Tuple[int, int]]) -> bool:
        """
        Global pause/resume jesti algılandı mı kontrol eder.
        İki elin işaret parmakları birbirine değdiğinde.
        
        Args:
            left_landmarks: Sol elin 21 landmark koordinatı
            right_landmarks: Sağ elin 21 landmark koordinatı
            
        Returns:
            True: İki elin işaret parmakları birleşik
        """
        if not left_landmarks or not right_landmarks:
            return False
        
        if len(left_landmarks) < 21 or len(right_landmarks) < 21:
            return False
        
        # İki elin işaret parmağı uçlarını al
        left_index_tip = left_landmarks[8]   # Sol el işaret parmağı ucu
        right_index_tip = right_landmarks[8]  # Sağ el işaret parmağı ucu
        
        # İki işaret parmağı arasındaki mesafeyi hesapla
        distance = self.calculate_distance(left_index_tip, right_index_tip)
        
        # Eşikten küçükse birleşmişler demektir
        # Global pause için daha geniş eşik (50 piksel)
        return distance < 50
    
    def set_gesture_name(self, gesture_name: str):
        """
        Aktif jest adını ayarla (GUI'de gösterilmek için)
        
        Args:
            gesture_name: Jest adı (örn: "Sol Tıklama", "Sağ Tıklama", "Scroll")
        """
        self.current_gesture_name = gesture_name
    
    def get_gesture_name(self) -> str:
        """
        Şu anki jest adını döndürür (GUI'de gösterilmek için)
        
        Returns:
            Jest adı veya boş string
        """
        return self.current_gesture_name
