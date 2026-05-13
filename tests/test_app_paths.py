import os

from app_paths import get_default_database_path, get_user_data_dir, get_user_data_path


def test_user_data_path_uses_localappdata_on_windows(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    monkeypatch.delenv("APPDATA", raising=False)

    user_data_dir = get_user_data_dir()
    db_path = get_default_database_path()

    assert user_data_dir.startswith(str(tmp_path / "LocalAppData"))
    assert db_path == os.path.join(user_data_dir, "projeler.db")


def test_get_user_data_path_can_create_parent(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    target = get_user_data_path("logs", "proje_takip.log", create_parent=True)

    assert os.path.isdir(os.path.dirname(target))
    assert target.endswith(os.path.join("logs", "proje_takip.log"))
