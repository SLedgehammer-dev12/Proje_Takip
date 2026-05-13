import json
import time
from pathlib import Path

from services.presence_service import PresenceService


def test_presence_service_lists_writer_and_guest_sessions(tmp_path):
    db_path = tmp_path / "projeler.db"
    db_path.write_text("", encoding="utf-8")
    service = PresenceService(str(db_path))

    writer = service.register_session(
        username="admin",
        display_name="Admin Kullanici",
        is_guest=False,
        can_write=True,
    )
    guest = service.register_session(
        username="misafir",
        display_name="Misafir Kullanici",
        is_guest=True,
        can_write=False,
    )

    sessions = service.list_active_sessions()

    assert [session["session_id"] for session in sessions] == [
        writer["session_id"],
        guest["session_id"],
    ]
    assert sessions[0]["can_write"] is True
    assert sessions[1]["is_guest"] is True


def test_presence_service_cleans_up_stale_sessions(tmp_path):
    db_path = tmp_path / "projeler.db"
    db_path.write_text("", encoding="utf-8")
    service = PresenceService(str(db_path), heartbeat_ttl_sec=30)

    session = service.register_session(
        username="admin",
        display_name="Admin Kullanici",
        is_guest=False,
        can_write=True,
    )
    session_path = service._session_path(session["session_id"])

    with open(session_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["last_seen_ts"] = time.time() - 300
    with open(session_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)

    assert service.list_active_sessions() == []
    assert not Path(session_path).exists()


def test_presence_service_allows_only_one_writer_lock(tmp_path):
    db_path = tmp_path / "projeler.db"
    db_path.write_text("", encoding="utf-8")
    service = PresenceService(str(db_path))

    first = service.try_acquire_writer_lock(
        username="admin",
        display_name="Admin Kullanici",
    )
    second = service.try_acquire_writer_lock(
        username="editor",
        display_name="Editor Kullanici",
    )

    assert first["acquired"] is True
    assert second["acquired"] is False
    assert second["payload"]["username"] == "admin"


def test_presence_service_reclaims_stale_writer_lock(tmp_path):
    db_path = tmp_path / "projeler.db"
    db_path.write_text("", encoding="utf-8")
    service = PresenceService(str(db_path), heartbeat_ttl_sec=30)

    first = service.try_acquire_writer_lock(
        username="admin",
        display_name="Admin Kullanici",
    )
    lock_path = service._writer_lock_path()

    with open(lock_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["last_seen_ts"] = time.time() - 300
    with open(lock_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)

    second = service.try_acquire_writer_lock(
        username="editor",
        display_name="Editor Kullanici",
    )

    assert first["acquired"] is True
    assert second["acquired"] is True
    assert second["payload"]["username"] == "editor"
