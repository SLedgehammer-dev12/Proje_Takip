"""
Authentication service for user login and permission management.
"""

import logging
from typing import Optional, Dict, Any
from utils import get_class_logger


class AuthService:
    """Service for handling user authentication and permissions."""

    def __init__(self, db):
        """Initialize the authentication service.
        
        Args:
            db: Database instance with user authentication methods
        """
        self.db = db
        self.logger = get_class_logger(self)
        self.current_user: Optional[Dict[str, Any]] = None
        self.is_guest = False

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate a user with username and password.
        
        Args:
            username: Username to authenticate
            password: Password to verify
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            user = self.db.verify_user(username, password)
            if user:
                self.current_user = user
                self.is_guest = False
                # Update last login timestamp
                self.db.update_last_login(user["id"])
                self.logger.info(f"User '{username}' logged in successfully")
                return True
            else:
                self.logger.warning(f"Failed login attempt for username: {username}")
                return False
        except Exception as e:
            self.logger.error(f"Authentication error: {e}", exc_info=True)
            return False

    def login_as_guest(self):
        """Set the session to guest mode (read-only access)."""
        self.current_user = None
        self.is_guest = True
        self.logger.info("User logged in as guest")

    def logout(self):
        """Log out the current user."""
        if self.current_user:
            self.logger.info(f"User '{self.current_user['username']}' logged out")
        self.current_user = None
        self.is_guest = False

    def is_logged_in(self) -> bool:
        """Check if a user is logged in.
        
        Returns:
            True if user is logged in (not guest), False otherwise
        """
        return self.current_user is not None

    def has_permission(self, action: str) -> bool:
        """Check if current user/session has permission for an action.
        
        Args:
            action: Action to check ('read', 'write', 'delete', 'admin', etc.)
            
        Returns:
            True if user has permission, False otherwise
        """
        # Guest mode: only read and download permissions
        if self.is_guest:
            return action in ['read', 'view', 'download', 'export']
        
        # Logged in users: full access
        if self.current_user:
            return True
        
        # Not logged in and not guest: no permissions
        return False

    def get_current_username(self) -> str:
        """Get the current user's username or 'Guest'.
        
        Returns:
            Username of current user or 'Misafir' for guests
        """
        if self.current_user:
            return self.current_user.get('username', 'Unknown')
        elif self.is_guest:
            return 'Misafir'
        else:
            return 'Not Logged In'

    def get_current_display_name(self) -> str:
        """Get the current user's display name.
        
        Returns:
            Full name of current user or 'Misafir Kullanıcı' for guests
        """
        if self.current_user:
            return self.current_user.get('full_name', self.current_user.get('username', 'Unknown'))
        elif self.is_guest:
            return 'Misafir Kullanıcı'
        else:
            return 'Not Logged In'
