"""
Preview render service for revision document caching and validation.

This keeps preview preparation logic out of the main window while leaving
render worker orchestration in the UI layer.
"""

from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from i18n import tr
from models import RevizyonModel
from utils import get_class_logger


@dataclass
class PreviewLoadResult:
    status: str
    document_bytes: Optional[bytes] = None
    message: Optional[str] = None


class PreviewRenderService:
    """Manage cached revision documents and validate them before rendering."""

    def __init__(self, db, max_cache_size: int = 5, max_letter_cache_size: int = 8):
        self.db = db
        self.max_cache_size = max_cache_size
        self.max_letter_cache_size = max_letter_cache_size
        self.logger = get_class_logger(self)
        self._document_cache: OrderedDict[int, bytes] = OrderedDict()
        self._letter_document_cache: OrderedDict[tuple[str, str, str], bytes] = (
            OrderedDict()
        )
        self.performance_mode = False

    def clear_cache(self):
        self._document_cache.clear()
        self._letter_document_cache.clear()

    def configure_performance_mode(self, enabled: bool):
        self.performance_mode = bool(enabled)
        if self.performance_mode:
            self.max_cache_size = 2
            self.max_letter_cache_size = 2
        else:
            self.max_cache_size = 5
            self.max_letter_cache_size = 8
        self._trim_cache(self._document_cache, self.max_cache_size)
        self._trim_cache(self._letter_document_cache, self.max_letter_cache_size)

    def invalidate_revision(self, revision_id: Optional[int]):
        if revision_id is None:
            return
        self._document_cache.pop(revision_id, None)

    def invalidate_letter(
        self,
        yazi_no: Optional[str],
        yazi_tarih: Optional[str],
        yazi_turu: Optional[str],
    ):
        if not yazi_no or not yazi_turu:
            return
        cache_key = self._normalize_letter_cache_key(yazi_no, yazi_tarih, yazi_turu)
        self._letter_document_cache.pop(cache_key, None)

    def prepare_revision_preview(
        self, revision: Optional[RevizyonModel]
    ) -> PreviewLoadResult:
        if not revision:
            return PreviewLoadResult(status="missing_revision")

        if revision.dokuman_durumu != "Var":
            return PreviewLoadResult(status="no_document_flag", message=tr("Doküman yok"))

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
            self._touch_document_cache(rev_id)
            validation_message = self._validate_document_bytes(rev_id, document_bytes)
            if validation_message is not None:
                self.invalidate_revision(rev_id)
                return PreviewLoadResult(
                    status="invalid_document",
                    message=validation_message,
                )

        return PreviewLoadResult(status="ready", document_bytes=document_bytes)

    def prepare_letter_preview(self, letter_payload: Optional[dict]) -> PreviewLoadResult:
        if not letter_payload or letter_payload.get("kind") != "letter":
            return PreviewLoadResult(status="missing_letter_payload")

        yazi_no = (letter_payload.get("yazi_no") or "").strip()
        yazi_turu = (
            letter_payload.get("lookup_yazi_turu")
            or letter_payload.get("yazi_turu")
            or ""
        ).strip()
        yazi_tarih = letter_payload.get("yazi_tarih")
        if not yazi_no or not yazi_turu:
            return PreviewLoadResult(status="missing_letter_identity")

        cache_key = self._normalize_letter_cache_key(yazi_no, yazi_tarih, yazi_turu)
        document_bytes = self._letter_document_cache.get(cache_key)
        if document_bytes is None:
            # Önce bildirilen türle dene, sonra türsüz (geniş) fallback
            document_tuple = self.db.yazi_dokumani_getir(yazi_no, yazi_tarih, yazi_turu)
            fallback_used = False
            if not document_tuple:
                document_tuple = self.db.yazi_dokumani_getir(yazi_no, yazi_tarih, None)
                fallback_used = document_tuple is not None

            if not document_tuple:
                self.logger.debug(
                    "Letter preview prepare: no document row for yazi_no=%s type=%s",
                    yazi_no,
                    yazi_turu,
                )
                return PreviewLoadResult(
                    status="missing_letter_document",
                    message=tr("Bu revizyona ait yazı dokümanı bulunamadı."),
                )

            document_bytes = document_tuple[1]
            validation_message = self._validate_document_bytes(
                f"letter:{yazi_no}:{yazi_turu}",
                document_bytes,
            )
            if validation_message is not None:
                return PreviewLoadResult(
                    status="invalid_letter_document",
                    message=validation_message,
                )
            # Fallback ile bulduysak cache key'i türsüz (ANY) tutarak tekrar kullanılabilir yap
            cache_to_use = cache_key if not fallback_used else self._normalize_letter_cache_key(yazi_no, yazi_tarih, "any")
            self._cache_letter_document(cache_to_use, document_bytes)
        else:
            self._touch_letter_cache(cache_key)
            validation_message = self._validate_document_bytes(
                f"letter:{yazi_no}:{yazi_turu}",
                document_bytes,
            )
            if validation_message is not None:
                self.invalidate_letter(yazi_no, yazi_tarih, yazi_turu)
                return PreviewLoadResult(
                    status="invalid_letter_document",
                    message=validation_message,
                )

        return PreviewLoadResult(status="ready", document_bytes=document_bytes)

    def _cache_document(self, revision_id: int, document_bytes: bytes):
        self._trim_cache(self._document_cache, self.max_cache_size - 1)
        self._document_cache[revision_id] = document_bytes

    def _touch_document_cache(self, revision_id: int):
        try:
            self._document_cache.move_to_end(revision_id)
        except KeyError:
            return

    def _cache_letter_document(
        self, cache_key: tuple[str, str, str], document_bytes: bytes
    ):
        self._trim_cache(self._letter_document_cache, self.max_letter_cache_size - 1)
        self._letter_document_cache[cache_key] = document_bytes

    def _touch_letter_cache(self, cache_key: tuple[str, str, str]):
        try:
            self._letter_document_cache.move_to_end(cache_key)
        except KeyError:
            return

    def _normalize_letter_cache_key(
        self, yazi_no: str, yazi_tarih: Optional[str], yazi_turu: str
    ) -> tuple[str, str, str]:
        return (yazi_no.strip(), (yazi_tarih or "").strip(), yazi_turu.strip())

    def _trim_cache(self, cache: OrderedDict, max_size: int):
        target_size = max(0, int(max_size))
        while len(cache) > target_size:
            try:
                cache.popitem(last=False)
            except (KeyError, RuntimeError):
                break

    def _validate_document_bytes(
        self, revision_id: int, document_bytes: Optional[bytes]
    ) -> Optional[str]:
        try:
            if not document_bytes or not isinstance(document_bytes, (bytes, bytearray)):
                self.logger.error(
                    "Invalid preview document type for rev_id=%s",
                    revision_id,
                )
                return tr("Doküman önizlenemiyor: geçersiz dosya")
            if len(document_bytes) < 5 or document_bytes[:4] != b"%PDF":
                self.logger.error(
                    "Invalid PDF header for rev_id=%s, size=%s",
                    revision_id,
                    len(document_bytes),
                )
                return tr("Doküman önizlenemiyor: bozuk/uyumsuz dosya")
        except Exception:
            self.logger.exception(
                "Preview document validation failed for rev_id=%s",
                revision_id,
            )
            return tr("Doküman önizlenemiyor: geçersiz dosya")
        return None
