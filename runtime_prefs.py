from PySide6.QtCore import QSettings

from config import APP_NAME


PERFORMANCE_MODE_KEY = "ui/performance_mode"


def _normalize_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def is_performance_mode_enabled(default: bool = False) -> bool:
    try:
        settings = QSettings(APP_NAME, APP_NAME)
        return _normalize_bool(settings.value(PERFORMANCE_MODE_KEY, default), default)
    except Exception:
        return bool(default)


def set_performance_mode_enabled(enabled: bool) -> bool:
    value = bool(enabled)
    try:
        settings = QSettings(APP_NAME, APP_NAME)
        settings.setValue(PERFORMANCE_MODE_KEY, value)
    except Exception:
        pass
    return value
