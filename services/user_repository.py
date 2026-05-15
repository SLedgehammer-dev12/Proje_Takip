"""
User repository for authentication and user management.
Extracted from database.py to reduce coupling and improve testability.
"""

import datetime
import logging
from typing import Any, Dict, Optional

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "bcrypt not available - user authentication will not work. Install with: pip install bcrypt"
    )


class UserRepository:
    """Handles all user-related database operations: CRUD, password hashing, and authentication."""

    def __init__(self, db_instance):
        self._db = db_instance
        self.logger = logging.getLogger(self.__class__.__name__)

    # -------------------------------------------------------------------------
    # Password helpers
    # -------------------------------------------------------------------------

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        if not BCRYPT_AVAILABLE:
            raise RuntimeError("bcrypt is not installed")
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        if not BCRYPT_AVAILABLE:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # User CRUD
    # -------------------------------------------------------------------------

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information by username."""
        try:
            self._db.cursor.execute(
                """SELECT id, username, password_hash, full_name, role, created_at, last_login
                   FROM users WHERE username = ?""",
                (username,),
            )
            row = self._db.cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "username": row[1],
                    "password_hash": row[2],
                    "full_name": row[3],
                    "role": row[4],
                    "created_at": row[5],
                    "last_login": row[6],
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get user: {e}", exc_info=True)
            return None

    def verify(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials and return user info if valid."""
        user = self.get_by_username(username)
        if user and self.verify_password(password, user["password_hash"]):
            return user
        return None

    def update_last_login(self, user_id: int):
        """Update the last_login timestamp for a user."""
        try:
            with self._db.transaction():
                self._db.cursor.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.datetime.now(), user_id),
                )
        except Exception as e:
            self.logger.error(f"Failed to update last login: {e}", exc_info=True)

    # -------------------------------------------------------------------------
    # Initial user seeding
    # -------------------------------------------------------------------------

    _INITIAL_USERS = [
        {
            "username": "alperb.yilmaz",
            "password": "Botas.2025",
            "full_name": "Alper Berkan Yılmaz",
            "role": "admin",
        },
        {
            "username": "omer.erbas",
            "password": "Botas.2025",
            "full_name": "Ömer Erbaş",
            "role": "admin",
        },
    ]

    def create_initial_users(self):
        """Create initial users if users table is empty, or fix broken hashes."""
        if not BCRYPT_AVAILABLE:
            self.logger.warning("bcrypt is not available; skipping user setup.")
            return

        try:
            for user_data in self._INITIAL_USERS:
                existing = self.get_by_username(user_data["username"])
                needs_upsert = False

                if existing is None:
                    needs_upsert = True
                else:
                    ph = (existing.get("password_hash") or "").strip()
                    is_valid_bcrypt = ph.startswith("$2b$") or ph.startswith("$2a$") or ph.startswith("$2y$")
                    if not is_valid_bcrypt:
                        self.logger.info(
                            "Kullanıcı %s için geçersiz/eksik hash bulundu; yeniden oluşturuluyor.",
                            user_data["username"],
                        )
                        needs_upsert = True

                if needs_upsert:
                    password_hash = self.hash_password(user_data["password"])
                    with self._db.transaction():
                        self._db.cursor.execute(
                            """INSERT INTO users (username, password_hash, full_name, role, created_at)
                               VALUES (?, ?, ?, ?, ?)
                               ON CONFLICT(username) DO UPDATE SET
                                   password_hash = excluded.password_hash,
                                   full_name = excluded.full_name,
                                   role = excluded.role""",
                            (
                                user_data["username"],
                                password_hash,
                                user_data["full_name"],
                                user_data["role"],
                                datetime.datetime.now(),
                            ),
                        )
                    self.logger.info("Kullanıcı oluşturuldu/güncellendi: %s", user_data["username"])

        except Exception as e:
            self.logger.error(f"Failed to create/update initial users: {e}", exc_info=True)
