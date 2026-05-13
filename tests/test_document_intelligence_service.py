from pathlib import Path

import fitz

from services.document_intelligence_service import DocumentIntelligenceService


def _create_pdf(path: Path, lines):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "\n".join(lines))
    doc.save(path)
    doc.close()


def test_analyze_project_document_uses_filename_when_pattern_matches(tmp_path):
    service = DocumentIntelligenceService()

    result = service.analyze_project_document(
        str(tmp_path / "1-MEK-2026_Pompa_Modernizasyonu.pdf")
    )

    assert result["kod"] == "1-MEK-2026"
    assert result["isim"] == "Pompa Modernizasyonu"
    assert result["source"] == "filename"


def test_analyze_project_document_extracts_pdf_text(tmp_path):
    service = DocumentIntelligenceService()
    pdf_path = tmp_path / "proje.pdf"
    _create_pdf(
        pdf_path,
        [
            "Proje Adi: Pompa Istasyonu Modernizasyonu",
            "Kod: 2-ELEK-2026",
        ],
    )

    result = service.analyze_project_document(str(pdf_path))

    assert result["kod"] == "2-ELEK-2026"
    assert result["isim"] == "Pompa Istasyonu Modernizasyonu"
    assert result["source"] == "pdf_text"


def test_analyze_letter_document_extracts_pdf_text(tmp_path):
    service = DocumentIntelligenceService()
    pdf_path = tmp_path / "yazi.pdf"
    _create_pdf(
        pdf_path,
        [
            "12.04.2026 tarih ve 456 sayili yazidir.",
            "Konu: Pompa istasyonu revizyon talebi",
            "Kurum: BOTAS Genel Mudurlugu",
        ],
    )

    result = service.analyze_letter_document(str(pdf_path))

    assert result["yazi_tarih"] == "12.04.2026"
    assert result["yazi_no"] == "456"
    assert result["konu"] == "Pompa istasyonu revizyon talebi"
    assert result["kurum"] == "BOTAS Genel Mudurlugu"
    assert result["aciklama"] == "BOTAS Genel Mudurlugu - Pompa istasyonu revizyon talebi"
    assert result["source"] == "pdf_text"


def test_analyze_letter_document_uses_tesseract_backend_for_images(tmp_path):
    class FakeBackend:
        def run_ocr(self, image_path):
            assert image_path.endswith(".png")
            return (
                "12.04.2026 tarih ve 789 sayili yazidir.\n"
                "Konu: Hat baglantisi onayi\n"
                "Kurum: BOTAŞ Etut"
            )

    service = DocumentIntelligenceService()
    image_path = tmp_path / "taranmis.png"
    image_path.write_bytes(b"fake-image")
    service._get_tesseract_backend = lambda: FakeBackend()
    service._is_pytesseract_available = lambda: False

    result = service.analyze_letter_document(str(image_path))

    assert result["yazi_tarih"] == "12.04.2026"
    assert result["yazi_no"] == "789"
    assert result["konu"] == "Hat baglantisi onayi"
    assert result["kurum"] == "BOTAŞ Etut"
    assert result["source"] == "image_tesseract"
    assert result["used_ocr"] is True
