"""
Doğal Gaz Özellikleri G5 - Basit Başlatıcı

Bu dosyayı direkt çalıştırabilirsiniz:
    python run_app.py

veya çift tıklayın.
"""

import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run main
from natural_gas_g5.main import main

if __name__ == "__main__":
    main()
