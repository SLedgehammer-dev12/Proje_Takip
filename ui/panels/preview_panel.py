from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from i18n import set_widget_text
from models import RevizyonModel


class PreviewPanel(QWidget):
    """
    Panel for previewing and displaying PDF documents.

    Provides a scrollable preview area and a button to open the document
    in full-screen mode.

    Signals:
        view_document_clicked: Emitted when the view document button is clicked
    """

    view_document_clicked = Signal(object)

    def __init__(self, parent=None):
        """Initialize the PreviewPanel."""
        super().__init__(parent)
        self.current_revision = None
        self.current_document_payload = None
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Başlık ve Buton
        self.onizleme_etiketi = QLabel("Bir revizyon seçerek dokümanı ön izleyin.")
        self.onizleme_etiketi.setAlignment(Qt.AlignCenter)
        self.onizleme_etiketi.setWordWrap(True)
        layout.addWidget(self.onizleme_etiketi)

        self.goruntule_btn = QPushButton("Tam Ekran Görüntüle")
        self.goruntule_btn.setEnabled(False)
        self.goruntule_btn.clicked.connect(self._on_view_clicked)
        layout.addWidget(self.goruntule_btn)

        # PDF Viewer (ScrollArea içinde Label)
        self.scroll_area = QScrollArea()
        self.pdf_label = QLabel()
        self.pdf_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.pdf_label)
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

    def show_preview(self, revision: RevizyonModel, pixmap: QPixmap = None):
        self.current_revision = revision
        self.current_document_payload = revision
        if pixmap:
            self.pdf_label.setPixmap(pixmap)
            set_widget_text(self.onizleme_etiketi, f"Önizleme: {revision.revizyon_kodu}")
        else:
            self.pdf_label.clear()
            set_widget_text(
                self.onizleme_etiketi,
                "Önizleme yükleniyor veya mevcut değil...",
            )

        self.goruntule_btn.setEnabled(True)

    def clear(self):
        self.current_revision = None
        self.current_document_payload = None
        self.pdf_label.clear()
        set_widget_text(self.onizleme_etiketi, "Bir revizyon seçerek dokümanı ön izleyin.")
        self.goruntule_btn.setEnabled(False)

    def _on_view_clicked(self):
        payload = self.current_document_payload or self.current_revision
        if payload:
            self.view_document_clicked.emit(payload)
