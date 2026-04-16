from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QComboBox,
    QTableWidget,
    QHeaderView,
)


class ReportPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Rapor Seçimi
        self.rapor_turu_combo = QComboBox()
        self.rapor_turu_combo.addItems(
            ["Genel Durum Raporu", "Bekleyen İşler", "Onaylananlar"]
        )
        layout.addWidget(self.rapor_turu_combo)

        # Tablo
        self.rapor_tablosu = QTableWidget()
        self.rapor_tablosu.setColumnCount(5)
        self.rapor_tablosu.setHorizontalHeaderLabels(
            ["Proje Kodu", "İsim", "Durum", "Son Revizyon", "Tarih"]
        )
        self.rapor_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.rapor_tablosu)

        # Butonlar
        self.rapor_al_btn = QPushButton("Rapor Oluştur (Excel)")
        layout.addWidget(self.rapor_al_btn)
