import copy

# GEREKLİ İÇE AKTARMALAR EKLENDİ
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QWidget,
    QPushButton,
    QLabel,
    QScrollArea,
    QHBoxLayout,
    QDateEdit,
    QLineEdit,
    QListWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt, QDate
from filters import FilterType
from project_types import normalize_project_type

# EKLENEN KISIM BİTTİ


class AdvancedFilterDialog(QDialog):
    def __init__(self, parent, filter_manager):
        super().__init__(parent)
        self.filter_manager = filter_manager
        self._initial_filters = copy.deepcopy(filter_manager.active_filters)
        self.setWindowTitle("Gelişmiş Filtreleme")
        self.setMinimumSize(600, 500)

        # Dinamik filtre seceneklerini tazele (yazi yili vb.)
        if hasattr(self.filter_manager, '_populate_dynamic_options'):
            self.filter_manager._populate_dynamic_options()

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Filtre ekleme bölümü
        filter_group = QGroupBox("Yeni Filtre Ekle")
        self.filter_layout = QFormLayout(filter_group)

        self.field_combo = QComboBox()
        self.field_combo.addItems(
            [
                config["label"]
                for config in self.filter_manager.available_filters.values()
            ]
        )
        self.field_combo.currentTextChanged.connect(self.on_field_changed)

        self.operator_combo = QComboBox()

        # --- EN ÖNEMLİ DEĞİŞİKLİK BURADA ---
        # self.value_widget artık kalıcı bir konteyner olacak
        self.value_widget = QWidget()
        # Ve bu konteynerin kendi içinde kalıcı bir layout'u olacak
        self.value_layout = QHBoxLayout(self.value_widget)
        self.value_layout.setContentsMargins(0, 0, 0, 0)
        # --- DEĞİŞİKLİK BİTTİ ---

        self.filter_layout.addRow("Filtre Alanı:", self.field_combo)
        self.filter_layout.addRow("Operatör:", self.operator_combo)
        self.filter_layout.addRow(
            "Değer:", self.value_widget
        )  # Kalıcı konteyner buraya eklendi

        self.add_filter_btn = QPushButton("Filtre Ekle")
        self.add_filter_btn.clicked.connect(self.add_filter)
        self.filter_layout.addRow(self.add_filter_btn)

        layout.addWidget(filter_group)

        # Aktif filtreler
        layout.addWidget(
            QLabel(
                "<b>Aktif Filtreler (Silmek için yanındaki X butonuna tıklayın):</b>"
            )
        )

        self.filters_container = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_container)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.filters_container)
        layout.addWidget(scroll)

        # Butonlar
        button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Filtreleri Uygula")
        self.clear_btn = QPushButton("Tümünü Temizle")
        self.close_btn = QPushButton("Kapat")

        self.apply_btn.clicked.connect(self.accept)
        self.clear_btn.clicked.connect(self.clear_filters)
        self.close_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        self.on_field_changed(self.field_combo.currentText())
        self.update_filters_display()

    def on_field_changed(self, field_label):
        field_name = self.get_field_name_from_label(field_label)
        filter_config = self.filter_manager.available_filters.get(field_name)

        if not filter_config:
            return

        # Operatörleri güncelle
        self.operator_combo.clear()
        self.operator_combo.addItems(filter_config["operators"])

        # Değer widget'ını güncelle
        self.update_value_widget(filter_config, field_name)

    def update_value_widget(self, filter_config, field_name: str = None):
        # --- YENİ GÜVENLİ GÜNCELLEME YÖNTEMİ ---

        # 1. Kalıcı olan self.value_layout'un İÇİNDEKİLERİ temizle
        # (Layout'un kendisini silme!)
        while self.value_layout.count():
            item = self.value_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # 2. Filtre tipine göre yeni "Değer" bileşenini oluştur

        if filter_config["type"] == FilterType.TEXT:
            self.value_input = QLineEdit()
            self.value_input.returnPressed.connect(self.add_filter)
            self.value_layout.addWidget(self.value_input)  # Kalıcı layout'a ekle
            # If the field is one of the yazı number fields, add a checkbox to search across all revisions
            if field_name in ("gelen_yazi_no", "onay_yazi_no", "red_yazi_no", "giden_yazi_no"):
                from PySide6.QtWidgets import QCheckBox

                self._all_revisions_checkbox = QCheckBox("Tüm revizyonlarda ara")
                self._all_revisions_checkbox.setToolTip(
                    "Seçiliyse projeye ait tüm revizyonlardaki yazı numaraları aranır; seçili değilse yalnızca son revizyona bakılır."
                )
                self.value_layout.addWidget(self._all_revisions_checkbox)

        elif filter_config["type"] == FilterType.MULTI_SELECT:
            self.value_input = QListWidget()
            self.value_input.setSelectionMode(QListWidget.MultiSelection)
            self.value_input.addItems(self._get_multi_select_options(filter_config, field_name))
            self.value_input.setMaximumHeight(120)
            self.value_layout.addWidget(self.value_input)  # Kalıcı layout'a ekle

        elif filter_config["type"] == FilterType.BOOLEAN:
            self.value_input = QComboBox()
            self.value_input.addItems(filter_config["options"])
            self.value_layout.addWidget(self.value_input)  # Kalıcı layout'a ekle

        elif filter_config["type"] == FilterType.DATE_RANGE:
            # Tarih için birden fazla bileşen olduğundan bir konteyner kullan
            date_widget = QWidget()
            date_layout = QVBoxLayout(date_widget)  # Layout'u date_widget'in içine koy

            start_layout = QHBoxLayout()
            self.start_date = QDateEdit()
            self.start_date.setCalendarPopup(True)
            self.start_date.setDate(QDate.currentDate().addDays(-30))
            start_layout.addWidget(QLabel("Başlangıç:"))
            start_layout.addWidget(self.start_date)

            end_layout = QHBoxLayout()
            self.end_date = QDateEdit()
            self.end_date.setCalendarPopup(True)
            self.end_date.setDate(QDate.currentDate())
            end_layout.addWidget(QLabel("Bitiş:"))
            end_layout.addWidget(self.end_date)

            date_layout.addLayout(start_layout)
            date_layout.addLayout(end_layout)

            self.value_input = date_widget  # value_input referansı konteyner
            self.value_layout.addWidget(
                self.value_input
            )  # Konteyneri kalıcı layout'a ekle

        # 3. Form dizilimini (QFormLayout) hiç ellemedik.
        # Sadece kalıcı konteynerin içini değiştirdik.
        # --- GÜNCELLEME BİTTİ ---

    def _get_multi_select_options(self, filter_config, field_name: str = None):
        options = list(filter_config.get("options", []))
        if field_name != "proje_turu":
            return options

        sanitized = []
        seen = set()
        for option in options:
            if option == "Belirtilmemiş":
                display_value = option
            else:
                display_value = normalize_project_type(option) or option
            if display_value not in seen:
                sanitized.append(display_value)
                seen.add(display_value)
        return sanitized

    def get_field_name_from_label(self, label):
        for field_name, config in self.filter_manager.available_filters.items():
            if config["label"] == label:
                return field_name
        return None

    def get_current_value(self):
        field_label = self.field_combo.currentText()
        field_name = self.get_field_name_from_label(field_label)
        filter_config = self.filter_manager.available_filters.get(field_name)

        if not filter_config:
            return None

        if filter_config["type"] == FilterType.TEXT:
            value = self.value_input.text().strip()
            if value:
                if hasattr(self, "_all_revisions_checkbox") and self._all_revisions_checkbox is not None:
                    return {"value": value, "all_revisions": bool(self._all_revisions_checkbox.isChecked())}
                return value
            return None
        elif filter_config["type"] == FilterType.MULTI_SELECT:
            selected_items = [item.text() for item in self.value_input.selectedItems()]
            return selected_items if selected_items else None
        elif filter_config["type"] == FilterType.BOOLEAN:
            return self.value_input.currentText()
        elif filter_config["type"] == FilterType.DATE_RANGE:
            return {
                "start": self.start_date.date().toString("yyyy-MM-dd"),
                "end": self.end_date.date().toString("yyyy-MM-dd"),
            }
        return None

    def add_filter(self):
        field_label = self.field_combo.currentText()
        field_name = self.get_field_name_from_label(field_label)
        operator = self.operator_combo.currentText()
        value = self.get_current_value()

        if value:
            success = self.filter_manager.add_filter(field_name, operator, value)
            if success:
                self.update_filters_display()
                # Formu temizle
                if hasattr(self, "value_input"):
                    if isinstance(self.value_input, QLineEdit):
                        self.value_input.clear()
                    elif isinstance(self.value_input, QListWidget):
                        self.value_input.clearSelection()
            else:
                QMessageBox.warning(self, "Hata", "Filtre eklenemedi!")
        else:
            QMessageBox.warning(self, "Uyarı", "Lütfen geçerli bir değer girin!")

    def update_filters_display(self):
        """Aktif filtreleri görüntüle"""
        # Eski widget'ları temizle
        for i in reversed(range(self.filters_layout.count())):
            widget = self.filters_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        if not self.filter_manager.active_filters:
            # Liste boşsa mesaj göster
            empty_label = QLabel("Henüz filtre eklenmedi")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
            self.filters_layout.addWidget(empty_label)
        else:
            # Yeni filtreleri ekle
            for i, condition in enumerate(self.filter_manager.active_filters):
                widget = self.create_filter_item(condition, i)
                self.filters_layout.addWidget(widget)

        # Boşluk ekle
        self.filters_layout.addStretch()

    def create_filter_item(self, condition, index):
        """Tek bir filtre için widget oluştur"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)

        # Sil butonu - KIRMIZI ve GÖRÜNÜR
        delete_btn = QPushButton("X")
        delete_btn.setFixedSize(30, 30)
        delete_btn.setToolTip("Bu filtreyi sil")
        delete_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
            QPushButton:pressed {
                background-color: #990000;
            }
        """
        )
        delete_btn.clicked.connect(lambda checked, idx=index: self.delete_filter(idx))

        # Filtre bilgisi
        filter_config = self.filter_manager.available_filters[condition.field]
        # condition.value may be a primitive or list
        value_text = (
            str(condition.value) if not isinstance(condition.value, list) else ", ".join(condition.value)
        )
        # If this FilterCondition has the all_revisions flag, append label
        extra_text = ""
        try:
            if getattr(condition, "all_revisions", False):
                extra_text = " (Tüm revizyonlarda ara)"
        except Exception:
            extra_text = ""
        filter_text = f"{filter_config['label']} {condition.operator} {value_text}{extra_text}"

        label = QLabel(filter_text)
        label.setStyleSheet(
            """
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 6px;
                margin: 2px;
            }
        """
        )
        label.setWordWrap(True)

        layout.addWidget(delete_btn)
        layout.addWidget(label, 1)  # 1 = stretch factor

        return widget

    def delete_filter(self, index):
        """Tek bir filtreyi sil"""
        if 0 <= index < len(self.filter_manager.active_filters):
            # Filtreyi sil
            deleted_filter = self.filter_manager.active_filters[index]
            self.filter_manager.remove_filter(index)
            # Görünümü güncelle
            self.update_filters_display()

            # Kullanıcıya bilgi ver (opsiyonel)
            filter_config = self.filter_manager.available_filters[deleted_filter.field]
            QMessageBox.information(
                self, "Bilgi", f"'{filter_config['label']}' filtresi silindi."
            )

    def clear_filters(self):
        """Tüm filtreleri temizle"""
        if self.filter_manager.active_filters:
            self.filter_manager.clear_filters()
            self.update_filters_display()
            QMessageBox.information(self, "Bilgi", "Tüm filtreler temizlendi.")

    def accept(self):
        self._initial_filters = copy.deepcopy(self.filter_manager.active_filters)
        super().accept()

    def reject(self):
        self.filter_manager.active_filters = copy.deepcopy(self._initial_filters)
        super().reject()
