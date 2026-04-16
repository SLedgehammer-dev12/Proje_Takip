from typing import Optional

from PySide6.QtGui import QPixmap

from models import RevizyonModel


class PreviewStateHelper:
    """Keep preview panel and legacy preview widgets in sync."""

    DEFAULT_TEXT = "Bir revizyon seçerek dokümanı ön izleyin."

    def __init__(self, window):
        self.window = window

    def _panel(self):
        panel = getattr(self.window, "preview_panel", None)
        return panel if panel is not None else None

    def _legacy_label(self):
        return getattr(self.window, "onizleme_etiketi", None)

    def _legacy_button(self):
        return getattr(self.window, "goruntule_btn", None)

    def clear(self):
        panel = self._panel()
        if panel is not None:
            panel.clear()
            return

        label = self._legacy_label()
        button = self._legacy_button()
        if label is not None:
            label.clear()
            label.setText(self.DEFAULT_TEXT)
        if button is not None:
            button.setEnabled(False)

    def show_status(
        self,
        text: str,
        *,
        enable_open: bool = False,
        revision: Optional[RevizyonModel] = None,
        payload=None,
        clear_visual: bool = False,
    ):
        panel = self._panel()
        if panel is not None:
            if clear_visual:
                panel.pdf_label.clear()
            panel.current_revision = revision
            panel.current_document_payload = payload if payload is not None else revision
            panel.onizleme_etiketi.setText(text)
            panel.goruntule_btn.setEnabled(enable_open)
            return

        label = self._legacy_label()
        button = self._legacy_button()
        if label is not None:
            if clear_visual:
                label.clear()
            label.setText(text)
        if button is not None:
            button.setEnabled(enable_open)

    def show_loading(self, revision: Optional[RevizyonModel]):
        self.show_status(
            "Ön izleme yükleniyor...",
            enable_open=False,
            revision=revision,
            payload=revision,
            clear_visual=False,
        )

    def show_revision_preview(self, revision: RevizyonModel, pixmap: QPixmap):
        panel = self._panel()
        if panel is not None:
            panel.current_revision = revision
            panel.current_document_payload = revision
            panel.pdf_label.setPixmap(pixmap)
            panel.onizleme_etiketi.setText(f"Önizleme: {revision.revizyon_kodu}")
            panel.goruntule_btn.setEnabled(True)
            return

        label = self._legacy_label()
        button = self._legacy_button()
        if label is not None:
            label.setPixmap(pixmap)
        if button is not None:
            button.setEnabled(True)

    def show_letter_preview(self, yazi_no: str, pixmap: QPixmap, payload):
        panel = self._panel()
        enable_open = bool(payload)
        if panel is not None:
            panel.current_revision = None
            panel.current_document_payload = payload
            panel.pdf_label.setPixmap(pixmap)
            panel.onizleme_etiketi.setText(f"Yazı Önizleme: {yazi_no}")
            panel.goruntule_btn.setEnabled(enable_open)
            return

        label = self._legacy_label()
        button = self._legacy_button()
        if label is not None:
            label.setPixmap(pixmap)
        if button is not None:
            button.setEnabled(enable_open)

    def show_render_error(self, error_msg: str):
        panel = self._panel()
        if panel is not None:
            panel.pdf_label.clear()
            panel.onizleme_etiketi.setText(f"Önizleme oluşturulamadı.\n{error_msg}")
            panel.goruntule_btn.setEnabled(False)
            return

        label = self._legacy_label()
        button = self._legacy_button()
        if label is not None:
            label.clear()
            label.setText(f"Önizleme oluşturulamadı.\n{error_msg}")
        if button is not None:
            button.setEnabled(False)
