from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from typing import List
from models import RevizyonModel, Durum


class RevisionPanel(QWidget):
    """
    Panel for displaying project revisions in a tree view.

    Shows revision code, status, description, letter type, and document info
    with status-based color coding.

    Signals:
        revision_selected: Emitted when a revision is selected (RevizyonModel or None)
        letter_clicked: Emitted when a letter number is double-clicked (yazi_no: str, yazi_turu: str)
        revision_double_clicked: Emitted when a revision row is double-clicked (non-letter column)
        view_letter_requested: Emitted when "Yazıyı Görüntüle" button clicked (RevizyonModel)
    """

    revision_selected = Signal(object)       # Emits RevizyonModel or None
    letter_clicked = Signal(str, str)        # Emits (yazi_no, yazi_turu)
    revision_double_clicked = Signal(object) # Emits RevizyonModel
    view_letter_requested = Signal(object)   # Emits RevizyonModel

    def __init__(self, parent=None):
        """Initialize the RevisionPanel."""
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Quick action button row
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(6)

        self.view_letter_btn = QPushButton("📄 Yazıyı Görüntüle")
        self.view_letter_btn.setToolTip(
            "Seçili revizyona ait gelen/onay/red yazısını tam ekranda aç"
        )
        self.view_letter_btn.setEnabled(False)
        self.view_letter_btn.setFixedHeight(28)
        self.view_letter_btn.setCursor(Qt.PointingHandCursor)
        self.view_letter_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff;
                color: #2f3542;
                border: 1px solid #d9dee7;
                border-radius: 7px;
                padding: 3px 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #eaf4ff;
                border-color: #6baed6;
            }
            QPushButton:pressed {
                background-color: #d0e8fb;
            }
            QPushButton:disabled {
                background-color: #f4f6f9;
                color: #9aa3b2;
                border-color: #e6e9ef;
            }
            """
        )
        self.view_letter_btn.clicked.connect(self._on_view_letter_clicked)
        btn_row.addWidget(self.view_letter_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.revizyon_agaci = QTreeWidget()
        self.revizyon_agaci.setHeaderLabels(
            [
                "Revizyon",
                "Durum",
                "Açıklama",
                "Yazı Türü",
                "Yazı No",
                "Yazı Tarihi",
                "Doküman",
                "Yazı Dok.",
                "Uyarı",
                "Takip",
            ]
        )
        self.revizyon_agaci.itemSelectionChanged.connect(self._on_selection_changed)
        self.revizyon_agaci.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.revizyon_agaci)

    def load_revisions(self, revisions: List[RevizyonModel]):
        tree = self.revizyon_agaci
        tree.setSortingEnabled(False)
        tree.setUpdatesEnabled(False)
        
        # Enforce sorting: Newest -> Oldest (RevNo DESC, ID DESC)
        # Ensure types are int for correct comparison
        revisions.sort(key=lambda r: (int(r.proje_rev_no) if r.proje_rev_no is not None else -1, int(r.id)), reverse=True)
        
        try:
            tree.clear()
            for rev in revisions:
                yazi_no = "-"
                yazi_tarih = "-"

                if rev.yazi_turu == "gelen":
                    yazi_no = rev.gelen_yazi_no or "-"
                    yazi_tarih = rev.gelen_yazi_tarih or "-"
                elif rev.yazi_turu == "giden":
                    if rev.onay_yazi_no:
                        yazi_no = rev.onay_yazi_no
                        yazi_tarih = rev.onay_yazi_tarih or "-"
                    elif rev.red_yazi_no:
                        yazi_no = rev.red_yazi_no
                        yazi_tarih = rev.red_yazi_tarih or "-"

                yazi_turu_display = {
                    "gelen": "📥 Gelen Yazı",
                    "giden": "📤 Giden Yazı",
                    "yok": "-"
                }.get(rev.yazi_turu, "-")

                item = QTreeWidgetItem(tree)
                item.setText(0, rev.revizyon_kodu)
                item.setText(1, rev.durum)
                item.setText(2, rev.aciklama or "")
                item.setText(3, yazi_turu_display)
                item.setText(4, yazi_no)
                item.setText(5, str(yazi_tarih))

                filename_display = getattr(rev, "dosya_adi", None) or rev.dokuman_durumu
                item.setText(6, filename_display)
                yazi_dokuman_durumu = getattr(rev, "yazi_dokuman_durumu", None) or "-"
                item.setText(7, yazi_dokuman_durumu)
                supheli = int(getattr(rev, "supheli_yazi_dokumani", 0) or 0)
                item.setText(8, "Aynı Dosya" if supheli else "-")
                takipte_mi = int(getattr(rev, "takipte_mi", 0) or 0)
                item.setText(9, "Takipte" if takipte_mi else "-")
                takip_notu = getattr(rev, "takip_notu", None)
                if takip_notu:
                    item.setToolTip(9, takip_notu)

                if rev.durum == Durum.ONAYLI.value:
                    item.setForeground(1, QBrush(QColor("green")))
                elif rev.durum == Durum.REDDEDILDI.value:
                    item.setForeground(1, QBrush(QColor("red")))
                elif rev.durum == Durum.ONAYLI_NOTLU.value:
                    item.setForeground(1, QBrush(QColor("orange")))
                if yazi_dokuman_durumu == "Eksik":
                    item.setForeground(7, QBrush(QColor("red")))
                elif yazi_dokuman_durumu == "Yüklü":
                    item.setForeground(7, QBrush(QColor("green")))
                if supheli:
                    item.setForeground(8, QBrush(QColor("darkorange")))
                if takipte_mi:
                    item.setForeground(9, QBrush(QColor("blue")))
                    takip_fill = QBrush(QColor("#ffe7db"))
                    for col in range(10):
                        item.setBackground(col, takip_fill)

                item.setData(0, Qt.UserRole, rev)
                item.setData(4, Qt.UserRole, rev.yazi_turu)

            if not getattr(self, "_columns_sized_once", False):
                for i in range(10):
                    tree.resizeColumnToContents(i)
                self._columns_sized_once = True
        finally:
            tree.setUpdatesEnabled(True)

    def _on_selection_changed(self):
        items = self.revizyon_agaci.selectedItems()
        if items:
            rev = items[0].data(0, Qt.UserRole)
            self.revision_selected.emit(rev)
            # Enable/disable "Yazıyı Görüntüle" based on whether yazi_turu has a letter
            has_letter = bool(rev and getattr(rev, "yazi_turu", None) in ("gelen", "giden"))
            self.view_letter_btn.setEnabled(has_letter)
        else:
            self.revision_selected.emit(None)
            self.view_letter_btn.setEnabled(False)

    def _on_item_double_clicked(self, item, column):
        """Handle double-click on tree items."""
        # Column 4 is "Yazı No"
        if column == 4:
            yazi_no = item.text(4)
            yazi_turu = item.data(4, Qt.UserRole)
            
            # Only emit if there's a valid letter number
            if yazi_no and yazi_no != "-":
                self.letter_clicked.emit(yazi_no, yazi_turu)
        else:
            # For all other columns, emit revision_double_clicked to open the main revision document
            rev = item.data(0, Qt.UserRole)
            if rev:
                self.revision_double_clicked.emit(rev)

    def _on_view_letter_clicked(self):
        """Handle 'Yazıyı Görüntüle' button click."""
        items = self.revizyon_agaci.selectedItems()
        if items:
            rev = items[0].data(0, Qt.UserRole)
            if rev:
                self.view_letter_requested.emit(rev)
