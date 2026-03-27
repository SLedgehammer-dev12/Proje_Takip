"""
Document service for preview/document payload building and opening flows.

This service keeps preview-related document lookup logic out of the main
window and delegates actual file opening to FileService.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import QMessageBox, QWidget

from models import RevizyonModel
from services.file_service import FileService


class DocumentService:
    """Handle document payload construction and DB-backed document opening."""

    def __init__(self, db, file_service: FileService, parent: Optional[QWidget] = None):
        self.db = db
        self.file_service = file_service
        self.parent = parent
        self.logger = logging.getLogger(__name__)

    def get_letter_lookup(
        self, rev: Optional[RevizyonModel], yazi_turu: str
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        if not rev:
            return None, None, None
        if yazi_turu == "gelen":
            return rev.gelen_yazi_no, rev.gelen_yazi_tarih, "gelen"
        if yazi_turu in {"onay", "notlu_onay"}:
            return rev.onay_yazi_no, rev.onay_yazi_tarih, "onay"
        if yazi_turu == "red":
            return rev.red_yazi_no, rev.red_yazi_tarih, "red"
        return None, None, yazi_turu

    def build_preview_letter_payload(
        self, rev: Optional[RevizyonModel], yazi_no: str
    ) -> Optional[dict]:
        if not rev or not yazi_no:
            return None

        if rev.gelen_yazi_no == yazi_no:
            return {
                "kind": "letter",
                "yazi_no": yazi_no,
                "yazi_turu": "gelen",
                "yazi_tarih": rev.gelen_yazi_tarih,
                "rev_id": rev.id,
            }
        if rev.onay_yazi_no == yazi_no:
            return {
                "kind": "letter",
                "yazi_no": yazi_no,
                "yazi_turu": "onay",
                "yazi_tarih": rev.onay_yazi_tarih,
                "rev_id": rev.id,
            }
        if rev.red_yazi_no == yazi_no:
            return {
                "kind": "letter",
                "yazi_no": yazi_no,
                "yazi_turu": "red",
                "yazi_tarih": rev.red_yazi_tarih,
                "rev_id": rev.id,
            }
        return None

    def build_letter_payload_from_revision(
        self,
        rev: Optional[RevizyonModel],
        yazi_turu: str,
        fallback_yazi_no: Optional[str] = None,
    ) -> Optional[dict]:
        lookup_no, lookup_tarih, lookup_turu = self.get_letter_lookup(rev, yazi_turu)
        resolved_yazi_no = lookup_no or fallback_yazi_no
        resolved_yazi_turu = lookup_turu or yazi_turu

        if not resolved_yazi_no or not resolved_yazi_turu:
            return None

        return {
            "kind": "letter",
            "yazi_no": resolved_yazi_no,
            "yazi_tarih": lookup_tarih,
            "yazi_turu": resolved_yazi_turu,
            "rev_id": getattr(rev, "id", None),
        }

    def open_revision_document(self, rev: Optional[RevizyonModel]) -> bool:
        """Open the revision document represented by the given model."""
        if not rev:
            QMessageBox.warning(self.parent, "Uyarı", "Açılacak revizyon bulunamadı.")
            return False

        document = self.db.dokumani_getir(rev.id)
        if not document:
            QMessageBox.warning(
                self.parent,
                "Uyarı",
                "Bu revizyona ait doküman bulunamadı.",
            )
            return False

        filename, file_data = document
        opened = self.file_service.open_temporary_document(
            filename,
            file_data,
            temp_prefix=f"rev_{rev.id}",
            error_title="Açma Hatası",
        )
        if opened:
            self.logger.info("Revizyon dokümanı açıldı: rev_id=%s", rev.id)
        return opened

    def open_letter_document(self, payload: Optional[dict]) -> bool:
        """Open the exact letter document represented by the preview payload."""
        if not payload or payload.get("kind") != "letter":
            QMessageBox.warning(
                self.parent,
                "Uyarı",
                "Açılacak yazı dokümanı bulunamadı.",
            )
            return False

        yazi_no = payload.get("yazi_no") or ""
        yazi_tarih = payload.get("yazi_tarih")
        yazi_turu = payload.get("yazi_turu") or ""

        if not yazi_no or not yazi_turu:
            QMessageBox.warning(
                self.parent,
                "Uyarı",
                "Yazı dokümanı bilgisi eksik.",
            )
            return False

        document = self.db.yazi_dokumani_getir(yazi_no, yazi_tarih, yazi_turu)
        if not document:
            QMessageBox.information(
                self.parent,
                "Yazı Bulunamadı",
                f"'{yazi_no}' numaralı yazı dokümanı bulunamadı.",
            )
            return False

        filename, file_data = document
        opened = self.file_service.open_temporary_document(
            filename,
            file_data,
            temp_prefix=f"yazi_{yazi_no}",
            error_title="Açma Hatası",
        )
        if opened:
            self.logger.info("Yazı dokümanı açıldı: %s (%s)", yazi_no, yazi_turu)
        return opened
