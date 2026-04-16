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
from .login_dialog import LoginDialog
from .export_dialog import ProjectExportDialog

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
    "CokluProjeDialog",
    "CokluAciklamaDialog",
    "LoginDialog",
    "ProjectExportDialog",
]

