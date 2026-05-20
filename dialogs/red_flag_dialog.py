from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QDialogButtonBox, QMessageBox, QPushButton, QFrame,
)
from PySide6.QtCore import Qt
from datetime import datetime


class RedFlagDialog(QDialog):
    """Red flag ekleme/kaldırma dialogu - sebep, kullanıcı ve tarih bilgisi kaydeder."""

    def __init__(self, parent, revizyon_info: str, current_user: str, existing_reason: str = None):
        super().__init__(parent)
        self.setWindowTitle("🚩 Hatalı Kayıt İşareti")
        self.setMinimumSize(480, 320)
        self.setModal(True)

        self.revizyon_info = revizyon_info
        self.current_user = current_user
        self.existing_reason = existing_reason

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(
            f"<b>Revizyon:</b> {revizyon_info}<br>"
            f"<b>Kullanıcı:</b> {current_user}<br>"
            f"<b>Tarih:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        title.setWordWrap(True)
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        if existing_reason:
            self.mode = "kaldir"
            reason_label = QLabel("<b>Mevcut İşaret Sebebi:</b>")
            layout.addWidget(reason_label)

            reason_display = QLabel(existing_reason)
            reason_display.setWordWrap(True)
            reason_display.setStyleSheet(
                "background-color: #fff3cd; border: 1px solid #ffc107; "
                "border-radius: 4px; padding: 8px;"
            )
            layout.addWidget(reason_display)

            info_label = QLabel(
                "Bu işareti kaldırmak için onaylayın. "
                "Eğer sorun çözüldüyse işareti kaldırabilirsiniz."
            )
            info_label.setWordWrap(True)
            layout.addWidget(info_label)

            self.reason_edit = None
            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.button(QDialogButtonBox.Ok).setText("🗑️ İşareti Kaldır")
            buttons.accepted.connect(self._confirm_remove)
        else:
            self.mode = "ekle"
            reason_label = QLabel("<b>İşaret Sebebi:</b> (zorunlu)")
            layout.addWidget(reason_label)

            self.reason_edit = QTextEdit()
            self.reason_edit.setPlaceholderText(
                "Bu revizyonun neden hatalı olduğunu açıklayın..."
            )
            self.reason_edit.setMinimumHeight(100)
            layout.addWidget(self.reason_edit)

            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.button(QDialogButtonBox.Ok).setText("🚩 İşaretle")
            buttons.accepted.connect(self._validate_and_accept)

        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate_and_accept(self):
        reason = self.reason_edit.toPlainText().strip()
        if not reason:
            QMessageBox.warning(
                self, "Eksik Bilgi",
                "Lütfen işaret sebebini açıklayın."
            )
            return
        self.reason = reason
        self.accept()

    def _confirm_remove(self):
        self.reason = ""
        self.accept()

    def get_flag_data(self):
        return {
            "flagged": self.mode == "ekle",
            "reason": getattr(self, "reason", self.existing_reason or ""),
            "user": self.current_user,
            "date": datetime.now().isoformat(),
        }
