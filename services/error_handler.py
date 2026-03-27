"""
Performance monitoring and error handling utilities.

PERFORMANCE: Added to improve debugging and user feedback for critical errors.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import QMessageBox, QWidget


logger = logging.getLogger(__name__)


def show_critical_error(parent: Optional[QWidget], title: str, message: str, details: Optional[str] = None):
    """
    Show a critical error dialog to the user.
    
    CRASH FIX: Instead of silently failing, show errors that need user attention.
    
    Args:
        parent: Parent widget for the dialog
        title: Error dialog title
        message: Main error message
        details: Optional detailed error information
    """
    try:
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if details:
            msg_box.setDetailedText(details)
        
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
    except Exception as e:
        # Fallback: at least log it
        logger.critical(f"Failed to show error dialog: {e}")
        logger.critical(f"Original error - {title}: {message}")
        if details:
            logger.critical(f"Details: {details}")


def show_warning(parent: Optional[QWidget], title: str, message: str):
    """
    Show a warning dialog to the user.
    
    Args:
        parent: Parent widget for the dialog
        title: Warning dialog title
        message: Warning message
    """
    try:
        QMessageBox.warning(parent, title, message)
    except Exception as e:
        logger.warning(f"Failed to show warning dialog: {e}")
        logger.warning(f"Original warning - {title}: {message}")


def safe_ui_operation(func, error_message="UI operation failed", show_error=False, parent=None):
    """
    Decorator/wrapper for UI operations that might fail.
    
    CRASH FIX: Prevents UI crashes by catching exceptions and optionally showing errors.
    
    Args:
        func: Function to execute safely
        error_message: Message to log/show if error occurs
        show_error: Whether to show error dialog to user
        parent: Parent widget for error dialog
    
    Returns:
        Result of func, or None if error occurred
    """
    try:
        return func()
    except Exception as e:
        logger.error(f"{error_message}: {e}", exc_info=True)
        if show_error:
            show_critical_error(
                parent,
                "Hata",
                error_message,
                str(e)
            )
        return None
