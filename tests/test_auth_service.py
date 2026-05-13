from pathlib import Path

import pytest

from services.auth_service import AuthService, WriterSessionConflictError


class FakeDB:
    def __init__(
        self,
        db_path: Path,
        username: str = "admin",
        full_name: str = "Admin Kullanici",
        fail_update_last_login: bool = False,
    ):
        self.db_adi = str(db_path)
        self._user = {
            "id": 1,
            "username": username,
            "full_name": full_name,
        }
        self.last_login_updates = []
        self.fail_update_last_login = fail_update_last_login

    def verify_user(self, username: str, password: str):
        if username == self._user["username"] and password == "secret":
            return dict(self._user)
        return None

    def update_last_login(self, user_id: int):
        if self.fail_update_last_login:
            raise RuntimeError("login timestamp write failed")
        self.last_login_updates.append(user_id)


def test_auth_service_blocks_second_writer_session(tmp_path):
    db_path = tmp_path / "projeler.db"
    db_path.write_text("", encoding="utf-8")

    primary = AuthService(FakeDB(db_path, username="admin", full_name="Admin Kullanici"))
    secondary = AuthService(FakeDB(db_path, username="editor", full_name="Editor Kullanici"))

    try:
        assert primary.authenticate("admin", "secret") is True
        assert secondary.authenticate("editor", "secret") is False

        error = secondary.get_last_auth_error()
        assert error["code"] == "writer_conflict"
        assert "Admin Kullanici" in error["message"]
    finally:
        primary.shutdown()
        secondary.shutdown()


def test_auth_service_allows_guest_while_writer_session_exists(tmp_path):
    db_path = tmp_path / "projeler.db"
    db_path.write_text("", encoding="utf-8")

    writer = AuthService(FakeDB(db_path))
    guest = AuthService(FakeDB(db_path, username="guest", full_name="Guest Kullanici"))

    try:
        assert writer.authenticate("admin", "secret") is True

        guest.login_as_guest()

        sessions = guest.get_active_sessions(include_self=True)
        assert any(session.get("can_write") for session in sessions)
        assert guest.is_guest is True
        assert guest.has_permission("write") is False
        assert guest.has_permission("read") is True
    finally:
        writer.shutdown()
        guest.shutdown()


def test_auth_service_bind_db_rejects_conflicting_writer(tmp_path):
    db_one = tmp_path / "db1.db"
    db_two = tmp_path / "db2.db"
    db_one.write_text("", encoding="utf-8")
    db_two.write_text("", encoding="utf-8")

    first = AuthService(FakeDB(db_one, username="admin"))
    other = AuthService(FakeDB(db_two, username="editor", full_name="Editor Kullanici"))

    try:
        assert first.authenticate("admin", "secret") is True
        assert other.authenticate("editor", "secret") is True

        with pytest.raises(WriterSessionConflictError):
            first.bind_db(FakeDB(db_two, username="admin"))
    finally:
        first.shutdown()
        other.shutdown()


def test_auth_service_cleans_up_partial_login_on_failure(tmp_path):
    db_path = tmp_path / "projeler.db"
    db_path.write_text("", encoding="utf-8")
    auth = AuthService(
        FakeDB(
            db_path,
            username="admin",
            full_name="Admin Kullanici",
            fail_update_last_login=True,
        )
    )

    try:
        assert auth.authenticate("admin", "secret") is False
        assert auth.current_user is None
        assert auth.has_permission("write") is False
        assert auth.get_active_sessions(include_self=True) == []
        assert auth.presence_service.get_writer_lock() == {}

        error = auth.get_last_auth_error()
        assert error["code"] == "authentication_error"
    finally:
        auth.shutdown()


def test_auth_service_downgrades_to_read_only_when_writer_lease_is_lost(tmp_path):
    db_path = tmp_path / "projeler.db"
    db_path.write_text("", encoding="utf-8")
    auth = AuthService(FakeDB(db_path))

    try:
        assert auth.authenticate("admin", "secret") is True
        auth.presence_service.release_writer_lock(auth._presence_session_id)

        assert auth.heartbeat_session() is True
        assert auth.heartbeat_session() is True
        assert auth.heartbeat_session() is False
        assert auth.has_permission("write") is False
        assert auth.has_permission("read") is True
        assert auth.get_last_auth_error()["code"] == "writer_lease_lost"

        sessions = auth.get_active_sessions(include_self=True)
        assert sessions
        assert not any(session.get("can_write") for session in sessions)
    finally:
        auth.shutdown()


def test_auth_service_recovers_from_single_transient_lease_failure(tmp_path, monkeypatch):
    db_path = tmp_path / "projeler.db"
    db_path.write_text("", encoding="utf-8")
    auth = AuthService(FakeDB(db_path))

    original_refresh = auth.presence_service.refresh_writer_lock
    state = {"calls": 0}

    def flaky_refresh(*args, **kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            return False
        return original_refresh(*args, **kwargs)

    try:
        assert auth.authenticate("admin", "secret") is True
        monkeypatch.setattr(auth.presence_service, "refresh_writer_lock", flaky_refresh)

        assert auth.heartbeat_session() is True
        assert auth.has_permission("write") is True
        assert auth.heartbeat_session() is True
        assert auth.has_permission("write") is True
        assert auth.get_last_auth_error() == {}
    finally:
        auth.shutdown()
