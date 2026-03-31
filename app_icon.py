import os
import sys
from typing import List, Optional

from PySide6.QtGui import QIcon

from app_paths import get_internal_path, get_resource_path


def iter_application_icon_sources(
    *,
    icon_name: str = "app_icon.ico",
    executable_path: Optional[str] = None,
    frozen: Optional[bool] = None,
) -> List[str]:
    sources: List[str] = []

    def add_if_exists(path: Optional[str]):
        if not path:
            return
        normalized = os.path.normcase(os.path.abspath(path))
        if normalized in seen:
            return
        if os.path.exists(path):
            sources.append(path)
            seen.add(normalized)

    seen = set()
    add_if_exists(get_internal_path(icon_name))
    add_if_exists(get_resource_path(icon_name))

    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    resolved_executable = executable_path or sys.executable
    if is_frozen:
        add_if_exists(resolved_executable)

    return sources


def load_application_icon(
    *,
    icon_name: str = "app_icon.ico",
    executable_path: Optional[str] = None,
    frozen: Optional[bool] = None,
) -> QIcon:
    for source in iter_application_icon_sources(
        icon_name=icon_name,
        executable_path=executable_path,
        frozen=frozen,
    ):
        icon = QIcon(source)
        if not icon.isNull():
            return icon
    return QIcon()
