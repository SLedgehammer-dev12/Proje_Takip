"""
Login dialog for user authentication.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon


class LoginDialog(QDialog):
    """Dialog for user login or guest access."""

    def __init__(self, auth_service, parent=None):
        """Initialize the login dialog.
        
        Args:
            auth_service: AuthService instance for authentication
            parent: Parent widget
        """
        super().__init__(parent)
        self.auth_service = auth_service
        self.login_successful = False
        self.setup_ui()

    def setup_ui(self):
        """Set up the login dialog UI."""
        self.setWindowTitle("Proje Takip Sistemi - Giriş")
        # Ensure dialog is front and blocks app until choice is made
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title_label = QLabel("🔐 Kullanıcı Girişi")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Lütfen kullanıcı bilgilerinizi girin veya misafir olarak devam edin")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)

        # Spacer
        layout.addSpacing(10)

        # Username field
        username_label = QLabel("Kullanıcı Adı:")
        layout.addWidget(username_label)
        
        self.username_field = QLineEdit()
        self.username_field.setPlaceholderText("Kullanıcı adınızı girin")
        self.username_field.setMinimumHeight(35)
        layout.addWidget(self.username_field)

        # Password field
        password_label = QLabel("Şifre:")
        layout.addWidget(password_label)
        
        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Şifrenizi girin")
        self.password_field.setEchoMode(QLineEdit.Password)
        self.password_field.setMinimumHeight(35)
        self.password_field.returnPressed.connect(self.on_login_clicked)
        layout.addWidget(self.password_field)

        # Buttons layout
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)

        # Login button
        self.login_btn = QPushButton("🔓 Giriş Yap")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.setDefault(True)
        self.login_btn.clicked.connect(self.on_login_clicked)
        buttons_layout.addWidget(self.login_btn)

        # Guest button
        self.guest_btn = QPushButton("👤 Misafir Olarak Devam Et")
        self.guest_btn.setMinimumHeight(40)
        self.guest_btn.clicked.connect(self.on_guest_clicked)
        buttons_layout.addWidget(self.guest_btn)

        layout.addSpacing(10)
        layout.addLayout(buttons_layout)

        # Info label
        info_label = QLabel(
            "💡 <i>Misafir mod: Sadece görüntüleme ve indirme yetkisi</i>"
        )
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.setLayout(layout)

        # Set focus and tab order for quick keyboard navigation (Tab/Shift+Tab)
        self.username_field.setFocus()
        self.setTabOrder(self.username_field, self.password_field)
        self.setTabOrder(self.password_field, self.login_btn)
        self.setTabOrder(self.login_btn, self.guest_btn)
        self.setTabOrder(self.guest_btn, self.username_field)

    def showEvent(self, event):
        """Force the dialog to come to the foreground when shown."""
        super().showEvent(event)
        try:
            self.raise_()
            self.activateWindow()
        except Exception:
            pass

    def on_login_clicked(self):
        """Handle login button click."""
        username = self.username_field.text().strip()
        password = self.password_field.text()

        if not username or not password:
            QMessageBox.warning(
                self,
                "Eksik Bilgi",
                "Lütfen kullanıcı adı ve şifre girin."
            )
            return

        # Try to authenticate
        if self.auth_service.authenticate(username, password):
            self.login_successful = True
            QMessageBox.information(
                self,
                "Başarılı",
                f"Hoş geldiniz, {self.auth_service.get_current_display_name()}!"
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Giriş Başarısız",
                "Kullanıcı adı veya şifre hatalı.\n\nLütfen tekrar deneyin."
            )
            self.password_field.clear()
            self.password_field.setFocus()

    def on_guest_clicked(self):
        """Handle guest button click."""
        reply = QMessageBox.question(
            self,
            "Misafir Modu",
            "Misafir olarak devam etmek istediğinizden emin misiniz?\n\n"
            "Misafir modunda sadece görüntüleme ve indirme yetkiniz olacak.\n"
            "Düzenleme, ekleme ve silme işlemleri yapamayacaksınız.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.auth_service.login_as_guest()
            self.login_successful = True
            self.accept()

    def closeEvent(self, event):
        """Handle dialog close event."""
        if not self.login_successful:
            reply = QMessageBox.question(
                self,
                "Çıkış",
                "Giriş yapmadan çıkmak istediğinizden emin misiniz?\n\n"
                "Uygulama kapatılacaktır.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                event.accept()
                self.reject()
            else:
                event.ignore()
        else:
            event.accept()
