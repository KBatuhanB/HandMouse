"""
Config Manager - Ayarları Dosyaya Kaydetme/Yükleme
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """Config ayarlarını yönetir"""
    
    def __init__(self, config_file: str = "settings.json"):
        """
        ConfigManager başlatıcı
        
        Args:
            config_file: Ayar dosyasının adı
        """
        # EXE için özel path kontrolü
        if getattr(sys, 'frozen', False):
            # EXE modunda - kullanıcının AppData klasörünü kullan
            app_data = os.getenv('APPDATA')  # C:\Users\USERNAME\AppData\Roaming
            config_dir = Path(app_data) / 'HandMouse'
            config_dir.mkdir(exist_ok=True)  # Klasörü oluştur
            self.config_path = config_dir / config_file
        else:
            # Normal Python modunda - proje dizinini kullan
            self.config_path = Path(__file__).parent.parent / config_file
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Ayarları JSON dosyasına kaydet
        
        Args:
            settings: Kaydedilecek ayarlar dictionary
            
        Returns:
            Başarılı ise True
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Ayar kaydetme hatası: {e}")
            return False
    
    def load_settings(self) -> Dict[str, Any]:
        """
        JSON dosyasından ayarları yükle
        
        Returns:
            Yüklenen ayarlar dictionary
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"❌ Ayar yükleme hatası: {e}")
            return {}
    
    def update_config_file(self, settings: Dict[str, Any]) -> bool:
        """
        Config.py dosyasını güncelle
        
        Args:
            settings: Güncellenecek ayarlar
            
        Returns:
            Başarılı ise True
        """
        try:
            config_py_path = Path(__file__).parent / 'config.py'
            
            with open(config_py_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = []
            for line in lines:
                original_line = line
                updated = False
                
                # Her ayar için kontrol et
                for key, value in settings.items():
                    if line.strip().startswith(key + ' =') or line.strip().startswith(key + '='):
                        # Değeri güncelle
                        indent = len(line) - len(line.lstrip())
                        
                        if isinstance(value, str):
                            new_line = f"{' ' * indent}{key} = '{value}'"
                        elif isinstance(value, bool):
                            new_line = f"{' ' * indent}{key} = {value}"
                        else:
                            new_line = f"{' ' * indent}{key} = {value}"
                        
                        # Yorum varsa koru
                        if '#' in original_line:
                            comment = original_line[original_line.index('#'):]
                            new_line += ' ' * (len(original_line.split('#')[0]) - len(new_line)) + comment
                        else:
                            new_line += '\n'
                        
                        new_lines.append(new_line)
                        updated = True
                        break
                
                if not updated:
                    new_lines.append(original_line)
            
            # Dosyayı yaz
            with open(config_py_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            return True
            
        except Exception as e:
            print(f"❌ Config dosyası güncelleme hatası: {e}")
            return False
