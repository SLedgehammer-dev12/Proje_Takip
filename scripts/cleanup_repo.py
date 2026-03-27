"""
Cleanup script to remove tracked runtime artifacts and dev leftovers.
WARNING: This will remove files and directories from your working tree.
Make sure you have backups (the user said they do).
Run: python scripts/cleanup_repo.py
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REMOVE_FILES = [
    ROOT / "projeler.db",
    ROOT / "projeler.db.geri_yukleme_oncesi.bak",
    ROOT / "projeler.db.pre_restore.bak",
    ROOT / "proje_takip.log",
    ROOT / "yazi_indirme.log",
    ROOT / "test_yeni_ozellik.py",
    ROOT / "tools" / "quick_backup_test.py",
    ROOT / "tests" / "test_backup_service.py",
    ROOT / "database.py.backup_before_migration",
]

REMOVE_DIRS = [
    ROOT / "veritabani_yedekleri",
    ROOT / "tools" / "originals",
]


def remove_file(p: Path):
    if p.exists():
        try:
            p.unlink()
            print(f"Removed: {p}")
        except Exception as e:
            print(f"Failed to remove file {p}: {e}")


def remove_dir(p: Path):
    if p.exists() and p.is_dir():
        try:
            shutil.rmtree(p)
            print(f"Removed directory: {p}")
        except Exception as e:
            print(f"Failed to remove directory {p}: {e}")


def main():
    print("Starting cleanup...")
    for f in REMOVE_FILES:
        remove_file(f)
    for d in REMOVE_DIRS:
        remove_dir(d)
    print(
        "Cleanup finished. You can now run 'git status' to see changes, and commit or push them."
    )


if __name__ == "__main__":
    main()
