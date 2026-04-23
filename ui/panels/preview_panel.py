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
        layout.setSpacing(4)

        self.baslik_etiketi = QLabel("<b>🔍 Doküman Ön İzleme</b>")
        self.baslik_etiketi.setStyleSheet("font-size: 11pt; color: #212529;")
        layout.addWidget(self.baslik_etiketi)

        # Durum metni
        self.onizleme_etiketi = QLabel("Bir revizyon seçerek dokümanı ön izleyin.")
        self.onizleme_etiketi.setAlignment(Qt.AlignCenter)
        self.onizleme_etiketi.setWordWrap(True)
        self.onizleme_etiketi.setStyleSheet("color: #777; font-size: 10pt;")
        layout.addWidget(self.onizleme_etiketi)

        # PDF Viewer (ScrollArea içinde Label)
        self.scroll_area = QScrollArea()
        self.pdf_label = QLabel()
        self.pdf_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.pdf_label)
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

        self.goruntule_btn = QPushButton("📄 Dokümanı Tam Ekran Aç")
        self.goruntule_btn.setEnabled(False)
        self.goruntule_btn.setFixedHeight(30)
        self.goruntule_btn.setCursor(Qt.PointingHandCursor)
        self.goruntule_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff;
                color: #2f3542;
                border: 1px solid #d9dee7;
                border-radius: 8px;
                padding: 4px 10px;
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
        self.goruntule_btn.clicked.connect(self._on_view_clicked)
        layout.addWidget(self.goruntule_btn)

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
