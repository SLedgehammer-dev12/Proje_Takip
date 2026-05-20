from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QComboBox, QFormLayout, QDialogButtonBox,
)
from PySide6.QtCore import Qt


class UserManagerDialog(QDialog):
    """Admin panel for managing application users."""

    def __init__(self, parent, auth_service, user_repo):
        super().__init__(parent)
        self.auth_service = auth_service
        self.user_repo = user_repo
        self.setWindowTitle("Kullanıcı Yönetimi")
        self.setMinimumSize(700, 450)
        self.setModal(True)
        self.setup_ui()
        self.refresh_table()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("<b>Kullanıcı Yönetimi</b>")
        header.setStyleSheet("font-size: 14pt;")
        layout.addWidget(header)

        info = QLabel(
            "Kullanıcı ekleme, düzenleme, şifre sıfırlama ve silme işlemleri. "
            "Kendinizi silemezsiniz."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 9pt; margin-bottom: 4px;")
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Kullanıcı Adı", "Tam İsim", "Rol", "Durum", "Son Giriş"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ Kullanıcı Ekle")
        self.edit_btn = QPushButton("✏️ Düzenle")
        self.reset_pwd_btn = QPushButton("🔑 Şifre Sıfırla")
        self.delete_btn = QPushButton("🗑️ Sil")
        self.refresh_btn = QPushButton("🔄 Yenile")
        self.close_btn = QPushButton("Kapat")

        self.add_btn.clicked.connect(self._add_user)
        self.edit_btn.clicked.connect(self._edit_user)
        self.reset_pwd_btn.clicked.connect(self._reset_password)
        self.delete_btn.clicked.connect(self._delete_user)
        self.refresh_btn.clicked.connect(self.refresh_table)
        self.close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.reset_pwd_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def refresh_table(self):
        self.table.setRowCount(0)
        users = self.user_repo.list_users()
        current_username = self.auth_service.get_current_username()
        for user in users:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(user["username"]))
            self.table.setItem(row, 2, QTableWidgetItem(user["full_name"] or ""))
            role_text = {"admin": "Admin", "editor": "Editör", "viewer": "İzleyici"}.get(
                user["role"], user["role"]
            )
            if user["username"] == current_username:
                role_text += " (siz)"
            self.table.setItem(row, 3, QTableWidgetItem(role_text))
            status_text = "✅ Aktif" if user["is_active"] else "❌ Pasif"
            self.table.setItem(row, 4, QTableWidgetItem(status_text))
            last_login = user["last_login"] or "-"
            self.table.setItem(row, 5, QTableWidgetItem(str(last_login)))

    def _get_selected_user(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir kullanıcı seçin.")
            return None
        user_id = int(self.table.item(rows[0].row(), 0).text())
        return self.user_repo.get_by_id(user_id)

    def _add_user(self):
        dialog = _UserEditDialog(self, mode="add")
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            user_id = self.user_repo.create_user(
                username=data["username"],
                password=data["password"],
                full_name=data["full_name"],
                role=data["role"],
            )
            if user_id:
                QMessageBox.information(self, "Başarılı", f"Kullanıcı '{data['username']}' oluşturuldu.")
                self.refresh_table()
            else:
                QMessageBox.critical(self, "Hata", "Kullanıcı oluşturulamadı. Kullanıcı adı mevcut olabilir.")

    def _edit_user(self):
        user = self._get_selected_user()
        if not user:
            return
        dialog = _UserEditDialog(self, mode="edit", user=user)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success = self.user_repo.update_user(
                user["id"],
                full_name=data.get("full_name"),
                role=data.get("role"),
                is_active=data.get("is_active"),
            )
            if success:
                QMessageBox.information(self, "Başarılı", "Kullanıcı güncellendi.")
                self.refresh_table()
            else:
                QMessageBox.critical(self, "Hata", "Kullanıcı güncellenemedi.")

    def _reset_password(self):
        user = self._get_selected_user()
        if not user:
            return
        dialog = _PasswordResetDialog(self, user["username"])
        if dialog.exec() == QDialog.Accepted:
            new_password = dialog.get_password()
            if self.user_repo.change_password(user["id"], new_password):
                QMessageBox.information(self, "Başarılı", "Şifre sıfırlandı.")
            else:
                QMessageBox.critical(self, "Hata", "Şifre sıfırlanamadı.")

    def _delete_user(self):
        user = self._get_selected_user()
        if not user:
            return
        current_username = self.auth_service.get_current_username()
        if user["username"] == current_username:
            QMessageBox.warning(self, "Uyarı", "Kendinizi silemezsiniz!")
            return
        reply = QMessageBox.question(
            self, "Kullanıcı Sil",
            f"'{user['username']}' kullanıcısını silmek istediğinize emin misiniz?\n\nBu işlem geri alınamaz.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if self.user_repo.delete_user(user["id"]):
                QMessageBox.information(self, "Başarılı", "Kullanıcı silindi.")
                self.refresh_table()


class _UserEditDialog(QDialog):
    def __init__(self, parent, mode="add", user=None):
        super().__init__(parent)
        self.mode = mode
        self.user = user
        self.setWindowTitle("Kullanıcı Ekle" if mode == "add" else "Kullanıcı Düzenle")
        self.setMinimumWidth(400)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)

        self.username_input = QLineEdit()
        if self.mode == "add":
            self.username_input.setPlaceholderText("Kullanıcı adı (zorunlu)")
            layout.addRow("Kullanıcı Adı:", self.username_input)
        else:
            self.username_label = QLabel(f"<b>{self.user['username']}</b>")
            layout.addRow("Kullanıcı Adı:", self.username_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tam ad (opsiyonel)")
        if self.user:
            self.name_input.setText(self.user.get("full_name", ""))
        layout.addRow("Tam İsim:", self.name_input)

        if self.mode == "add":
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.setPlaceholderText("Şifre (zorunlu)")
            layout.addRow("Şifre:", self.password_input)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["viewer", "editor", "admin"])
        role_labels = {"viewer": "İzleyici (salt okunur)", "editor": "Editör (yazma + okuma)", "admin": "Admin (tüm yetkiler)"}
        for i in range(self.role_combo.count()):
            self.role_combo.setItemText(i, role_labels.get(self.role_combo.itemText(i), self.role_combo.itemText(i)))
        if self.user:
            current_role = self.user.get("role", "viewer")
            idx = self.role_combo.findText(role_labels.get(current_role, current_role))
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)
        layout.addRow("Rol:", self.role_combo)

        if self.mode == "edit":
            self.active_combo = QComboBox()
            is_active = self.user.get("is_active", True) if self.user else True
            self.active_combo.addItems(["Aktif", "Pasif"])
            self.active_combo.setCurrentIndex(0 if is_active else 1)
            layout.addRow("Durum:", self.active_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _validate(self):
        if self.mode == "add":
            username = self.username_input.text().strip()
            password = self.password_input.text()
            if not username or not password:
                QMessageBox.warning(self, "Eksik Bilgi", "Kullanıcı adı ve şifre zorunludur.")
                return
        self.accept()

    def get_data(self):
        role_map = {
            "İzleyici (salt okunur)": "viewer",
            "Editör (yazma + okuma)": "editor",
            "Admin (tüm yetkiler)": "admin",
        }
        data = {
            "full_name": self.name_input.text().strip(),
            "role": role_map.get(self.role_combo.currentText(), "viewer"),
        }
        if self.mode == "add":
            data["username"] = self.username_input.text().strip()
            data["password"] = self.password_input.text()
        if self.mode == "edit":
            data["is_active"] = (self.active_combo.currentText() == "Aktif")
        return data


class _PasswordResetDialog(QDialog):
    def __init__(self, parent, username):
        super().__init__(parent)
        self.setWindowTitle(f"Şifre Sıfırla - {username}")
        self.setMinimumWidth(350)
        self.setModal(True)
        layout = QFormLayout(self)

        layout.addRow(QLabel(f"<b>{username}</b> için yeni şifre:"))

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Yeni şifre (en az 4 karakter)")
        layout.addRow("Yeni Şifre:", self.password_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Şifreyi tekrar girin")
        layout.addRow("Onayla:", self.confirm_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _validate(self):
        pwd = self.password_input.text()
        confirm = self.confirm_input.text()
        if len(pwd) < 4:
            QMessageBox.warning(self, "Geçersiz", "Şifre en az 4 karakter olmalıdır.")
            return
        if pwd != confirm:
            QMessageBox.warning(self, "Uyuşmazlık", "Şifreler eşleşmiyor.")
            return
        self.password = pwd
        self.accept()

    def get_password(self):
        return self.password
