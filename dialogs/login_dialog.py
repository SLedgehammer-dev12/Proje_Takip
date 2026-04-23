"""
Login dialog for user authentication.
"""

import html

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class LoginDialog(QDialog):
    """Dialog for user login or guest access."""

    def __init__(self, auth_service, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.login_successful = False
        self._presence_refresh_timer = QTimer(self)
        self._presence_refresh_timer.setInterval(3000)
        self._presence_refresh_timer.timeout.connect(self.refresh_active_sessions)
        self.setup_ui()
        self.refresh_active_sessions()
        self._presence_refresh_timer.start()

    def setup_ui(self):
        self.setWindowTitle("Proje Takip Sistemi - Giriş")
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        title_label = QLabel("Kullanıcı Girişi")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        subtitle_label = QLabel(
            "Lütfen kullanıcı bilgilerinizi girin veya misafir olarak devam edin."
        )
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)

        session_frame = QFrame()
        session_frame.setFrameShape(QFrame.StyledPanel)
        session_layout = QVBoxLayout(session_frame)
        session_layout.setContentsMargins(12, 12, 12, 12)
        session_layout.setSpacing(8)
        session_title = QLabel("Aktif Veritabanı Oturumları")
        session_title.setAlignment(Qt.AlignCenter)
        session_layout.addWidget(session_title)
        self.session_info_label = QLabel()
        self.session_info_label.setWordWrap(True)
        self.session_info_label.setTextFormat(Qt.RichText)
        session_layout.addWidget(self.session_info_label)
        layout.addWidget(session_frame)

        layout.addSpacing(10)

        username_label = QLabel("Kullanıcı Adı:")
        layout.addWidget(username_label)
        self.username_field = QLineEdit()
        self.username_field.setPlaceholderText("Kullanıcı adınızı girin")
        self.username_field.setMinimumHeight(35)
        layout.addWidget(self.username_field)

        password_label = QLabel("Şifre:")
        layout.addWidget(password_label)
        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Şifrenizi girin")
        self.password_field.setEchoMode(QLineEdit.Password)
        self.password_field.setMinimumHeight(35)
        self.password_field.returnPressed.connect(self.on_login_clicked)
        layout.addWidget(self.password_field)

        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)

        self.login_btn = QPushButton("Giriş Yap")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.setDefault(True)
        self.login_btn.clicked.connect(self.on_login_clicked)
        buttons_layout.addWidget(self.login_btn)

        self.guest_btn = QPushButton("Misafir Olarak Devam Et")
        self.guest_btn.setMinimumHeight(40)
        self.guest_btn.clicked.connect(self.on_guest_clicked)
        buttons_layout.addWidget(self.guest_btn)

        layout.addSpacing(10)
        layout.addLayout(buttons_layout)

        info_label = QLabel(
            "<i>Misafir mod: Sadece görüntüleme ve indirme yetkisi</i>"
        )
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.setLayout(layout)

        self.username_field.setFocus()
        self.setTabOrder(self.username_field, self.password_field)
        self.setTabOrder(self.password_field, self.login_btn)
        self.setTabOrder(self.login_btn, self.guest_btn)
        self.setTabOrder(self.guest_btn, self.username_field)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.raise_()
            self.activateWindow()
        except Exception:
            pass

    def on_login_clicked(self):
        username = self.username_field.text().strip()
        password = self.password_field.text()

        if not username or not password:
            QMessageBox.warning(
                self,
                "Eksik Bilgi",
                "Lütfen kullanıcı adı ve şifre girin.",
            )
            return

        if self.auth_service.authenticate(username, password):
            self.login_successful = True
            self._presence_refresh_timer.stop()
            QMessageBox.information(
                self,
                "Başarılı",
                f"Hos geldiniz, {self.auth_service.get_current_display_name()}!",
            )
            self.accept()
            return

        auth_error = self.auth_service.get_last_auth_error()
        if auth_error.get("code") == "writer_conflict":
            QMessageBox.warning(
                self,
                "Veritabanı Kullanımda",
                f"{auth_error.get('message')}\n\n"
                "Yazma oturumu serbest kalana kadar misafir olarak devam edebilirsiniz.",
            )
            self.refresh_active_sessions()
            self.guest_btn.setFocus()
            return

        if auth_error.get("code") and auth_error.get("code") != "invalid_credentials":
            QMessageBox.warning(
                self,
                "Giriş Başarısız",
                auth_error.get("message")
                or "Giriş sırasında beklenmeyen bir hata oluştu.",
            )
            self.password_field.clear()
            self.password_field.setFocus()
            return

        QMessageBox.warning(
            self,
            "Giriş Başarısız",
            "Kullanıcı adı veya şifre hatalı.\n\nLütfen tekrar deneyin.",
        )
        self.password_field.clear()
        self.password_field.setFocus()

    def on_guest_clicked(self):
        reply = QMessageBox.question(
            self,
            "Misafir Modu",
            "Misafir olarak devam etmek istediğinizden emin misiniz?\n\n"
            "Misafir modunda sadece görüntüleme ve indirme yetkiniz olacak.\n"
            "Düzenleme, ekleme ve silme işlemleri yapamayacaksınız.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.auth_service.login_as_guest()
            self.login_successful = True
            self._presence_refresh_timer.stop()
            self.accept()

    def refresh_active_sessions(self):
        try:
            sessions = self.auth_service.get_active_sessions(include_self=False)
        except Exception:
            self.session_info_label.setText("Aktif oturum bilgisi alınamadı.")
            return

        if not sessions:
            self.session_info_label.setText("Aktif oturum görünmüyor.")
            return

        writer_sessions = [session for session in sessions if session.get("can_write")]
        guest_sessions = [session for session in sessions if session.get("is_guest")]
        lines = []

        if writer_sessions:
            labels = []
            for session in writer_sessions:
                display_name = html.escape(
                    session.get("display_name") or session.get("username") or "Bilinmeyen"
                )
                host_name = html.escape(session.get("host") or "?")
                labels.append(f"{display_name} <i>({host_name})</i>")
            lines.append("<b>Yazma yetkili aktif kullanici:</b> " + ", ".join(labels))
        else:
            lines.append("<b>Yazma yetkili aktif kullanici:</b> Yok")

        lines.append(f"<b>Misafir oturum sayısı:</b> {len(guest_sessions)}")
        lines.append("<i>Misafir oturumlar salt okunur çalışır.</i>")
        self.session_info_label.setText("<br>".join(lines))

    def closeEvent(self, event):
        try:
            self._presence_refresh_timer.stop()
        except Exception:
            pass

        if not self.login_successful:
            reply = QMessageBox.question(
                self,
                "Cikis",
                "Giriş yapmadan çıkmak istediğinizden emin misiniz?\n\n"
                "Uygulama kapatılacaktır.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                event.accept()
                self.reject()
            else:
                event.ignore()
        else:
            event.accept()
