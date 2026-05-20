from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)
from PySide6.QtCore import Qt
from typing import List, Optional
from models import RevizyonModel


class RedFlagPanel(QWidget):
    """Red flag işaretli tüm revizyonları listeleyen dashboard paneli."""

    def __init__(self, parent=None, db=None, window=None):
        super().__init__(parent)
        self._db = db
        self._window = window
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header_layout = QHBoxLayout()
        title = QLabel("<b>🚩 Red Flag Listesi</b>")
        title.setStyleSheet("font-size: 13pt;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.yenile_btn = QPushButton("🔄 Yenile")
        self.yenile_btn.clicked.connect(self.refresh)
        header_layout.addWidget(self.yenile_btn)

        layout.addLayout(header_layout)

        info = QLabel(
            "Aşağıda tüm projelerde red flag işaretli revizyonlar listelenmektedir. "
            "Her revizyon için işaret sebebini görebilir ve işareti kaldırabilirsiniz."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 9pt; margin-bottom: 4px;")
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Proje Kodu", "Proje İsmi", "Revizyon", "Durum",
            "İşaretleyen", "Tarih", "Sebep", "İşlem"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def bind(self, db, window):
        self._db = db
        self._window = window

    def refresh(self):
        if not self._db:
            return
        self.table.setRowCount(0)
        try:
            cursor = self._db.cursor
            cursor.execute("""
                SELECT p.proje_kodu, p.proje_ismi,
                       r.revizyon_kodu, r.durum,
                       r.flag_user, r.flag_date, r.flag_reason,
                       r.id as revizyon_id, p.id as proje_id
                FROM revizyonlar r
                JOIN projeler p ON p.id = r.proje_id
                WHERE r.is_flagged = 1
                ORDER BY r.flag_date DESC, p.proje_kodu
            """)
            rows = cursor.fetchall()
            for row_data in rows:
                row = self.table.rowCount()
                self.table.insertRow(row)
                proje_kodu, proje_ismi, rev_kodu, durum = row_data[:4]
                flag_user, flag_date, flag_reason = row_data[4:7]
                revizyon_id, proje_id = row_data[7:9]

                self.table.setItem(row, 0, QTableWidgetItem(str(proje_kodu or "")))
                self.table.setItem(row, 1, QTableWidgetItem(str(proje_ismi or "")))
                self.table.setItem(row, 2, QTableWidgetItem(str(rev_kodu or "")))
                self.table.setItem(row, 3, QTableWidgetItem(str(durum or "")))
                self.table.setItem(row, 4, QTableWidgetItem(str(flag_user or "")))
                self.table.setItem(row, 5, QTableWidgetItem(str(flag_date or "")))
                self.table.setItem(row, 6, QTableWidgetItem(str(flag_reason or "")))

                remove_btn = QPushButton("🚫 İşareti Kaldır")
                remove_btn.setStyleSheet(
                    "QPushButton { background-color: #dc3545; color: white; "
                    "border: none; border-radius: 4px; padding: 4px 10px; }"
                    "QPushButton:hover { background-color: #c82333; }"
                )
                remove_btn.clicked.connect(
                    lambda checked, rid=revizyon_id, pid=proje_id: self._remove_flag(rid, pid)
                )
                self.table.setCellWidget(row, 7, remove_btn)

            if not rows:
                self.table.setRowCount(1)
                msg = QTableWidgetItem("Red flag işaretli kayıt bulunmamaktadır.")
                msg.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(0, 0, msg)
                self.table.setSpan(0, 0, 1, 8)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"RedFlagPanel refresh hatası: {e}")

    def _remove_flag(self, revizyon_id: int, proje_id: int):
        if not self._db or not self._window:
            return
        reply = QMessageBox.question(
            self, "İşareti Kaldır",
            "Bu revizyonun red flag işaretini kaldırmak istediğinize emin misiniz?\n\n"
            "İşaret kaldırıldığında proje listesinde 🚩 işareti görünmez olacaktır.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success = self._db.revizyon_flag_durumu_guncelle(revizyon_id, False)
            if success:
                self.refresh()
                if self._window:
                    self._window._invalidate_filter_cache_and_reload(
                        keep_project_id=proje_id, force_sync=True
                    )
