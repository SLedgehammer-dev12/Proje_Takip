"""Dialogs package.
This package splits dialog classes from the monolithic `dialogs.py` into
separate modules for clarity. The main module re-exports the commonly used
classes for backward compatibility: `from dialogs import ProjeDialog`.
"""

from .proje_dialogs import (
    ProjeDialog,
    ProjeTuruDuzenlemeDialog,
    ProjeYuklemeDialog,
    ManuelProjeGirisiDialog,
    DosyadanCokluProjeDialog,
)
from .revizyon_dialogs import (
    YeniRevizyonDialog,
    OnayRedDialog,
    RevizyonSecDialog,
    DurumDegistirDialog,
    YaziTuruSecDialog,
)
from .misc_dialogs import (
    CokluProjeDialog,
    CokluAciklamaDialog,
)
from .yazi_ekler_dialog import YaziEklerDialog
from .proje_sec_dialog import ProjeSecDialog
from .login_dialog import LoginDialog
from .export_dialog import ProjectExportDialog
from .red_flag_dialog import RedFlagDialog
from .user_manager_dialog import UserManagerDialog

__all__ = [
    "ProjeDialog",
    "ProjeTuruDuzenlemeDialog",
    "ProjeYuklemeDialog",
    "ManuelProjeGirisiDialog",
    "DosyadanCokluProjeDialog",
    "YeniRevizyonDialog",
    "OnayRedDialog",
    "RevizyonSecDialog",
    "DurumDegistirDialog",
    "YaziTuruSecDialog",
    "YaziEklerDialog",
    "ProjeSecDialog",
    "CokluProjeDialog",
    "CokluAciklamaDialog",
    "LoginDialog",
    "ProjectExportDialog",
    "RedFlagDialog",
    "UserManagerDialog",
]

