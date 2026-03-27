"""
Preview render service for revision document caching and validation.

This keeps preview preparation logic out of the main window while leaving
render worker orchestration in the UI layer.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from models import RevizyonModel
from utils import get_class_logger


@dataclass
class PreviewLoadResult:
    status: str
    document_bytes: Optional[bytes] = None
    message: Optional[str] = None


class PreviewRenderService:
    """Manage cached revision documents and validate them before rendering."""

    def __init__(self, db, max_cache_size: int = 5):
        self.db = db
        self.max_cache_size = max_cache_size
        self.logger = get_class_logger(self)
        self._document_cache: dict[int, bytes] = {}

    def clear_cache(self):
        self._document_cache.clear()

    def invalidate_revision(self, revision_id: Optional[int]):
        if revision_id is None:
            return
        self._document_cache.pop(revision_id, None)

    def prepare_revision_preview(
        self, revision: Optional[RevizyonModel]
    ) -> PreviewLoadResult:
        if not revision:
            return PreviewLoadResult(status="missing_revision")

        if revision.dokuman_durumu != "Var":
            return PreviewLoadResult(status="no_document_flag", message="Doküman yok")

        rev_id = revision.id
        document_bytes = self._document_cache.get(rev_id)
        if document_bytes is None:
            document_tuple = self.db.dokumani_getir(rev_id)
            if not document_tuple:
                self.logger.debug(
                    "Preview prepare: no document row for rev_id=%s",
                    rev_id,
                )
                return PreviewLoadResult(status="missing_document_record")

            document_bytes = document_tuple[1]
            validation_message = self._validate_document_bytes(rev_id, document_bytes)
            if validation_message is not None:
                return PreviewLoadResult(
                    status="invalid_document",
                    message=validation_message,
                )
            self._cache_document(rev_id, document_bytes)
        else:
            validation_message = self._validate_document_bytes(rev_id, document_bytes)
            if validation_message is not None:
                self.invalidate_revision(rev_id)
                return PreviewLoadResult(
                    status="invalid_document",
                    message=validation_message,
                )

        return PreviewLoadResult(status="ready", document_bytes=document_bytes)

    def _cache_document(self, revision_id: int, document_bytes: bytes):
        if len(self._document_cache) >= self.max_cache_size:
            try:
                first_key = next(iter(self._document_cache))
                del self._document_cache[first_key]
            except (StopIteration, KeyError, RuntimeError):
                pass
        self._document_cache[revision_id] = document_bytes

    def _validate_document_bytes(
        self, revision_id: int, document_bytes: Optional[bytes]
    ) -> Optional[str]:
        try:
            if not document_bytes or not isinstance(document_bytes, (bytes, bytearray)):
                self.logger.error(
                    "Invalid preview document type for rev_id=%s",
                    revision_id,
                )
                return "Doküman önizlenemiyor: geçersiz dosya"
            if len(document_bytes) < 5 or document_bytes[:4] != b"%PDF":
                self.logger.error(
                    "Invalid PDF header for rev_id=%s, size=%s",
                    revision_id,
                    len(document_bytes),
                )
                return "Doküman önizlenemiyor: bozuk/uyumsuz dosya"
        except Exception:
            self.logger.exception(
                "Preview document validation failed for rev_id=%s",
                revision_id,
            )
            return "Doküman önizlenemiyor: geçersiz dosya"
        return None
