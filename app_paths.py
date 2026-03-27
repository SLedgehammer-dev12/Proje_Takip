import os
import sys


def get_app_base_dir() -> str:
    """Folder where the .exe or the main script is located."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def get_bundle_dir() -> str:
    """Folder where internal assets are (temp folder in onefile, or same as base in dir-mode)."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", get_app_base_dir())
    # Use dirname(__file__) to get the source code dir during development
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(*parts: str) -> str:
    """Path to a file next to the executable (Logs, DB, etc)."""
    return os.path.join(get_app_base_dir(), *parts)


def get_internal_path(*parts: str) -> str:
    """Path to a file inside the bundle (Icons, Images, Fonts)."""
    return os.path.join(get_bundle_dir(), *parts)
