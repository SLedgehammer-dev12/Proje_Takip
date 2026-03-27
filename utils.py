# utils.py
import sys
import os
import re
import logging
from PySide6.QtGui import QPalette
from app_paths import get_resource_path

# Modüllerimizden gerekli tanımları içe aktar
from config import APP_NAME, CHANGELOG, CHANGELOG_FILE

# =============================================================================
# LOGGING KURULUMU
# =============================================================================


def setup_logging():
    # Allow enabling debug logging by setting the environment variable PT_DEBUG=1
    level = logging.DEBUG if os.environ.get("PT_DEBUG", "0").lower() in ("1", "true", "yes") else logging.INFO
    log_path = get_resource_path("proje_takip.log")
    # Ensure logfile is created with UTF-8 BOM for compatibility with Windows Notepad
    # if opening the file without specifying encoding results in replacement characters.
    if not os.path.exists(log_path):
        # create empty logfile with BOM
        with open(log_path, "w", encoding="utf-8-sig"):
            pass

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8-sig"),
            logging.StreamHandler(),
        ],
    )


def get_class_logger(owner) -> logging.Logger:
    """Return a logger name that includes the concrete class name."""
    cls = owner if isinstance(owner, type) else owner.__class__
    return logging.getLogger(f"{cls.__module__}.{cls.__name__}")


# =============================================================================
# DEĞİŞİKLİK NOTU YAZDIRMA
# =============================================================================


def write_changelog_file():
    """Uygulamanın bulunduğu dizine bir güncelleme geçmişi dosyası yazar."""
    try:
        filepath = get_resource_path(CHANGELOG_FILE)

        with open(filepath, "w", encoding="utf-8") as f:
            # HATA DÜZELTMESİ: .UPPER() -> .upper() olarak değiştirildi.
            f.write(f"{APP_NAME.upper()} - GÜNCELLEME NOTLARI\n")
            f.write("=" * 40 + "\n\n")

            for version, changes in CHANGELOG.items():
                f.write(f"--- Sürüm: {version} ---\n")
                for change in changes:
                    f.write(f"  * {change}\n")
                f.write("\n")

    except Exception as e:
        # --- LOG GÜNCELLEMESİ ---
        logging.critical(f"Güncelleme notları dosyası yazılamadı: {e}")


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================


def dosyadan_tarih_sayi_cikar(dosya_adi):
    match = re.search(
        r"(\d{2}\.\d{2}\.\d{4})\s+tarih\s+ve\s+([0-9]+)\s+sayılı", dosya_adi
    )
    return {"tarih": match.group(1), "sayi": match.group(2)} if match else None


def dosyadan_proje_bilgisi_cikar(dosya_adi):
    match = re.search(r"([0-4]-.+?-\d{4})_(.+?)\.pdf", dosya_adi, re.IGNORECASE)
    return (
        {"kod": match.group(1), "isim": match.group(2).replace("_", " ").strip()}
        if match
        else None
    )


def log_qt_style_info(app):
    """Log current Qt style and palette info useful for diagnosing high-contrast issues."""
    try:
        style_name = app.style().objectName() if app.style() else "None"
        logging.info(f"Qt Style: {style_name}")
        pal = app.palette()
        # log a few colors
        logging.info(f"Palette Window: {pal.color(QPalette.Window).name()} ")
        logging.info(f"Palette WindowText: {pal.color(QPalette.WindowText).name()} ")
        logging.info(f"Palette Highlight: {pal.color(QPalette.Highlight).name()} ")
        logging.info(
            f"Palette HighlightedText: {pal.color(QPalette.HighlightedText).name()} "
        )
    except Exception as e:
        logging.warning(f"Unable to log Qt style info: {e}")
