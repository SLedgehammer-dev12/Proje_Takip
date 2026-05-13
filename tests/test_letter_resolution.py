from pathlib import Path

from letter_resolution import resolve_revision_letter_candidate
from models import RevizyonModel
from services.document_service import DocumentService


class FakeDB:
    def __init__(self, docs=None):
        self.docs = docs or {}
        self.calls = []

    def yazi_dokumani_getir(self, yazi_no, yazi_tarih=None, yazi_turu=None):
        self.calls.append((yazi_no, yazi_tarih, yazi_turu))
        return self.docs.get((yazi_no, yazi_tarih, yazi_turu))

    def dokumani_getir(self, rev_id):
        return ("rev.pdf", b"%PDF-1.7\n")


class FakeFileService:
    def __init__(self):
        self.opened = []

    def open_temporary_document(self, filename, file_data, **kwargs):
        self.opened.append((filename, file_data, kwargs))
        return True


def make_revision(**overrides):
    data = {
        "id": 1,
        "proje_rev_no": 0,
        "revizyon_kodu": "A",
        "durum": "Onaysiz",
        "tarih": "2026-03-31",
        "aciklama": "",
        "dokuman_durumu": "Var",
        "onay_yazi_no": None,
        "onay_yazi_tarih": None,
        "red_yazi_no": None,
        "red_yazi_tarih": None,
        "gelen_yazi_no": None,
        "gelen_yazi_tarih": None,
        "tse_gonderildi": 0,
        "yazi_turu": "yok",
        "dosya_adi": "rev.pdf",
        "yazi_dokuman_durumu": "-",
        "supheli_yazi_dokumani": 0,
        "takipte_mi": 0,
        "takip_notu": None,
    }
    data.update(overrides)
    return RevizyonModel(**data)


def test_resolver_prefers_real_outgoing_letter_when_yazi_turu_is_stale():
    rev = make_revision(
        durum="Onayli",
        yazi_turu="gelen",
        onay_yazi_no="33048",
        onay_yazi_tarih="29.08.2025",
    )

    candidate = resolve_revision_letter_candidate(rev)

    assert candidate is not None
    assert candidate.logical_type == "onay"
    assert candidate.yazi_no == "33048"
    assert candidate.broad_type == "giden"


def test_document_service_uses_outgoing_fallback_for_mislabeled_red_document():
    rev = make_revision(
        id=991,
        durum="Reddedildi",
        yazi_turu="giden",
        red_yazi_no="40772",
        red_yazi_tarih="23.10.2025",
    )
    db = FakeDB(
        docs={
            ("40772", "23.10.2025", "giden"): (
                "23.10.2025 tarih ve 40772 sayili yazi.pdf",
                b"%PDF-1.7\n",
            )
        }
    )
    file_service = FakeFileService()
    service = DocumentService(db, file_service)

    payload = service.resolve_letter_payload(rev)

    assert payload is not None
    assert payload["logical_yazi_turu"] == "red"
    assert payload["yazi_turu"] == "giden"
    assert payload["document_exists"] is True

    opened = service.open_letter_document(payload)

    assert opened is True
    assert file_service.opened[0][0] == "23.10.2025 tarih ve 40772 sayili yazi.pdf"
    assert ("40772", "23.10.2025", "red") in db.calls
    assert ("40772", "23.10.2025", "giden") in db.calls


def test_preview_payload_matches_clicked_number_even_with_inconsistent_metadata():
    rev = make_revision(
        durum="Onayli",
        yazi_turu="gelen",
        onay_yazi_no="42044",
        onay_yazi_tarih="04.11.2025",
    )
    db = FakeDB(
        docs={
            ("42044", "04.11.2025", "onay"): (
                "42044.pdf",
                b"%PDF-1.7\n",
            )
        }
    )
    service = DocumentService(db, FakeFileService())

    payload = service.build_preview_letter_payload(rev, "42044")

    assert payload is not None
    assert payload["yazi_no"] == "42044"
    assert payload["logical_yazi_turu"] == "onay"
