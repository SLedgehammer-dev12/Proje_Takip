import os
import sys


APP_DATA_DIRNAME = "BOTAS\\ProjeTakipSistemi"


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
    """Path to a file next to the executable for bundled or legacy resources."""
    return os.path.join(get_app_base_dir(), *parts)


def get_internal_path(*parts: str) -> str:
    """Path to a file inside the bundle (Icons, Images, Fonts)."""
    return os.path.join(get_bundle_dir(), *parts)


def get_user_data_dir() -> str:
    """Per-user writable application data folder."""
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if root:
            return os.path.join(root, APP_DATA_DIRNAME)
    elif sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~/Library/Application Support"),
            "BOTAS",
            "ProjeTakipSistemi",
        )

    return os.path.join(
        os.path.expanduser("~"),
        ".local",
        "share",
        "BOTAS",
        "ProjeTakipSistemi",
    )


def ensure_directory(path: str) -> str:
    if path:
        os.makedirs(path, exist_ok=True)
    return path


def get_user_data_path(*parts: str, create_parent: bool = False) -> str:
    """Path inside the per-user writable application data folder."""
    path = os.path.join(get_user_data_dir(), *parts)
    if create_parent:
        ensure_directory(os.path.dirname(path))
    return path


def get_default_database_path() -> str:
    return get_user_data_path("projeler.db", create_parent=True)
