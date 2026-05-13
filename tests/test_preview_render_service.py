from collections import OrderedDict
from types import SimpleNamespace

from services.preview_render_service import PreviewRenderService


class FakeDB:
    def __init__(self):
        self.letter_calls = []

    def yazi_dokumani_getir(self, yazi_no, yazi_tarih=None, yazi_turu=None):
        self.letter_calls.append((yazi_no, yazi_tarih, yazi_turu))
        return ("letter.pdf", b"%PDF-1.7\ncached letter\n")


def test_prepare_letter_preview_uses_cache_for_repeated_requests():
    db = FakeDB()
    service = PreviewRenderService(db=db, max_letter_cache_size=2)
    payload = {
        "kind": "letter",
        "yazi_no": "42044",
        "yazi_tarih": "04.11.2025",
        "lookup_yazi_turu": "onay",
    }

    first = service.prepare_letter_preview(payload)
    second = service.prepare_letter_preview(payload)

    assert first.status == "ready"
    assert second.status == "ready"
    assert db.letter_calls == [("42044", "04.11.2025", "onay")]


def test_prepare_revision_preview_uses_clean_turkish_message_for_missing_document_flag():
    service = PreviewRenderService(db=FakeDB())
    revision = SimpleNamespace(id=10, dokuman_durumu="Yok")

    result = service.prepare_revision_preview(revision)

    assert result.status == "no_document_flag"
    assert result.message == "Doküman yok"


def test_prepare_letter_preview_uses_clean_turkish_message_when_document_missing():
    class MissingLetterDB(FakeDB):
        def yazi_dokumani_getir(self, yazi_no, yazi_tarih=None, yazi_turu=None):
            self.letter_calls.append((yazi_no, yazi_tarih, yazi_turu))
            return None

    db = MissingLetterDB()
    service = PreviewRenderService(db=db, max_letter_cache_size=2)
    payload = {
        "kind": "letter",
        "yazi_no": "42044",
        "yazi_tarih": "04.11.2025",
        "lookup_yazi_turu": "onay",
    }

    result = service.prepare_letter_preview(payload)

    assert result.status == "missing_letter_document"
    assert result.message == "Bu revizyona ait yazı dokümanı bulunamadı."
    assert db.letter_calls == [
        ("42044", "04.11.2025", "onay"),
        ("42044", "04.11.2025", None),
    ]


def test_preview_render_service_performance_mode_trims_cache_limits():
    service = PreviewRenderService(db=FakeDB())
    service._document_cache = OrderedDict(
        [(1, b"%PDF-1"), (2, b"%PDF-2"), (3, b"%PDF-3")]
    )
    service._letter_document_cache = OrderedDict(
        [
            (("1", "", "gelen"), b"%PDF-a"),
            (("2", "", "gelen"), b"%PDF-b"),
            (("3", "", "gelen"), b"%PDF-c"),
        ]
    )

    service.configure_performance_mode(True)

    assert service.max_cache_size == 2
    assert service.max_letter_cache_size == 2
    assert list(service._document_cache.keys()) == [2, 3]
    assert list(service._letter_document_cache.keys()) == [
        ("2", "", "gelen"),
        ("3", "", "gelen"),
    ]
