"""
Authentication service for user login and permission management.
"""

from typing import Any, Dict, Optional

from services.presence_service import PresenceService
from utils import get_class_logger


class WriterSessionConflictError(RuntimeError):
    """Raised when another write-capable session already owns the database lease."""

    def __init__(self, conflict_payload: Optional[Dict[str, Any]] = None):
        self.conflict_payload = conflict_payload or {}
        super().__init__(self._build_message(self.conflict_payload))

    @staticmethod
    def _build_message(conflict_payload: Dict[str, Any]) -> str:
        display_name = (
            conflict_payload.get("display_name")
            or conflict_payload.get("username")
            or "Bilinmeyen kullanici"
        )
        host = conflict_payload.get("host")
        if host:
            return (
                f"{display_name} kullanicisi ({host}) su anda veritabaninda "
                "yazma oturumu acik tutuyor."
            )
        return f"{display_name} kullanicisi su anda veritabaninda yazma oturumu acik tutuyor."


class AuthService:
    """Service for handling user authentication and permissions."""

    LEASE_FAILURE_THRESHOLD = 3

    def __init__(self, db):
        self.db = db
        self.logger = get_class_logger(self)
        self.current_user: Optional[Dict[str, Any]] = None
        self.is_guest = False
        self.presence_service = PresenceService(getattr(self.db, "db_adi", "projeler.db"))
        self._presence_session_id: Optional[str] = None
        self._write_session_active = False
        self._consecutive_lease_failures = 0
        self.last_auth_error: Dict[str, Any] = {}

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate a user with username/password and claim the writer lease."""
        self._clear_last_auth_error()
        try:
            user = self.db.verify_user(username, password)
            if not user:
                self._set_auth_error(
                    code="invalid_credentials",
                    message="Kullanici adi veya sifre hatali.",
                )
                self.logger.warning("Failed login attempt for username: %s", username)
                return False

            display_name = user.get("full_name") or user.get("username") or username
            lease = self.presence_service.try_acquire_writer_lock(
                username=user.get("username", username),
                display_name=display_name,
                session_id=self._presence_session_id,
            )
            if not lease.get("acquired"):
                conflict_payload = lease.get("payload") or {}
                error = WriterSessionConflictError(conflict_payload)
                self._set_auth_error(
                    code="writer_conflict",
                    message=str(error),
                    payload=conflict_payload,
                )
                self.logger.info(
                    "Writer lease denied for '%s': %s",
                    username,
                    str(error),
                )
                return False

            try:
                self.current_user = user
                self.is_guest = False
                self._write_session_active = True
                self._presence_session_id = (lease.get("payload") or {}).get("session_id")
                presence_payload = self._register_presence()
                if not presence_payload:
                    self._set_auth_error(
                        code="presence_register_failed",
                        message="Oturum kaydi olusturulamadi. Lutfen tekrar deneyin.",
                    )
                    self._reset_session_state(cleanup_presence=True)
                    return False

                self.db.update_last_login(user["id"])
                self.logger.info("User '%s' logged in successfully", username)
                return True
            except Exception:
                self._reset_session_state(cleanup_presence=True)
                raise
        except Exception as exc:
            self._set_auth_error(
                code="authentication_error",
                message=f"Kimlik dogrulama hatasi: {exc}",
            )
            self.logger.error("Authentication error: %s", exc, exc_info=True)
            return False

    def login_as_guest(self):
        """Set the session to guest mode (read-only access)."""
        self._clear_last_auth_error()
        self.close_session()
        self.current_user = None
        self.is_guest = True
        self._write_session_active = False
        self._consecutive_lease_failures = 0
        self._register_presence()
        self.logger.info("User logged in as guest")

    def logout(self):
        """Log out the current user."""
        if self.current_user:
            self.logger.info("User '%s' logged out", self.current_user.get("username"))
        self.close_session()
        self.current_user = None
        self.is_guest = False
        self._write_session_active = False
        self._consecutive_lease_failures = 0
        self._clear_last_auth_error()

    def is_logged_in(self) -> bool:
        return self.current_user is not None

    def has_permission(self, action: str) -> bool:
        if self.is_guest:
            return action in ["read", "view", "download", "export"]
        if self.current_user:
            if action == "write":
                return self._write_session_active
            return True
        return False

    def get_current_username(self) -> str:
        if self.current_user:
            return self.current_user.get("username", "Unknown")
        if self.is_guest:
            return "Misafir"
        return "Not Logged In"

    def get_current_display_name(self) -> str:
        if self.current_user:
            return self.current_user.get("full_name", self.current_user.get("username", "Unknown"))
        if self.is_guest:
            return "Misafir Kullanici"
        return "Not Logged In"

    def get_last_auth_error(self) -> Dict[str, Any]:
        return dict(self.last_auth_error)

    def get_write_state_message(self) -> str:
        if self.is_guest:
            return "Misafir oturum salt okunur calisiyor."
        if self.current_user and not self._write_session_active:
            return "Yazma oturumu aktif degil; uygulama salt okunur moda dusuruldu."
        return ""

    def bind_db(self, db):
        """Re-bind services to a new database file and preserve the active session mode."""
        identity = self._current_presence_identity()
        old_presence = self.presence_service
        old_session_id = self._presence_session_id

        new_presence = PresenceService(getattr(db, "db_adi", "projeler.db"))
        new_session_id = old_session_id

        if identity and identity.get("can_write"):
            lease = new_presence.try_acquire_writer_lock(
                username=identity["username"],
                display_name=identity["display_name"],
                session_id=old_session_id,
            )
            if not lease.get("acquired"):
                raise WriterSessionConflictError(lease.get("payload") or {})
            new_session_id = (lease.get("payload") or {}).get("session_id")

        try:
            if identity:
                payload = new_presence.register_session(
                    username=identity["username"],
                    display_name=identity["display_name"],
                    is_guest=identity["is_guest"],
                    can_write=identity["can_write"],
                    session_id=new_session_id,
                )
                new_session_id = payload.get("session_id")
        except Exception:
            if identity and identity.get("can_write"):
                new_presence.release_writer_lock(new_session_id)
            raise

        old_presence.release_writer_lock(old_session_id)
        old_presence.unregister_session(old_session_id)

        self.db = db
        self.presence_service = new_presence
        self._presence_session_id = new_session_id if identity else None
        self._write_session_active = bool(identity and identity.get("can_write"))

    def get_active_sessions(self, include_self: bool = False):
        sessions = self._normalize_sessions(self.presence_service.list_active_sessions())
        if include_self or not self._presence_session_id:
            return sessions
        return [
            session
            for session in sessions
            if session.get("session_id") != self._presence_session_id
        ]

    def get_active_writer_sessions(self, include_self: bool = False):
        return [
            session
            for session in self.get_active_sessions(include_self=include_self)
            if session.get("can_write")
        ]

    def heartbeat_session(self) -> bool:
        identity = self._current_presence_identity()
        if not identity:
            return True
        try:
            payload = self.presence_service.heartbeat_session(
                session_id=self._presence_session_id or "",
                username=identity["username"],
                display_name=identity["display_name"],
                is_guest=identity["is_guest"],
                can_write=identity["can_write"],
            )
            self._presence_session_id = payload.get("session_id")
            if identity["can_write"]:
                refreshed = self.presence_service.refresh_writer_lock(
                    session_id=self._presence_session_id,
                    username=identity["username"],
                    display_name=identity["display_name"],
                )
                if not refreshed:
                    return self._handle_lease_failure()
            self._consecutive_lease_failures = 0
        except Exception as exc:
            self.logger.debug("Presence heartbeat failed: %s", exc)
            return self._handle_lease_failure()
        return True

    def close_session(self):
        try:
            self.presence_service.release_writer_lock(self._presence_session_id)
        except Exception as exc:
            self.logger.debug("Presence writer lease release failed: %s", exc)

        try:
            self.presence_service.unregister_session(self._presence_session_id)
        except Exception as exc:
            self.logger.debug("Presence unregister failed: %s", exc)
        finally:
            self._presence_session_id = None
            self._write_session_active = False
            self._consecutive_lease_failures = 0

    def shutdown(self):
        self.close_session()

    def _register_presence(self):
        identity = self._current_presence_identity()
        if not identity:
            return None
        try:
            payload = self.presence_service.register_session(
                username=identity["username"],
                display_name=identity["display_name"],
                is_guest=identity["is_guest"],
                can_write=identity["can_write"],
                session_id=self._presence_session_id,
            )
            self._presence_session_id = payload.get("session_id")
            return payload
        except Exception as exc:
            self.logger.warning("Presence register failed: %s", exc)
            return None

    def _current_presence_identity(self):
        if self.current_user:
            return {
                "username": self.current_user.get("username", "unknown"),
                "display_name": self.get_current_display_name(),
                "is_guest": False,
                "can_write": self._write_session_active,
            }
        if self.is_guest:
            return {
                "username": "misafir",
                "display_name": self.get_current_display_name(),
                "is_guest": True,
                "can_write": False,
            }
        return None

    def _normalize_sessions(self, sessions):
        writer_lock = self.presence_service.get_writer_lock()
        if not writer_lock:
            return sessions

        writer_session_id = writer_lock.get("session_id")
        normalized = []
        writer_found = False
        for session in sessions:
            cloned = dict(session)
            if writer_session_id and cloned.get("session_id") == writer_session_id:
                cloned["can_write"] = True
                writer_found = True
            elif cloned.get("can_write"):
                cloned["can_write"] = False
            normalized.append(cloned)

        if writer_session_id and not writer_found:
            synthetic = dict(writer_lock)
            synthetic["is_guest"] = False
            synthetic["can_write"] = True
            normalized.insert(0, synthetic)
        return normalized

    def _clear_last_auth_error(self):
        self.last_auth_error = {}

    def _set_auth_error(self, code: str, message: str, payload: Optional[Dict[str, Any]] = None):
        self.last_auth_error = {
            "code": code,
            "message": message,
            "payload": dict(payload or {}),
        }

    def _reset_session_state(self, cleanup_presence: bool):
        if cleanup_presence:
            try:
                self.presence_service.release_writer_lock(self._presence_session_id)
            except Exception as exc:
                self.logger.debug("Presence writer lease release failed during reset: %s", exc)
            try:
                self.presence_service.unregister_session(self._presence_session_id)
            except Exception as exc:
                self.logger.debug("Presence unregister failed during reset: %s", exc)
        self.current_user = None
        self.is_guest = False
        self._write_session_active = False
        self._presence_session_id = None
        self._consecutive_lease_failures = 0

    def _downgrade_to_read_only(self):
        if not self.current_user or not self._write_session_active:
            return
        self._write_session_active = False
        self._consecutive_lease_failures = 0
        self._set_auth_error(
            code="writer_lease_lost",
            message="Yazma oturumu kaybedildi. Uygulama salt okunur moda dusuruldu.",
        )
        self._register_presence()

    def _handle_lease_failure(self) -> bool:
        if not self.current_user or not self._write_session_active:
            return False

        self._consecutive_lease_failures += 1
        self.logger.debug(
            "Writer lease heartbeat failed (%s/%s)",
            self._consecutive_lease_failures,
            self.LEASE_FAILURE_THRESHOLD,
        )
        if self._consecutive_lease_failures < self.LEASE_FAILURE_THRESHOLD:
            return True

        self._downgrade_to_read_only()
        return False
