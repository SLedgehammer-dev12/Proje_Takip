import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Optional

def _ensure_project_venv():
    # PyInstaller paketli sürümde venv kontrolü devre dışı.
    if getattr(sys, "frozen", False):
        return

    project_dir = Path(__file__).resolve().parent
    if os.name == "nt":
        venv_python = project_dir / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = project_dir / ".venv" / "bin" / "python"

    if not venv_python.exists():
        return

    current_python = Path(sys.executable).resolve()
    if current_python == venv_python.resolve():
        return

    # Prevent accidental restart loops if the venv interpreter itself fails.
    if os.environ.get("PROJE_TAKIP_VENV_BOOTSTRAPPED") == "1":
        return

    env = os.environ.copy()
    env["PROJE_TAKIP_VENV_BOOTSTRAPPED"] = "1"
    os.execve(
        str(venv_python),
        [str(venv_python), str(project_dir / "main.py"), *sys.argv[1:]],
        env,
    )

_ensure_project_venv()

import logging
import ctypes

# Modüllerimizden içe aktarma
from app_icon import load_application_icon
from app_paths import get_app_base_dir, get_default_database_path, get_resource_path, get_user_data_path
from config import APP_ICON_FILE, APP_NAME, APP_USER_MODEL_ID, APP_VERSION, CHANGELOG
from i18n import init_i18n, tr

# =============================================================================
# WINDOWS TASKBAR İKON DESTEĞİ
# =============================================================================
if os.name == 'nt':
    try:
        # AppUserModelID belirlemezsek Windows görev çubuğunda jenerik ikon gösterir.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            APP_USER_MODEL_ID
        )
    except Exception:
        pass


from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

from database import ProjeTakipDB
from runtime_prefs import is_performance_mode_enabled
from services.auth_service import AuthService
from utils import setup_logging, write_changelog_file
try:
    from utils import log_qt_style_info
except Exception:
    def log_qt_style_info(app):
        return
from main_window import AnaPencere

# =============================================================================
# UYGULAMA BAŞLATMA
# =============================================================================

logger = logging.getLogger(__name__)


def qt_message_handler(mode, context, message):
    """Qt message handler to capture Qt errors and warnings in our logger"""
    if mode == QtCore.QtMsgType.QtFatalMsg:
        logger.critical(f"Qt Fatal Error: {message}")
    elif mode == QtCore.QtMsgType.QtCriticalMsg:
        logger.critical(f"Qt Critical Error: {message}")
    elif mode == QtCore.QtMsgType.QtWarningMsg:
        logger.warning(f"Qt Warning: {message}")
    elif mode == QtCore.QtMsgType.QtInfoMsg:
        logger.info(f"Qt Info: {message}")
    else:
        logger.debug(f"Qt Debug: {message}")


def exception_hook(exctype, value, traceback):
    """Global exception handler to capture uncaught exceptions"""
    logger.critical("Beklenmeyen Hata:", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)


def thread_exception_hook(args):
    """Log uncaught background thread exceptions before the thread exits."""
    if getattr(args, "exc_type", None) is SystemExit:
        return

    logger.critical(
        "Arka plan thread hatasi: %s",
        getattr(getattr(args, "thread", None), "name", "<unnamed>"),
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )

    original_hook = getattr(threading, "__excepthook__", None)
    if callable(original_hook):
        try:
            original_hook(args)
        except Exception:
            pass


def unraisable_hook(unraisable):
    """Capture ignored destructor/finalizer errors that otherwise disappear."""
    logger.critical(
        "Yoksayilan hata: %s",
        getattr(unraisable, "err_msg", None) or "unraisable exception",
        exc_info=(
            getattr(unraisable, "exc_type", None),
            getattr(unraisable, "exc_value", None),
            getattr(unraisable, "exc_traceback", None),
        ),
    )

    original_hook = getattr(sys, "__unraisablehook__", None)
    if callable(original_hook):
        try:
            original_hook(unraisable)
        except Exception:
            pass


def install_runtime_hooks():
    """Install process-wide hooks for uncaught Python and Qt errors."""
    sys.excepthook = exception_hook
    if hasattr(threading, "excepthook"):
        threading.excepthook = thread_exception_hook
    if hasattr(sys, "unraisablehook"):
        sys.unraisablehook = unraisable_hook
    QtCore.qInstallMessageHandler(qt_message_handler)


def main():
    setup_logging()
    write_changelog_file()
    db = None
    auth_service = None

    # Install global exception handlers
    install_runtime_hooks()

    try:
        app = QApplication(sys.argv)
        init_i18n(app)
        app_icon = load_application_icon(icon_name=APP_ICON_FILE)
        if not app_icon.isNull():
            app.setWindowIcon(app_icon)
        if hasattr(app, "setDesktopFileName"):
            try:
                app.setDesktopFileName(APP_USER_MODEL_ID)
            except Exception:
                pass
        app.setApplicationDisplayName(tr(APP_NAME))

        # Apply theme + log styling if available
        _apply_stylesheet(app)
        _safe_log_qt_style_info(app)

        last_db = _load_last_db()
        # Application metadata
        latest_change_desc = _get_latest_change_desc()
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(f"{APP_VERSION} ({latest_change_desc})")

        # Login dialog first: ana pencereyi ve arka plan işlerini
        # yalnızca kullanıcı giriş yaptıktan sonra oluştur.
        db = ProjeTakipDB(last_db)
        auth_service = AuthService(db)

        from dialogs import LoginDialog
        from PySide6.QtWidgets import QDialog
        
        login_dialog = LoginDialog(auth_service)
        if not app.windowIcon().isNull():
            login_dialog.setWindowIcon(app.windowIcon())
        if login_dialog.exec() != QDialog.Accepted:
            # User cancelled login - exit application
            logger.info("Login cancelled, exiting application")
            try:
                db.close()
            except Exception:
                pass
            return 0

        # Create main window after successful login
        pencere = AnaPencere(db_dosyasi=last_db, db=db, auth_service=auth_service)
        if not app.windowIcon().isNull():
            pencere.setWindowIcon(app.windowIcon())
        
        # Setup UI permissions based on logged in user
        pencere._setup_permissions()
        pencere._update_user_status_label()
        
        # Show main window
        pencere.show()
        logger.info(f"Uygulama başlatıldı - Veritabanı: {last_db}")
        return app.exec()
    except Exception as e:
        logger.critical(f"Uygulama başlatılamadı: {e}", exc_info=True)
        try:
            if auth_service is not None:
                auth_service.shutdown()
            if db is not None:
                db.close()
        except Exception:
            pass
        return 1


def _apply_stylesheet(app: QApplication):
    from ui.styles import apply_stylesheet
    from PySide6.QtCore import QSettings

    settings = QSettings(APP_NAME, APP_NAME)
    # Avoid inline chained expressions to prevent errors when copying partial code
    tok_variant = settings.value("ui/tok_variant", "light")
    try:
        # normalize and ensure we're working with a non-empty string
        tok_variant = tok_variant or "light"
    except Exception:
        tok_variant = "light"
    apply_stylesheet(
        app,
        variant=str(tok_variant),
        performance_mode=is_performance_mode_enabled(),
    )


def _safe_log_qt_style_info(app: QApplication):
    """Call `log_qt_style_info` safely; fallback defined at module import time if missing."""
    try:
        log_qt_style_info(app)
    except Exception as e:
        logger.debug("log_qt_style_info unavailable or failed: %s", e)


def _load_last_db() -> str:
    """
    Son kullanılan DB yolunu yükler.
    - Önce mevcut APP_NAME için QSettings kontrol edilir.
    - Ardından eski/alternatif uygulama adları denenir (sürüm yükseltmelerinde
      ayar anahtarının değişmiş olma ihtimaline karşı).
    - Bulunan ilk mevcut dosya döndürülür; hiçbiri yoksa çalışma dizinindeki
      projeler.db tercih edilir.
    """
    import os

    candidate_paths = []
    default_db_path = get_default_database_path()
    legacy_runtime_paths = [
        os.path.abspath("projeler.db"),
        os.path.abspath(os.path.join(get_app_base_dir(), "projeler.db")),
    ]

    def _read_qsettings(app_name: str) -> Optional[str]:
        val = QtCore.QSettings(app_name, app_name).value("database/last_file")
        if val:
            try:
                return str(val)
            except Exception:
                return None
        return None

    # 1) Güncel uygulama adı
    current = _read_qsettings(APP_NAME)
    if current:
        candidate_paths.append(current)

    # 2) Olası eski uygulama adları (geriye dönük uyumluluk)
    legacy_names = [
        "Proje Takip",          # 2.1.6 ve öncesinde kullanılan olası isim
        "Proje_Takip",
        "ProjeTakip",
        "Proje Takip Sistemi",  # yanlış/boş değer ihtimaline karşı tekrar dene
    ]
    for name in legacy_names:
        val = _read_qsettings(name)
        if val:
            candidate_paths.append(val)

    # 3) Kullanici profili altindaki varsayilan DB
    candidate_paths.append(default_db_path)

    # 4) Legacy portable konumlar
    candidate_paths.extend(legacy_runtime_paths)

    # Adayları benzersiz ve mutlak hale getir
    seen = set()
    normalized = []
    for path in candidate_paths:
        abs_path = os.path.abspath(path)
        if abs_path not in seen:
            seen.add(abs_path)
            normalized.append(abs_path)

    # Mevcut ilk dosyayı döndür
    legacy_runtime_set = {os.path.abspath(path) for path in legacy_runtime_paths}
    for path in normalized:
        if os.path.exists(path):
            if path in legacy_runtime_set:
                migrated = _migrate_legacy_runtime_db(path, default_db_path)
                if migrated:
                    return migrated
            return path

    # Hiçbiri yoksa per-user fallback
    return default_db_path


def _migrate_legacy_runtime_db(source_path: str, target_path: str) -> Optional[str]:
    source_abs = os.path.abspath(source_path)
    target_abs = os.path.abspath(target_path)

    if source_abs == target_abs or not os.path.exists(source_abs):
        return source_abs

    if os.path.exists(target_abs):
        return target_abs

    if not _can_write_database_path(target_abs):
        logger.warning("Varsayilan kullanici veritabani konumu yazilabilir degil: %s", target_abs)
        return source_abs

    try:
        os.makedirs(os.path.dirname(target_abs), exist_ok=True)
        shutil.copy2(source_abs, target_abs)
        logger.info(
            "Legacy veritabani kullanici profiline tasindi: %s -> %s",
            source_abs,
            target_abs,
        )
        return target_abs
    except Exception as exc:
        logger.warning(
            "Legacy veritabani kopyalanamadi, mevcut konum kullanilacak: %s",
            exc,
        )
        return source_abs


def _can_write_database_path(path: str) -> bool:
    target_dir = os.path.dirname(os.path.abspath(path)) or os.getcwd()
    probe_file = os.path.join(target_dir, f".pt_write_probe_{os.getpid()}.tmp")

    try:
        os.makedirs(target_dir, exist_ok=True)
        with open(probe_file, "w", encoding="utf-8") as handle:
            handle.write("probe")
        os.remove(probe_file)
    except Exception:
        return False

    if os.path.exists(path):
        return os.access(path, os.W_OK)
    return True


def _get_latest_change_desc() -> str:
    """Return a short description string for the changelog of the current version."""
    latest_change_desc = ""
    try:
        changes = CHANGELOG.get(APP_VERSION, []) if isinstance(CHANGELOG, dict) else []
        if len(changes) > 0:
            latest_change_desc = changes[0]
            if len(latest_change_desc) > 60:
                latest_change_desc = latest_change_desc[:60] + "..."
    except Exception:
        latest_change_desc = ""
    return latest_change_desc


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # Last-resort crash reporting if main() fails catastrophically
        import traceback
        error_msg = f"FATAL ERROR AT STARTUP:\n{e}\n\n{traceback.format_exc()}"
        print(error_msg)
        try:
            # Try to write to a file in the same directory as the executable
            from app_paths import get_resource_path
            crash_file = get_user_data_path("CRITICAL_ERROR.txt", create_parent=True)
            with open(crash_file, "w", encoding="utf-8") as f:
                f.write(error_msg)
        except Exception:
            pass
        sys.exit(1)
