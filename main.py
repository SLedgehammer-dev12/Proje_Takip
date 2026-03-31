import os
import sys
from pathlib import Path

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
from app_paths import get_resource_path
from config import APP_ICON_FILE, APP_NAME, APP_USER_MODEL_ID, APP_VERSION, CHANGELOG

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


def main():
    setup_logging()
    write_changelog_file()
    db = None

    # Install global exception handlers
    sys.excepthook = exception_hook
    QtCore.qInstallMessageHandler(qt_message_handler)

    try:
        app = QApplication(sys.argv)
        app_icon = load_application_icon(icon_name=APP_ICON_FILE)
        if not app_icon.isNull():
            app.setWindowIcon(app_icon)
        if hasattr(app, "setDesktopFileName"):
            try:
                app.setDesktopFileName(APP_USER_MODEL_ID)
            except Exception:
                pass
        app.setApplicationDisplayName(APP_NAME)

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
    apply_stylesheet(app, variant=str(tok_variant))


def _safe_log_qt_style_info(app: QApplication):
    """Call `log_qt_style_info` safely; fallback defined at module import time if missing."""
    try:
        log_qt_style_info(app)
    except Exception as e:
        logger.debug("log_qt_style_info unavailable or failed: %s", e)


def _load_last_db() -> str:
    """Load last used DB from QSettings; ensure returned path exists or fallback to projeler.db"""
    settings = QtCore.QSettings(APP_NAME, APP_NAME)
    last_db = settings.value("database/last_file", "projeler.db") or "projeler.db"
    if not isinstance(last_db, str):
        try:
            last_db = str(last_db)
        except Exception:
            last_db = "projeler.db"
    import os

    if not os.path.exists(last_db):
        last_db_abs = os.path.abspath(last_db)
        if os.path.exists(last_db_abs):
            last_db = last_db_abs
        else:
            last_db = os.path.abspath("projeler.db")
    return last_db


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
            crash_file = get_resource_path("CRITICAL_ERROR.txt")
            with open(crash_file, "w", encoding="utf-8") as f:
                f.write(error_msg)
        except Exception:
            pass
        sys.exit(1)
