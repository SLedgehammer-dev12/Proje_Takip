"""
Doğal Gaz Özellikleri G5 - Ana Başlatıcı

Uygulamayı başlatır ve GUI'yi gösterir.
"""

import sys
import logging
from pathlib import Path

# Import from package
from natural_gas_g5.utils.logger import setup_logging
from natural_gas_g5.config.settings import config


def main():
    """
    Ana uygulama başlatıcı.
    
    1. Logging'i yapılandırır
    2. UI modüllerini import eder
    3. Ana pencereyi oluşturur ve başlatır
    """
    # Setup logging
    setup_logging(config.LOG_FILE, config.LOG_LEVEL)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Doğal Gaz Özellikleri G5 başlatılıyor...")
    logger.info(f"Python versiyonu: {sys.version}")
    logger.info("=" * 60)
    
    try:
        # Import UI (delayed to avoid import errors if tkinter not available)
        from natural_gas_g5.ui.app import ThermoApp
        
        # Create and run application
        logger.info("GUI oluşturuluyor...")
        app = ThermoApp()
        
        logger.info("Uygulama başlatıldı - mainloop başlıyor")
        app.mainloop()
        
        logger.info("Uygulama kapatıldı")
        
    except ImportError as e:
        logger.error(f"Import hatası: {e}")
        print(f"HATA: Gerekli modül bulunamadı: {e}")
        print("Lütfen 'pip install -r requirements.txt' komutunu çalıştırın.")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Beklenmeyen hata: {e}", exc_info=True)
        print(f"HATA: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
