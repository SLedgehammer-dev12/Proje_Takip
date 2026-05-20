from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QComboBox,
    QTableWidget,
    QHeaderView,
)
from PySide6.QtCore import Signal


class ReportPanel(QWidget):
    report_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.rapor_turu_combo = QComboBox()
        self.rapor_turu_combo.addItems(
            ["Genel Durum Raporu", "Bekleyen İşler", "Onaylananlar"]
        )
        layout.addWidget(self.rapor_turu_combo)

        self.rapor_tablosu = QTableWidget()
        self.rapor_tablosu.setColumnCount(5)
        self.rapor_tablosu.setHorizontalHeaderLabels(
            ["Proje Kodu", "İsim", "Durum", "Son Revizyon", "Tarih"]
        )
        self.rapor_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.rapor_tablosu)

        self.rapor_al_btn = QPushButton("Rapor Oluştur (Excel)")
        self.rapor_al_btn.clicked.connect(self.report_requested.emit)
        layout.addWidget(self.rapor_al_btn)
