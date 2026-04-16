"""
File service for handling document downloads and file operations.

This service encapsulates all file-related operations such as downloading,
saving, and opening documents from the database.
"""

import logging
import os
import subprocess
import sys
import tempfile
from typing import Optional, Tuple

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget
from utils import get_class_logger


class FileService:
    """
    Service class for file operations.

    Handles downloading documents, letters, and providing file save dialogs.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the FileService.

        Args:
            parent: Parent widget for dialogs
        """
        self.parent = parent
        self.logger = get_class_logger(self)

    def save_file_dialog(self, filename: str, file_data: bytes) -> bool:
        """
        Show a save file dialog and save the data to the selected location.

        Args:
            filename: Suggested filename
            file_data: Binary data to save

        Returns:
            True if file was saved successfully, False otherwise
        """
        try:
            save_path, _ = QFileDialog.getSaveFileName(self.parent, "Kaydet", filename)

            if not save_path:
                return False

            with open(save_path, "wb") as f:
                f.write(file_data)

            QMessageBox.information(self.parent, "Başarılı", "Dosya kaydedildi.")
            return True

        except Exception as e:
            self.logger.error(f"Dosya kaydetme hatası: {e}", exc_info=True)
            QMessageBox.critical(self.parent, "Hata", f"Dosya kaydedilemedi: {e}")
            return False

    def open_temporary_document(
        self,
        filename: str,
        file_data: bytes,
        *,
        temp_prefix: str,
        error_title: str = "Açma Hatası",
    ) -> bool:
        """
        Persist a document to a temporary file and ask the OS to open it.

        Args:
            filename: Source filename used to preserve extension
            file_data: Binary data to write to the temp file
            temp_prefix: Prefix used for the temporary file name
            error_title: Dialog title used when opening fails

        Returns:
            True if the OS accepted the open request, False otherwise
        """
        if not file_data:
            QMessageBox.warning(self.parent, "Uyarı", "Açılacak doküman verisi bulunamadı.")
            return False

        try:
            _, ext = os.path.splitext(filename or "")
            if not ext:
                ext = ".pdf"

            safe_prefix = "".join(
                ch if ch.isalnum() else "_" for ch in temp_prefix
            ).strip("_")
            safe_prefix = (safe_prefix or "proje_takip") + "_"

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=ext,
                prefix=safe_prefix,
            ) as temp_file:
                temp_file.write(file_data)
                temp_path = temp_file.name

            if not self._open_file_with_system_handler(temp_path):
                QMessageBox.warning(
                    self.parent,
                    error_title,
                    (
                        "Dosya açılamadı. Lütfen varsayılan PDF/doküman "
                        "görüntüleyicinizi kontrol edin."
                    ),
                )
                return False
            return True
        except Exception as e:
            self.logger.error(f"Geçici doküman açma hatası: {e}", exc_info=True)
            QMessageBox.critical(
                self.parent,
                error_title,
                f"Doküman açılırken hata oluştu: {e}",
            )
            return False

    def _open_file_with_system_handler(self, file_path: str) -> bool:
        """Open a local file using the most reliable OS-native method."""
        try:
            if sys.platform == "win32" and hasattr(os, "startfile"):
                os.startfile(file_path)
                return True
            if sys.platform == "darwin":
                completed = subprocess.run(["open", file_path], check=False)
                return completed.returncode == 0
            if sys.platform.startswith("linux"):
                completed = subprocess.run(["xdg-open", file_path], check=False)
                return completed.returncode == 0

            url = QUrl.fromLocalFile(file_path)
            return QDesktopServices.openUrl(url)
        except Exception:
            self.logger.error(
                "Sistem varsayilan uygulamasi ile dosya acma hatasi: %s",
                file_path,
                exc_info=True,
            )
            return False

    def download_document(self, document: Optional[Tuple[str, bytes]]) -> bool:
        """
        Download a document (filename and data tuple).

        Args:
            document: Tuple of (filename, file_data) or None

        Returns:
            True if downloaded successfully, False otherwise
        """
        if not document:
            QMessageBox.warning(self.parent, "Hata", "Doküman bulunamadı.")
            return False

        filename, file_data = document
        return self.save_file_dialog(filename, file_data)

    def download_letter_document(
        self,
        document: Optional[Tuple[str, bytes]],
        letter_no: str,
        letter_type: str = "yazı",
    ) -> bool:
        """
        Download a letter document with specific error message.

        Args:
            document: Tuple of (filename, file_data) or None
            letter_no: Letter number for error message
            letter_type: Type of letter (e.g., "gelen yazı", "onay")

        Returns:
            True if downloaded successfully, False otherwise
        """
        if not document:
            QMessageBox.warning(
                self.parent,
                "Hata",
                f"{letter_no} numaralı {letter_type} dokümanı veritabanında bulunamadı.",
            )
            return False

        filename, file_data = document
        return self.save_file_dialog(filename, file_data)
