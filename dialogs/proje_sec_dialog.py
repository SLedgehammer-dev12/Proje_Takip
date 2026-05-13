"""
ProjeSecDialog — Canlı Arama Destekli Proje Seçme Diyaloğu
============================================================
Kullanıcıya veritabanındaki tüm projeleri canlı filtreli bir listede sunar.
Proje kodu veya ismi yazarak anında filtreleme yapılabilir.
"""

import re
from typing import Optional

from PySide6.QtCore import Qt, QSortFilterProxyModel, QTimer
from PySide6.QtGui import QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QVBoxLayout,
)


class ProjeSecDialog(QDialog):
    """
    Canlı arama çubuğu ile proje seçme diyaloğu.

    Kullanım::

        dialog = ProjeSecDialog(parent, db)
        if dialog.exec():
            secilen = dialog.selected_project()
            # secilen = {"id": int, "kod": str, "isim": str}
    """

    def __init__(self, parent, db, title: str = "Proje Seç", projeler_listesi: Optional[list] = None):
        super().__init__(parent)
        self.db = db
        self.projeler_listesi = projeler_listesi
        self._selected: Optional[dict] = None

        self.setWindowTitle(f"🔍 {title}")
        self.setMinimumSize(600, 450)
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Başlık
        header = QLabel(f"<b>{title}</b> — Aramak için yazmaya başlayın")
        header.setFont(QFont("Segoe UI", 10))
        layout.addWidget(header)

        # Arama çubuğu
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Proje kodu veya ismi ile ara...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFont(QFont("Segoe UI", 10))
        self.search_input.setStyleSheet(
            "QLineEdit { padding: 6px; border: 2px solid #60a5fa; border-radius: 6px; }"
        )
        layout.addWidget(self.search_input)

        # Proje listesi
        self._model = QStandardItemModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterRole(Qt.UserRole + 1)  # search_text role

        self.list_view = QListView()
        self.list_view.setModel(self._proxy)
        self.list_view.setFont(QFont("Segoe UI", 9))
        self.list_view.setAlternatingRowColors(True)
        self.list_view.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_view, 1)

        # Bilgi satırı
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(self._info_label)

        # Butonlar
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("✅ Seç")
        btn_box.button(QDialogButtonBox.Cancel).setText("İptal")
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # Debounce timer
        self._filter_timer = QTimer()
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(200)
        self._filter_timer.timeout.connect(self._apply_filter)
        self.search_input.textChanged.connect(lambda: self._filter_timer.start())

        # Verileri yükle
        self._load_projects()
        self.search_input.setFocus()

    def _load_projects(self):
        """Projeleri modele yükle."""
        if self.projeler_listesi is not None:
            projeler = self.projeler_listesi
        else:
            try:
                projeler = list(self.db.projeleri_listele())
            except Exception:
                projeler = []

        self._model.clear()
        for p in projeler:
            if isinstance(p, dict):
                kod = p.get("kod") or p.get("proje_kodu") or ""
                isim = p.get("isim") or p.get("proje_ismi") or ""
                pid = p.get("id")
            else:
                kod = getattr(p, "proje_kodu", "") or ""
                isim = getattr(p, "proje_ismi", "") or ""
                pid = getattr(p, "id", None)

            item = QStandardItem(f"{kod}  —  {isim}")
            item.setData({"id": pid, "kod": kod, "isim": isim}, Qt.UserRole)
            # Arama için birleşik metin
            search_text = f"{kod} {isim}".lower()
            item.setData(search_text, Qt.UserRole + 1)
            item.setEditable(False)
            self._model.appendRow(item)

        self._info_label.setText(f"{len(projeler)} proje yüklendi")

    def _apply_filter(self):
        """Arama çubuğundaki metne göre listeyi filtrele."""
        text = self.search_input.text().strip().lower()
        if not text:
            self._proxy.setFilterFixedString("")
        else:
            # Her kelimeyi içeren satırları göster
            words = text.split()
            pattern = ".*".join(re.escape(w) for w in words)
            self._proxy.setFilterRegularExpression(pattern)

        visible = self._proxy.rowCount()
        self._info_label.setText(f"{visible} / {self._model.rowCount()} proje gösteriliyor")

    def _on_double_click(self, index):
        data = index.data(Qt.UserRole)
        if data:
            self._selected = data
            self.accept()

    def _on_accept(self):
        indexes = self.list_view.selectionModel().selectedIndexes()
        if indexes:
            data = indexes[0].data(Qt.UserRole)
            if data:
                self._selected = data
                self.accept()
                return
        # Seçim yoksa uyarı
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Uyarı", "Lütfen listeden bir proje seçin.")

    def selected_project(self) -> Optional[dict]:
        """Seçilen projeyi döndür: {"id": int, "kod": str, "isim": str}"""
        return self._selected
