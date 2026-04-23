import datetime
import hashlib
import json
import os
import socket
import uuid
from typing import Any, Dict, List, Optional

from utils import get_class_logger


class PresenceService:
    """Track active sessions with sidecar heartbeat files near the SQLite database."""

    def __init__(self, db_path: str, heartbeat_ttl_sec: int = 75):
        self.db_path = os.path.abspath(db_path)
        self.heartbeat_ttl_sec = max(heartbeat_ttl_sec, 30)
        self.logger = get_class_logger(self)

    def register_session(
        self,
        username: str,
        display_name: str,
        is_guest: bool,
        can_write: bool,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_id = session_id or uuid.uuid4().hex
        existing = self._read_session_payload(session_id)
        payload = self._build_payload(
            session_id=session_id,
            username=username,
            display_name=display_name,
            is_guest=is_guest,
            can_write=can_write,
            opened_at=existing.get("opened_at"),
        )
        self._write_payload(self._session_path(session_id), payload)
        return payload

    def heartbeat_session(
        self,
        session_id: str,
        username: str,
        display_name: str,
        is_guest: bool,
        can_write: bool,
    ) -> Dict[str, Any]:
        return self.register_session(
            username=username,
            display_name=display_name,
            is_guest=is_guest,
            can_write=can_write,
            session_id=session_id,
        )

    def unregister_session(self, session_id: Optional[str]) -> None:
        if not session_id:
            return
        self._remove_file(self._session_path(session_id))

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        self._ensure_presence_dir()
        sessions: List[Dict[str, Any]] = []
        for file_name in os.listdir(self._presence_dir()):
            if not file_name.endswith(".json"):
                continue
            session_id = os.path.splitext(file_name)[0]
            payload = self._read_session_payload(session_id)
            if not payload:
                continue
            if self._is_stale(payload):
                self.unregister_session(session_id)
                continue
            sessions.append(payload)

        sessions.sort(
            key=lambda item: (
                not bool(item.get("can_write")),
                str(item.get("username", "")).casefold(),
                -float(item.get("last_seen_ts", 0.0)),
            )
        )
        return sessions

    def try_acquire_writer_lock(
        self,
        username: str,
        display_name: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_id = session_id or uuid.uuid4().hex
        lock_path = self._writer_lock_path()
        existing = self.get_writer_lock()
        if existing:
            if existing.get("session_id") == session_id:
                payload = self._build_payload(
                    session_id=session_id,
                    username=username,
                    display_name=display_name,
                    is_guest=False,
                    can_write=True,
                    opened_at=existing.get("opened_at"),
                )
                self._write_payload(lock_path, payload)
                return {"acquired": True, "payload": payload}
            return {"acquired": False, "payload": existing}

        payload = self._build_payload(
            session_id=session_id,
            username=username,
            display_name=display_name,
            is_guest=False,
            can_write=True,
        )

        for _ in range(2):
            try:
                self._create_payload_exclusive(lock_path, payload)
                return {"acquired": True, "payload": payload}
            except FileExistsError:
                existing = self.get_writer_lock()
                if existing:
                    if existing.get("session_id") == session_id:
                        self._write_payload(lock_path, payload)
                        return {"acquired": True, "payload": payload}
                    return {"acquired": False, "payload": existing}

        return {"acquired": False, "payload": self.get_writer_lock()}

    def get_writer_lock(self) -> Dict[str, Any]:
        lock_path = self._writer_lock_path()
        payload = self._read_payload(lock_path)
        if not payload:
            return {}
        if self._is_stale(payload):
            self._remove_file(lock_path)
            return {}
        return payload

    def refresh_writer_lock(
        self,
        session_id: Optional[str],
        username: str,
        display_name: str,
    ) -> bool:
        if not session_id:
            return False

        current = self.get_writer_lock()
        if not current or current.get("session_id") != session_id:
            return False

        payload = self._build_payload(
            session_id=session_id,
            username=username,
            display_name=display_name,
            is_guest=False,
            can_write=True,
            opened_at=current.get("opened_at"),
        )
        self._write_payload(self._writer_lock_path(), payload)
        return True

    def release_writer_lock(self, session_id: Optional[str]) -> None:
        if not session_id:
            return

        current = self._read_payload(self._writer_lock_path())
        if current and current.get("session_id") != session_id:
            return
        self._remove_file(self._writer_lock_path())

    def _presence_dir(self) -> str:
        db_hash = hashlib.sha1(self.db_path.casefold().encode("utf-8")).hexdigest()[:16]
        return os.path.join(os.path.dirname(self.db_path), ".proje_takip_sessions", db_hash)

    def _ensure_presence_dir(self) -> None:
        os.makedirs(self._presence_dir(), exist_ok=True)

    def _session_path(self, session_id: str) -> str:
        return os.path.join(self._presence_dir(), f"{session_id}.json")

    def _writer_lock_path(self) -> str:
        return os.path.join(self._presence_dir(), "writer.lock")

    def _read_session_payload(self, session_id: str) -> Dict[str, Any]:
        return self._read_payload(self._session_path(session_id))

    def _write_payload(self, path: str, payload: Dict[str, Any]) -> None:
        self._ensure_presence_dir()
        temp_path = f"{path}.{os.getpid()}.tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(temp_path, path)

    def _create_payload_exclusive(self, path: str, payload: Dict[str, Any]) -> None:
        self._ensure_presence_dir()
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        descriptor = os.open(path, flags)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise

    def _read_payload(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except FileNotFoundError:
            return {}
        except Exception as exc:
            self.logger.debug("Presence payload could not be read (%s): %s", path, exc)
            return {}

        if not isinstance(payload, dict):
            return {}
        return payload

    def _remove_file(self, path: str) -> None:
        try:
            os.remove(path)
        except FileNotFoundError:
            return
        except Exception as exc:
            self.logger.debug("Presence file could not be removed (%s): %s", path, exc)

    def _is_stale(self, payload: Dict[str, Any]) -> bool:
        try:
            last_seen_ts = float(payload.get("last_seen_ts", 0.0))
        except (TypeError, ValueError):
            return True
        return (self._now().timestamp() - last_seen_ts) > self.heartbeat_ttl_sec

    def _build_payload(
        self,
        session_id: str,
        username: str,
        display_name: str,
        is_guest: bool,
        can_write: bool,
        opened_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = self._now()
        return {
            "session_id": session_id,
            "username": username,
            "display_name": display_name,
            "is_guest": bool(is_guest),
            "can_write": bool(can_write),
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "db_path": self.db_path,
            "opened_at": opened_at or now.isoformat(),
            "last_seen": now.isoformat(),
            "last_seen_ts": now.timestamp(),
        }

    def _now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc)
