# utils.py
import atexit
import sys
import os
import re
import logging
import queue
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from PySide6.QtGui import QPalette
from app_paths import get_resource_path
from runtime_prefs import is_performance_mode_enabled

# Modüllerimizden gerekli tanımları içe aktar
from config import APP_NAME, CHANGELOG, CHANGELOG_FILE

# =============================================================================
# LOGGING KURULUMU
# =============================================================================


_LOG_LISTENER: QueueListener | None = None
_LOG_QUEUE_HANDLER: QueueHandler | None = None
_LOG_FILE_HANDLER: RotatingFileHandler | None = None
_LOG_STREAM_HANDLER: logging.StreamHandler | None = None


def _shutdown_logging_listener():
    global _LOG_LISTENER
    listener = _LOG_LISTENER
    if listener is None:
        return
    try:
        listener.stop()
    except Exception:
        pass
    _LOG_LISTENER = None


def _get_logging_level(*, performance_mode: bool | None = None) -> int:
    if performance_mode is None:
        performance_mode = is_performance_mode_enabled()
    if performance_mode:
        return logging.ERROR
    return (
        logging.DEBUG
        if os.environ.get("PT_DEBUG", "0").lower() in ("1", "true", "yes")
        else logging.INFO
    )


def _apply_runtime_log_level(level: int):
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in list(root_logger.handlers):
        try:
            handler.setLevel(level)
        except Exception:
            pass

    for handler in (_LOG_QUEUE_HANDLER, _LOG_FILE_HANDLER, _LOG_STREAM_HANDLER):
        if handler is None:
            continue
        try:
            handler.setLevel(level)
        except Exception:
            pass

    listener = _LOG_LISTENER
    if listener is not None:
        for handler in getattr(listener, "handlers", ()):
            try:
                handler.setLevel(level)
            except Exception:
                pass


def setup_logging(performance_mode: bool | None = None):
    global _LOG_LISTENER, _LOG_QUEUE_HANDLER, _LOG_FILE_HANDLER, _LOG_STREAM_HANDLER
    # Allow enabling debug logging by setting the environment variable PT_DEBUG=1
    level = _get_logging_level(performance_mode=performance_mode)
    log_path = get_resource_path("proje_takip.log")
    # Ensure logfile is created with UTF-8 BOM for compatibility with Windows Notepad
    # if opening the file without specifying encoding results in replacement characters.
    if not os.path.exists(log_path):
        # create empty logfile with BOM
        with open(log_path, "w", encoding="utf-8-sig"):
            pass

    root_logger = logging.getLogger()
    if getattr(root_logger, "_proje_takip_logging_ready", False):
        _apply_runtime_log_level(level)
        return

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=4 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8-sig",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    log_queue: queue.SimpleQueue = queue.SimpleQueue()
    queue_handler = QueueHandler(log_queue)
    queue_handler.setLevel(level)
    _LOG_QUEUE_HANDLER = queue_handler
    _LOG_FILE_HANDLER = file_handler
    _LOG_STREAM_HANDLER = stream_handler

    _shutdown_logging_listener()
    _LOG_LISTENER = QueueListener(
        log_queue,
        file_handler,
        stream_handler,
        respect_handler_level=True,
    )
    _LOG_LISTENER.start()

    root_logger.setLevel(level)
    root_logger.addHandler(queue_handler)
    root_logger._proje_takip_logging_ready = True
    atexit.register(_shutdown_logging_listener)


def set_runtime_logging_mode(performance_mode: bool):
    root_logger = logging.getLogger()
    if not getattr(root_logger, "_proje_takip_logging_ready", False):
        setup_logging(performance_mode=performance_mode)
        return
    _apply_runtime_log_level(_get_logging_level(performance_mode=performance_mode))


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
