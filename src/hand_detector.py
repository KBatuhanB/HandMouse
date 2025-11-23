"""
Hand Detector Modülü
MediaPipe kullanarak gerçek zamanlı el algılama ve landmark tespiti yapar.
"""

import cv2
import mediapipe as mp
from typing import Optional, Tuple, List


class HandDetector:
    """
    El algılama ve takip sınıfı.
    MediaPipe Hands çözümünü kullanarak kamera görüntüsünden el tespiti yapar.
    """
    
    def __init__(self, 
                 max_hands: int = 1,
                 detection_confidence: float = 0.7,
                 tracking_confidence: float = 0.5):
        """
        HandDetector sınıfını başlatır.
        
        Args:
            max_hands: Maksimum algılanacak el sayısı
            detection_confidence: El algılama için minimum güven skoru (0.0 - 1.0)
            tracking_confidence: El takibi için minimum güven skoru (0.0 - 1.0)
        """
        # MediaPipe çözümlerini başlat
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_draw_styles = mp.solutions.drawing_styles
        
        # Ayarları sakla (GUI'den güncellenebilir)
        self.max_hands = max_hands
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence
        
        # Hands modülünü yapılandır
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,        # Video akışı için False
            max_num_hands=self.max_hands,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence
        )
        
        # Durum değişkenleri
        self.hand_detected = False
        self.landmarks_list = []
        self.hand_labels = []  # "Left" veya "Right"
        self.results = None
    
    def update_settings(self, max_hands: int = None, 
                       detection_confidence: float = None,
                       tracking_confidence: float = None):
        """
        Ayarları güncelle ve MediaPipe modülünü yeniden başlat.
        
        Args:
            max_hands: Yeni maksimum el sayısı
            detection_confidence: Yeni algılama güveni
            tracking_confidence: Yeni takip güveni
        """
        if max_hands is not None:
            self.max_hands = max_hands
        if detection_confidence is not None:
            self.detection_confidence = detection_confidence
        if tracking_confidence is not None:
            self.tracking_confidence = tracking_confidence
        
        # MediaPipe modülünü yeniden başlat
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence
        )
    
    def find_hands(self, image: cv2.Mat, draw: bool = True) -> cv2.Mat:
        """
        Görüntüde el arar ve isteğe bağlı olarak çizer.
        
        Args:
            image: İşlenecek BGR formatında görüntü
            draw: True ise tespit edilen eli görüntü üzerine çizer
            
        Returns:
            İşlenmiş görüntü (çizimlerle birlikte)
        """
        # BGR'den RGB'ye çevir (MediaPipe RGB kullanır)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # El tespiti yap
        self.results = self.hands.process(image_rgb)
        
        # Liste temizle
        self.landmarks_list = []
        self.hand_labels = []
        
        # El bulundu mu kontrol et
        if self.results.multi_hand_landmarks:
            self.hand_detected = True
            
            # Her el için işlem yap
            for idx, hand_landmarks in enumerate(self.results.multi_hand_landmarks):
                # Landmark'ları listeye ekle
                self.landmarks_list.append(hand_landmarks)
                
                # El tarafını (Left/Right) ekle
                if self.results.multi_handedness:
                    hand_label = self.results.multi_handedness[idx].classification[0].label
                    self.hand_labels.append(hand_label)
                else:
                    self.hand_labels.append("Unknown")
                
                # Çizim isteniyorsa
                if draw:
                    # Sadece parmak uçlarını çiz
                    self.draw_fingertips_only(image, hand_landmarks)
        else:
            self.hand_detected = False
        
        return image
    
    def draw_fingertips_only(self, image: cv2.Mat, hand_landmarks):
        """
        Sadece parmak uçlarını (5 nokta) ve avuç içi merkezini çizer.
        
        Args:
            image: Çizim yapılacak görüntü
            hand_landmarks: MediaPipe hand landmarks
        """
        h, w, _ = image.shape
        
        # Parmak ucu indeksleri: Başparmak(4), İşaret(8), Orta(12), Yüzük(16), Serçe(20)
        fingertip_ids = [4, 8, 12, 16, 20]
        
        # Her parmak ucu için
        for tip_id in fingertip_ids:
            landmark = hand_landmarks.landmark[tip_id]
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            
            # Daire çiz (parmak ucu)
            cv2.circle(image, (x, y), 10, (0, 255, 0), cv2.FILLED)  # Yeşil dolu daire
            cv2.circle(image, (x, y), 12, (255, 255, 255), 2)       # Beyaz çerçeve
        
        # Avuç içi merkezi çiz (bilek ve orta parmak tabanı arasında)
        wrist = hand_landmarks.landmark[0]
        palm_base = hand_landmarks.landmark[9]
        
        wrist_x = int(wrist.x * w)
        wrist_y = int(wrist.y * h)
        palm_x_coord = int(palm_base.x * w)
        palm_y_coord = int(palm_base.y * h)
        
        # Avuç merkezi hesapla
        center_x = (wrist_x + palm_x_coord) // 2
        center_y = (wrist_y + palm_y_coord) // 2
        
        # Avuç merkezini çiz (turuncu haç)
        cv2.drawMarker(image, (center_x, center_y), (0, 165, 255), 
                      cv2.MARKER_CROSS, 20, 3)
        cv2.circle(image, (center_x, center_y), 8, (0, 165, 255), 2)
    
    def get_landmark_position(self, 
                            landmark_id: int,
                            hand_no: int = 0) -> Optional[Tuple[int, int]]:
        """
        Belirli bir landmark'ın piksel koordinatlarını döndürür.
        
        Args:
            landmark_id: MediaPipe landmark ID'si (0-20 arası)
            hand_no: Hangi el (birden fazla el varsa, varsayılan: 0)
            
        Returns:
            (x, y) koordinatları veya None (el bulunamadıysa)
        """
        if not self.hand_detected or hand_no >= len(self.landmarks_list):
            return None
        
        # Landmark'ı al
        landmark = self.landmarks_list[hand_no].landmark[landmark_id]
        
        # Normalize koordinatları piksel değerlerine çevir
        h, w, _ = self.last_image_shape
        x = int(landmark.x * w)
        y = int(landmark.y * h)
        
        return (x, y)
    
    def get_all_landmarks(self, hand_no: int = 0) -> Optional[List[Tuple[int, int]]]:
        """
        Elin tüm landmark'larının koordinatlarını döndürür.
        
        Args:
            hand_no: Hangi el (varsayılan: 0)
            
        Returns:
            21 landmark için (x, y) koordinatları listesi veya None
        """
        if not self.hand_detected or hand_no >= len(self.landmarks_list):
            return None
        
        h, w, _ = self.last_image_shape
        landmarks = []
        
        # Tüm landmark'ları dönüştür
        for landmark in self.landmarks_list[hand_no].landmark:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            landmarks.append((x, y))
        
        return landmarks
    
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
        import math
        x1, y1 = point1
        x2, y2 = point2
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    def is_hand_present(self) -> bool:
        """
        Görüntüde el var mı kontrol eder.
        
        Returns:
            True: El algılandı, False: El yok
        """
        return self.hand_detected
    
    def get_hand_count(self) -> int:
        """
        Algılanan el sayısını döndürür.
        
        Returns:
            El sayısı (0, 1 veya 2)
        """
        return len(self.landmarks_list)
    
    def get_hand_label(self, hand_no: int = 0) -> Optional[str]:
        """
        Elin tarafını (Left/Right) döndürür.
        
        Args:
            hand_no: Hangi el (0 veya 1)
            
        Returns:
            "Left", "Right" veya None
        """
        if hand_no >= len(self.hand_labels):
            return None
        return self.hand_labels[hand_no]
    
    def get_hand_by_label(self, label: str) -> Optional[int]:
        """
        Belirli bir taraftaki elin indeksini döndürür.
        
        Args:
            label: "Left" veya "Right"
            
        Returns:
            El indeksi (0 veya 1) veya None (bulunamadıysa)
        """
        for idx, hand_label in enumerate(self.hand_labels):
            if hand_label == label:
                return idx
        return None
    
    def update_image_shape(self, image: cv2.Mat):
        """
        İşlenen görüntünün boyutlarını saklar (koordinat dönüşümü için).
        
        Args:
            image: OpenCV görüntüsü
        """
        self.last_image_shape = image.shape
    
    def __del__(self):
        """Kaynakları temizle"""
        if hasattr(self, 'hands'):
            self.hands.close()
