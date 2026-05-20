"""
User repository for authentication and user management.
Extracted from database.py to reduce coupling and improve testability.
"""

import datetime
import logging
import os
from typing import Any, Dict, List, Optional

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "bcrypt not available - user authentication will not work. Install with: pip install bcrypt"
    )


VALID_ROLES = ("admin", "editor", "viewer")


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

    def _row_to_dict(self, row) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "password_hash": row[2],
            "full_name": row[3],
            "role": row[4],
            "is_active": bool(row[5]),
            "created_at": row[6],
            "last_login": row[7],
        }

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information by username."""
        try:
            self._db.cursor.execute(
                """SELECT id, username, password_hash, full_name, role, is_active, created_at, last_login
                   FROM users WHERE username = ?""",
                (username,),
            )
            return self._row_to_dict(self._db.cursor.fetchone())
        except Exception as e:
            self.logger.error(f"Failed to get user: {e}", exc_info=True)
            return None

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information by user ID."""
        try:
            self._db.cursor.execute(
                """SELECT id, username, password_hash, full_name, role, is_active, created_at, last_login
                   FROM users WHERE id = ?""",
                (user_id,),
            )
            return self._row_to_dict(self._db.cursor.fetchone())
        except Exception as e:
            self.logger.error(f"Failed to get user by id: {e}", exc_info=True)
            return None

    def create_user(self, username: str, password: str, full_name: str = "", role: str = "viewer") -> Optional[int]:
        """Create a new user. Returns user ID on success, None on failure."""
        if role not in VALID_ROLES:
            self.logger.error(f"Invalid role: {role}")
            return None
        if not username or not password:
            return None
        if not BCRYPT_AVAILABLE:
            self.logger.error("bcrypt not available - cannot create user")
            return None
        try:
            password_hash = self.hash_password(password)
            with self._db.transaction():
                self._db.cursor.execute(
                    """INSERT INTO users (username, password_hash, full_name, role, is_active, created_at)
                       VALUES (?, ?, ?, ?, 1, ?)""",
                    (username.strip(), password_hash, full_name.strip(), role, datetime.datetime.now()),
                )
                user_id = self._db.cursor.lastrowid
            self.logger.info(f"User created: {username} (role={role})")
            return user_id
        except Exception as e:
            self.logger.error(f"Failed to create user {username}: {e}", exc_info=True)
            return None

    def update_user(self, user_id: int, full_name: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None) -> bool:
        """Update user details. Only non-None fields are updated."""
        try:
            fields = []
            params = []
            if full_name is not None:
                fields.append("full_name = ?")
                params.append(full_name.strip())
            if role is not None:
                if role not in VALID_ROLES:
                    self.logger.error(f"Invalid role: {role}")
                    return False
                fields.append("role = ?")
                params.append(role)
            if is_active is not None:
                fields.append("is_active = ?")
                params.append(1 if is_active else 0)
            if not fields:
                return False
            params.append(user_id)
            with self._db.transaction():
                self._db.cursor.execute(
                    f"UPDATE users SET {', '.join(fields)} WHERE id = ?",
                    params,
                )
            self.logger.info(f"User {user_id} updated: {', '.join(fields)}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update user {user_id}: {e}", exc_info=True)
            return False

    def change_password(self, user_id: int, new_password: str) -> bool:
        """Change a user's password."""
        if not new_password:
            return False
        if not BCRYPT_AVAILABLE:
            self.logger.error("bcrypt not available - cannot change password")
            return False
        try:
            password_hash = self.hash_password(new_password)
            with self._db.transaction():
                self._db.cursor.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (password_hash, user_id),
                )
            self.logger.info(f"Password changed for user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to change password for user {user_id}: {e}", exc_info=True)
            return False

    def delete_user(self, user_id: int) -> bool:
        """Delete a user. Cannot delete your own session's user (check externally)."""
        try:
            with self._db.transaction():
                self._db.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                deleted = self._db.cursor.rowcount > 0
            if deleted:
                self.logger.info(f"User {user_id} deleted")
            return deleted
        except Exception as e:
            self.logger.error(f"Failed to delete user {user_id}: {e}", exc_info=True)
            return False

    def list_users(self) -> List[Dict[str, Any]]:
        """List all users (password_hash excluded from return)."""
        try:
            self._db.cursor.execute(
                """SELECT id, username, full_name, role, is_active, created_at, last_login
                   FROM users ORDER BY username ASC"""
            )
            return [
                {
                    "id": row[0],
                    "username": row[1],
                    "full_name": row[2] or "",
                    "role": row[3],
                    "is_active": bool(row[4]),
                    "created_at": row[5],
                    "last_login": row[6],
                }
                for row in self._db.cursor.fetchall()
            ]
        except Exception as e:
            self.logger.error(f"Failed to list users: {e}", exc_info=True)
            return []

    def verify(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials and return user info if valid. Only active users can log in."""
        user = self.get_by_username(username)
        if user and user.get("is_active", False) and self.verify_password(password, user["password_hash"]):
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

    def _get_initial_user_credentials(self):
        users_from_env = os.environ.get("PROJETAKIP_INITIAL_USERS", "")
        if users_from_env:
            import json
            try:
                return json.loads(users_from_env)
            except Exception as e:
                self.logger.warning("PROJETAKIP_INITIAL_USERS parse edilemedi: %s", e)

        return [
            {
                "username": os.environ.get("PROJETAKIP_ADMIN_USER", "alperb.yilmaz"),
                "password": os.environ.get("PROJETAKIP_ADMIN_PASS", "Botas.2025"),
                "full_name": "Alper Berkan Yılmaz",
                "role": "admin",
            },
            {
                "username": os.environ.get("PROJETAKIP_ADMIN_USER_2", "omer.erbas"),
                "password": os.environ.get("PROJETAKIP_ADMIN_PASS_2", "Botas.2025"),
                "full_name": "Ömer Erbaş",
                "role": "admin",
            },
        ]

    _INITIAL_USERS = None

    def create_initial_users(self):
        """Create initial users if users table is empty, or fix broken hashes."""
        if not BCRYPT_AVAILABLE:
            self.logger.warning("bcrypt is not available; skipping user setup.")
            return

        try:
            for user_data in self._get_initial_user_credentials():
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
                            """INSERT INTO users (username, password_hash, full_name, role, is_active, created_at)
                               VALUES (?, ?, ?, ?, 1, ?)
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
