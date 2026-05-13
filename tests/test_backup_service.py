import os
import sqlite3
import time

from services.backup_service import BackupService


def test_has_recent_backup_detects_matching_recent_file(tmp_path):
    db_path = tmp_path / "projeler.db"
    sqlite3.connect(db_path).close()

    backup_root = tmp_path / "backups"
    service = BackupService(str(db_path), backup_folder=str(backup_root))

    recent_backup = backup_root / os.path.basename(service.backup_folder) / "yedek_Acilis_20260331_120000.db"
    recent_backup.parent.mkdir(parents=True, exist_ok=True)
    recent_backup.write_bytes(b"db")
    os.utime(recent_backup, (time.time(), time.time()))

    assert service.has_recent_backup(max_age_hours=24, description_prefix="Acilis") is True
    assert service.has_recent_backup(max_age_hours=24, description_prefix="Manuel") is False


def test_relative_backup_folder_resolves_under_user_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    db_path = tmp_path / "projeler.db"
    sqlite3.connect(db_path).close()

    service = BackupService(str(db_path))

    assert str(tmp_path / "LocalAppData") in service.backup_folder
    assert "veritabani_yedekleri" in service.backup_folder
