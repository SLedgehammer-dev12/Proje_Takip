"""
Document service for preview/document payload building and opening flows.

This service keeps preview-related document lookup logic out of the main
window and delegates actual file opening to FileService.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import QMessageBox, QWidget

from i18n import tr
from letter_resolution import (
    normalize_revision_letter_type,
    resolve_revision_letter_candidate,
)
from models import RevizyonModel
from services.file_service import FileService
from utils import get_class_logger


class DocumentService:
    """Handle document payload construction and DB-backed document opening."""

    def __init__(self, db, file_service: FileService, parent: Optional[QWidget] = None):
        self.db = db
        self.file_service = file_service
        self.parent = parent
        self.logger = get_class_logger(self)

    def get_letter_lookup(
        self, rev: Optional[RevizyonModel], yazi_turu: str
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        candidate = resolve_revision_letter_candidate(rev, preferred_type=yazi_turu)
        if not candidate:
            return None, None, normalize_revision_letter_type(yazi_turu)
        return candidate.yazi_no, candidate.yazi_tarih, candidate.logical_type

    def _lookup_types_for_logical_type(self, logical_type: Optional[str]) -> list[str]:
        normalized_type = normalize_revision_letter_type(logical_type)
        if normalized_type == "gelen":
            return ["gelen"]
        if normalized_type == "onay":
            return ["onay", "giden"]
        if normalized_type == "red":
            return ["red", "giden"]
        if normalized_type == "giden":
            return ["giden"]
        return [normalized_type] if normalized_type else []

    def _build_letter_payload(
        self,
        *,
        rev: Optional[RevizyonModel],
        yazi_no: str,
        yazi_tarih: Optional[str],
        logical_type: str,
        lookup_type: Optional[str] = None,
        document_exists: bool = False,
        source_field: Optional[str] = None,
        resolution_note: Optional[str] = None,
    ) -> dict:
        resolved_lookup = lookup_type or logical_type
        return {
            "kind": "letter",
            "yazi_no": yazi_no,
            "yazi_tarih": yazi_tarih,
            "yazi_turu": resolved_lookup,
            "logical_yazi_turu": logical_type,
            "lookup_yazi_turu": resolved_lookup,
            "broad_yazi_turu": "gelen" if logical_type == "gelen" else "giden",
            "document_exists": document_exists,
            "source_field": source_field,
            "resolution_note": resolution_note,
            "rev_id": getattr(rev, "id", None),
        }

    def _find_letter_document(
        self, yazi_no: str, yazi_tarih: Optional[str], logical_type: Optional[str], preferred_lookup: Optional[str] = None
    ):
        tried: list[str] = []
        lookup_types = []
        if preferred_lookup:
            lookup_types.append(preferred_lookup)
        lookup_types.extend(self._lookup_types_for_logical_type(logical_type))

        for lookup_type in lookup_types:
            normalized = normalize_revision_letter_type(lookup_type)
            if not normalized or normalized in tried:
                continue
            tried.append(normalized)
            document = self.db.yazi_dokumani_getir(yazi_no, yazi_tarih, normalized)
            if document:
                return document, normalized
        # Son çare: yazı türünü göz ardı ederek sadece numaraya göre ara
        try:
            document = self.db.yazi_dokumani_getir(yazi_no, yazi_tarih, None)
            if document:
                return document, "any"
        except Exception:
            pass
        return None, tried

    def resolve_letter_payload(
        self,
        rev: Optional[RevizyonModel],
        *,
        preferred_type: Optional[str] = None,
        preferred_yazi_no: Optional[str] = None,
        fallback_yazi_no: Optional[str] = None,
    ) -> Optional[dict]:
        candidate = resolve_revision_letter_candidate(
            rev,
            preferred_type=preferred_type,
            preferred_yazi_no=preferred_yazi_no,
        )
        if candidate:
            document, resolved_lookup = self._find_letter_document(
                candidate.yazi_no,
                candidate.yazi_tarih,
                candidate.logical_type,
            )
            resolution_note = None
            if resolved_lookup and resolved_lookup != candidate.logical_type:
                resolution_note = (
                    tr(
                        "Yazı türü '{logical_type}' yerine '{resolved_lookup}' fallback'i ile çözüldü."
                    ).format(
                        logical_type=candidate.logical_type,
                        resolved_lookup=resolved_lookup,
                    )
                )
                self.logger.warning(
                    "Yazı fallback ile çözüldü: rev_id=%s, yazi_no=%s, logical=%s, lookup=%s",
                    getattr(rev, "id", None),
                    candidate.yazi_no,
                    candidate.logical_type,
                    resolved_lookup,
                )
            return self._build_letter_payload(
                rev=rev,
                yazi_no=candidate.yazi_no,
                yazi_tarih=candidate.yazi_tarih,
                logical_type=candidate.logical_type,
                lookup_type=resolved_lookup or candidate.logical_type,
                document_exists=document is not None,
                source_field=candidate.source_field,
                resolution_note=resolution_note,
            )

        normalized_type = normalize_revision_letter_type(preferred_type)
        fallback_no = (fallback_yazi_no or preferred_yazi_no or "").strip()
        if not fallback_no or not normalized_type:
            return None

        document, resolved_lookup = self._find_letter_document(
            fallback_no,
            None,
            normalized_type,
        )
        return self._build_letter_payload(
            rev=rev,
            yazi_no=fallback_no,
            yazi_tarih=None,
            logical_type=normalized_type,
            lookup_type=resolved_lookup or normalized_type,
            document_exists=document is not None,
            source_field=None,
        )

    def build_preview_letter_payload(
        self, rev: Optional[RevizyonModel], yazi_no: str
    ) -> Optional[dict]:
        if not rev or not yazi_no:
            return None
        return self.resolve_letter_payload(rev, preferred_yazi_no=yazi_no)

    def build_letter_payload_from_revision(
        self,
        rev: Optional[RevizyonModel],
        yazi_turu: str,
        fallback_yazi_no: Optional[str] = None,
    ) -> Optional[dict]:
        return self.resolve_letter_payload(
            rev,
            preferred_type=yazi_turu,
            fallback_yazi_no=fallback_yazi_no,
        )

    def open_revision_document(self, rev: Optional[RevizyonModel]) -> bool:
        """Open the revision document represented by the given model."""
        if not rev:
            QMessageBox.warning(
                self.parent,
                tr("Uyarı"),
                tr("Açılacak revizyon bulunamadı."),
            )
            return False

        document = self.db.dokumani_getir(rev.id)
        if not document:
            QMessageBox.warning(
                self.parent,
                tr("Uyarı"),
                tr("Bu revizyona ait doküman bulunamadı."),
            )
            return False

        filename, file_data = document
        opened = self.file_service.open_temporary_document(
            filename,
            file_data,
            temp_prefix=f"rev_{rev.id}",
            error_title=tr("Açma Hatası"),
        )
        if opened:
            self.logger.info("Revizyon dokümanı açıldı: rev_id=%s", rev.id)
        return opened

    def open_letter_document(self, payload: Optional[dict]) -> bool:
        """Open the exact letter document represented by the preview payload."""
        if not payload or payload.get("kind") != "letter":
            QMessageBox.warning(
                self.parent,
                tr("Uyarı"),
                tr("Açılacak yazı dokümanı bulunamadı."),
            )
            return False

        yazi_no = payload.get("yazi_no") or ""
        yazi_tarih = payload.get("yazi_tarih")
        yazi_turu = payload.get("lookup_yazi_turu") or payload.get("yazi_turu") or ""
        logical_yazi_turu = payload.get("logical_yazi_turu") or yazi_turu

        if not yazi_no or not yazi_turu:
            QMessageBox.warning(
                self.parent,
                tr("Uyarı"),
                tr("Yazı dokümanı bilgisi eksik."),
            )
            return False

        document, resolved_lookup = self._find_letter_document(
            yazi_no,
            yazi_tarih,
            logical_yazi_turu,
            preferred_lookup=yazi_turu,
        )
        if not document:
            QMessageBox.information(
                self.parent,
                tr("Yazı Bulunamadı"),
                tr("'{yazi_no}' numaralı yazı dokümanı bulunamadı.").format(
                    yazi_no=yazi_no
                ),
            )
            return False

        filename, file_data = document
        opened = self.file_service.open_temporary_document(
            filename,
            file_data,
            temp_prefix=f"yazi_{yazi_no}",
            error_title=tr("Açma Hatası"),
        )
        if opened:
            self.logger.info(
                "Yazı dokümanı açıldı: %s (requested=%s, resolved=%s)",
                yazi_no,
                logical_yazi_turu,
                resolved_lookup or yazi_turu,
            )
        return opened
