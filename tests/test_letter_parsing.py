"""Tests for letter/document text parsing improvements (v3.2.1).

Covers header-based "Sayı :", "Tarih:", "Konu :" extraction
for formal Turkish letter formats (resmi yazı).
"""

import pytest
from services.document_intelligence_service import DocumentIntelligenceService


@pytest.fixture(scope="module")
def service():
    return DocumentIntelligenceService()


# ============================================================================
# Sample Formal Letter Texts (Turkish Resmi Yazı Formatı)
# ============================================================================

SAMPLE_LETTER_1 = """T.C.
ENERJİ VE TABİİ KAYNAKLAR BAKANLIĞI
Boru Hatları İle Petrol Taşıma A.Ş.

Sayı : E-12345678
Tarih: 25.03.2025
Konu : Doğalgaz Boru Hattı Projesi Revizyon Onayı Hk.

İlgi : 15.01.2025 tarihli ve 98765 sayılı yazınız.

Yazınızda belirtilen revizyon talebi incelenmiştir.
Bahse konu projeye ait revize dokümanlar ekte sunulmaktadır.
"""

SAMPLE_LETTER_2 = """T.C.
BOTAŞ GENEL MÜDÜRLÜĞÜ

Sayı : 1234567890
Tarih: 15/06/2025
Konu : Proje Takip Sistemi Revizyon Hk.

İlgi: 01.03.2025 tarihli ve 555 sayılı yazı.

Ekte belirtilen revizyon onaylanmıştır.
"""

SAMPLE_LETTER_3 = """Evrak Tarih ve Sayısı: 25.03.2025 - 98765

KONU: Petrol Boru Hattı Etüd Projesi

İLGİ: 15.01.2025 tarih ve 1234 sayılı yazı.
"""

SAMPLE_LETTER_4 = """T.C.
ÇEVRE VE ŞEHİRCİLİK BAKANLIĞI

Sayı : E-55432198
Tarih: 01.01.2024
Konu : ÇED Raporu Değerlendirme

Projeniz kapsamında hazırlanan ÇED raporu incelenmiş olup,
olumlu görüş verilmiştir.
"""

SAMPLE_LETTER_5 = """SAYI: B.19.5.BÜ.0.001/12345
TARİH: 10.12.2025
KONU: Teknik Şartname Değişikliği Hk.
"""

SAMPLE_LETTER_6 = """sayı : e-87654321
tarih: 20/05/2025
konu : boru hattı bakım çalışması hk.

ilgi : 01.04.2025 tarihli ve 123 sayılı yazınız.
"""

SAMPLE_LETTER_7 = """10.05.2025 tarih ve 45678 sayılı yazı
"""

SAMPLE_LETTER_8 = """Konu : Bu çok uzun bir konu başlığıdır ve birden fazla
satıra yayılmıştır bu nedenle
tam metnin okunması gerekir.

Sayı : 1000
Tarih: 05.05.2025
"""


# ============================================================================
# Sayı (Number) Extraction Tests
# ============================================================================


class TestSayiExtraction:
    """Test extraction of 'Sayı :' from letter headers."""

    def test_extracts_e_prefixed_number_from_header(self, service):
        """E-12345678 format from formal header."""
        result = service.parse_letter_text(SAMPLE_LETTER_1)
        assert result["yazi_no"] == "E-12345678", (
            f"Expected 'E-12345678', got '{result['yazi_no']}'"
        )

    def test_extracts_plain_number_from_header(self, service):
        """Plain number from formal header."""
        result = service.parse_letter_text(SAMPLE_LETTER_2)
        assert result["yazi_no"] == "1234567890", (
            f"Expected '1234567890', got '{result['yazi_no']}'"
        )

    def test_extracts_e_prefixed_from_another_header(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_4)
        assert result["yazi_no"] == "E-55432198"

    def test_extracts_compound_code_from_header(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_5)
        assert "B.19.5" in result["yazi_no"] or "12345" in result["yazi_no"], (
            f"Expected compound code, got '{result['yazi_no']}'"
        )

    def test_extracts_lowercase_e_number(self, service):
        """Lowercase 'sayı : e-xxxxx' format."""
        result = service.parse_letter_text(SAMPLE_LETTER_6)
        assert result["yazi_no"] == "E-87654321", (
            f"Expected 'E-87654321', got '{result['yazi_no']}'"
        )

    def test_extracts_number_from_sayili_format(self, service):
        """Legacy 'DD.MM.YYYY tarih ve NNN sayılı' format."""
        result = service.parse_letter_text(SAMPLE_LETTER_7)
        assert result["yazi_no"] == "45678", (
            f"Expected '45678', got '{result['yazi_no']}'"
        )


# ============================================================================
# Tarih (Date) Extraction Tests
# ============================================================================


class TestTarihExtraction:
    """Test extraction of 'Tarih:' from letter headers."""

    def test_extracts_dot_format_date(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_1)
        assert result["yazi_tarih"] == "25.03.2025", (
            f"Expected '25.03.2025', got '{result['yazi_tarih']}'"
        )

    def test_extracts_slash_format_date(self, service):
        """Date with '/' separators."""
        result = service.parse_letter_text(SAMPLE_LETTER_2)
        assert result["yazi_tarih"] == "15.06.2025", (
            f"Expected '15.06.2025' (standardized), got '{result['yazi_tarih']}'"
        )

    def test_extracts_date_from_another_header(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_4)
        assert result["yazi_tarih"] == "01.01.2024"

    def test_extracts_date_from_compound_code_header(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_5)
        assert result["yazi_tarih"] == "10.12.2025"

    def test_extracts_lowercase_tarih_date(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_6)
        assert result["yazi_tarih"] == "20.05.2025"

    def test_extracts_date_from_legacy_format(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_7)
        assert result["yazi_tarih"] == "10.05.2025"

    def test_extracts_date_from_evrak_header(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_3)
        assert result["yazi_tarih"] == "25.03.2025"


# ============================================================================
# Konu (Subject) Extraction Tests
# ============================================================================


class TestKonuExtraction:
    """Test extraction of 'Konu :' from letter headers."""

    def test_extracts_subject_from_header(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_1)
        assert "Doğalgaz" in result["konu"], (
            f"Expected subject containing 'Doğalgaz', got '{result['konu']}'"
        )

    def test_extracts_subject_from_another_header(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_2)
        assert "Proje Takip" in result["konu"], (
            f"Expected 'Proje Takip', got '{result['konu']}'"
        )

    def test_extracts_subject_fallback_hakkinda(self, service):
        """Legacy 'hakkında' subject extraction."""
        result = service.parse_letter_text(SAMPLE_LETTER_3)
        assert "Petrol Boru Hattı" in result["konu"] or "Etüd" in result["konu"], (
            f"Expected subject, got '{result['konu']}'"
        )

    def test_extracts_multiline_subject(self, service):
        """Multi-line subject should be captured."""
        result = service.parse_letter_text(SAMPLE_LETTER_8)
        assert len(result["konu"]) > 20, (
            f"Expected multi-line subject, got '{result['konu']}'"
        )
        assert "konu başlığıdır" in result["konu"].lower()


# ============================================================================
# Combined Extraction Tests
# ============================================================================


class TestCombinedExtraction:
    """Test that all fields are extracted together correctly."""

    def test_all_fields_from_formal_letter_1(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_1)
        assert result["yazi_no"] == "E-12345678"
        assert result["yazi_tarih"] == "25.03.2025"
        assert len(result["konu"]) > 5

    def test_all_fields_from_formal_letter_2(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_2)
        assert result["yazi_no"] == "1234567890"
        assert result["yazi_tarih"] == "15.06.2025"
        assert len(result["konu"]) > 5

    def test_all_fields_from_lowercase_letter(self, service):
        result = service.parse_letter_text(SAMPLE_LETTER_6)
        assert result["yazi_no"] == "E-87654321"
        assert result["yazi_tarih"] == "20.05.2025"
        assert "boru hattı" in result["konu"].lower()

    def test_return_values_are_strings(self, service):
        """All return values should be strings."""
        result = service.parse_letter_text(SAMPLE_LETTER_1)
        assert isinstance(result["yazi_no"], str)
        assert isinstance(result["yazi_tarih"], str)
        assert isinstance(result["konu"], str)
        assert isinstance(result["kurum"], str)
        assert isinstance(result["aciklama"], str)

    def test_dont_crash_on_empty_text(self, service):
        result = service.parse_letter_text("")
        assert result["yazi_no"] == ""
        assert result["yazi_tarih"] == ""
        assert result["konu"] == ""

    def test_dont_crash_on_nonsense_text(self, service):
        result = service.parse_letter_text("asdfghjkl qwerty 12345")
        # Should not raise, may or may not find any fields
        assert isinstance(result["yazi_no"], str)


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Edge cases for letter parsing."""

    def test_tarih_with_dot_behind(self, service):
        """'Tarih: 25.03.2025' with period after colon."""
        result = service.parse_letter_text("Tarih: 25.03.2025\nSayı: 12345\nKonu: Test")
        assert result["yazi_tarih"] == "25.03.2025"

    def test_sayi_without_e_prefix(self, service):
        result = service.parse_letter_text("Sayı: 55555\nTarih: 01.01.2024\nKonu: Test")
        assert result["yazi_no"] == "55555"

    def test_date_standardization_slash_to_dot(self, service):
        """Slash dates should be standardized to dots."""
        result = service.parse_letter_text("Tarih: 01/01/2024\nSayı: 123\nKonu: Test")
        assert result["yazi_tarih"] == "01.01.2024"
        assert "/" not in result["yazi_tarih"]

    def test_header_priority_over_body(self, service):
        """Header 'Sayı : 1111' should be preferred over body mention of 'sayı: 2222'."""
        text = "Sayı : 1111\nTarih: 01.01.2024\nKonu: Test\n\nBody mentions sayı: 2222"
        result = service.parse_letter_text(text)
        assert result["yazi_no"] == "1111", (
            f"Header should take priority, got '{result['yazi_no']}'"
        )


# ============================================================================
# Ek (Attachment) Extraction Tests
# ============================================================================

SAMPLE_FORMAL_EKLER = """Ekler:
Ek-1: 0-CS-C-001-1034 Rev A Boru Hattı Güzergah Planı
Ek-2: 0-CS-E-002-2056 Rev B Elektrik Şeması
Ek-3: 1-ME-M-003-7890 Rev 0 Mekanik Ekipman Listesi

Adres: Ankara Mah. Atatürk Cad. No:12 Çankaya/ANKARA
Telefon: 0312 123 45 67
Faks: 0312 987 65 43
e-posta: info@botas.gov.tr
www.botas.gov.tr

DAĞITIM:
Birim A
Birim B
"""

SAMPLE_EKLER_WITH_CONTACT = """Ekler:
1- 0-CS-C-001-1034 Boru Hattı Planı
2- 0-ME-E-002-2056 Elektrik Şeması
Telefon: 0312 123 4567
Faks: 0312 987 6543
Belgegeçer: 0312 111 2233
e-posta: test@kurum.gov.tr
KEP: kurum@hs01.kep.tr
www.kurum.gov.tr

Adres: İstanbul Mah. Cumhuriyet Cad. No:100 Kat:5
Posta Kodu: 34000

DAĞITIM GEREĞİ:
Sayın Yetkili
"""

SAMPLE_EKLER_SIMPLE_NUMBERED = """Ek:
1) 0-CS-C-001-1034 Rev A Plan
2) 0-CS-E-002-2056 Rev B Şema
a) 1-ME-M-003-7890 Rev 0 Mekanik
"""

SAMPLE_EKLER_EK_PREFIX = """EKLER:
Ek-1 0-CS-C-001-1034 Rev 0 Boru Hattı Planı
Ek-2 0-CS-E-002-2056 Rev A Elektrik Şeması
EK 3: 1-ME-M-003-7890 Rev B Mekanik
"""


class TestEkExtraction:
    """Test attachment (ek) extraction from formal letters."""

    def test_extracts_only_real_attachments(self, service):
        """Contact info lines should NOT appear in ekler list."""
        result = service.parse_letter_text(SAMPLE_FORMAL_EKLER)
        ekler = result["ekler_listesi"]
        assert len(ekler) == 3, f"Expected 3 attachments, got {len(ekler)}"

        codes = [e["kod"] for e in ekler]
        assert "0-CS-C-001-1034" in codes
        assert "0-CS-E-002-2056" in codes
        assert "1-ME-M-003-7890" in codes

    def test_filters_email_addresses(self, service):
        """@ containing lines should be filtered."""
        result = service.parse_letter_text(SAMPLE_EKLER_WITH_CONTACT)
        ekler_ham = " | ".join(e["ham_metin"] for e in result["ekler_listesi"])
        assert "@" not in ekler_ham, f"Email leaked into ekler: {ekler_ham}"

    def test_filters_websites(self, service):
        """www.* and .com/.gov domains should be filtered."""
        result = service.parse_letter_text(SAMPLE_EKLER_WITH_CONTACT)
        ekler_ham = " | ".join(e["ham_metin"] for e in result["ekler_listesi"])
        assert "www." not in ekler_ham.lower()

    def test_filters_telephone_numbers(self, service):
        """Phone/fax numbers should be filtered."""
        result = service.parse_letter_text(SAMPLE_FORMAL_EKLER)
        ekler_ham = " | ".join(e["ham_metin"] for e in result["ekler_listesi"])
        assert "Telefon" not in ekler_ham
        assert "0312" not in ekler_ham
        assert "Faks" not in ekler_ham

    def test_filters_address_lines(self, service):
        """Address lines (Mah., Cad., Posta Kodu) should be filtered."""
        result = service.parse_letter_text(SAMPLE_EKLER_WITH_CONTACT)
        ekler_ham = " | ".join(e["ham_metin"] for e in result["ekler_listesi"])
        assert "Mah." not in ekler_ham
        assert "Cad." not in ekler_ham
        assert "Posta Kodu" not in ekler_ham
        assert "Kat:" not in ekler_ham

    def test_filters_kep_address(self, service):
        """KEP addresses should be filtered."""
        result = service.parse_letter_text(SAMPLE_EKLER_WITH_CONTACT)
        ekler_ham = " | ".join(e["ham_metin"] for e in result["ekler_listesi"])
        assert "KEP" not in ekler_ham

    def test_filters_belgegecer(self, service):
        """Belgegeçer (fax) lines should be filtered."""
        result = service.parse_letter_text(SAMPLE_EKLER_WITH_CONTACT)
        ekler_ham = " | ".join(e["ham_metin"] for e in result["ekler_listesi"])
        assert "Belgegeçer" not in ekler_ham

    def test_simple_numbered_ek_extraction(self, service):
        """1), 2), a) style numbering."""
        result = service.parse_letter_text(SAMPLE_EKLER_SIMPLE_NUMBERED)
        ekler = result["ekler_listesi"]
        assert len(ekler) == 3, f"Expected 3, got {len(ekler)}"
        codes = [e["kod"] for e in ekler]
        assert "0-CS-C-001-1034" in codes
        assert "0-CS-E-002-2056" in codes

    def test_ek_prefix_variations(self, service):
        """Ek-1, Ek-2, EK 3: variations."""
        result = service.parse_letter_text(SAMPLE_EKLER_EK_PREFIX)
        ekler = result["ekler_listesi"]
        assert len(ekler) == 3, f"Expected 3, got {len(ekler)}"
        codes = [e["kod"] for e in ekler]
        assert "0-CS-C-001-1034" in codes

    def test_revision_extraction_from_ek(self, service):
        """Rev codes should be extracted from attachment lines."""
        result = service.parse_letter_text(SAMPLE_FORMAL_EKLER)
        ekler = result["ekler_listesi"]
        revs = [e["revizyon"] for e in ekler if e["revizyon"]]
        assert "A" in revs
        assert "B" in revs
        assert "0" in revs

    def test_dagitim_section_not_in_ekler(self, service):
        """DAĞITIM section should not appear in ekler."""
        result = service.parse_letter_text(SAMPLE_FORMAL_EKLER)
        ekler = result["ekler_listesi"]
        ham_texts = " ".join(e["ham_metin"] for e in ekler)
        assert "Dağıtım" not in ham_texts
        assert "DAĞITIM" not in ham_texts

    def test_empty_text_returns_empty_ekler(self, service):
        result = service.parse_letter_text("")
        assert result["ekler_listesi"] == []


# ============================================================================
# Contact Info Filtering Unit Tests
# ============================================================================


class TestContactFiltering:
    """Unit tests for _is_contact_info method."""

    def test_email_is_contact(self, service):
        assert service._is_contact_info("e-posta: info@botas.gov.tr")

    def test_website_is_contact(self, service):
        assert service._is_contact_info("www.botas.gov.tr")

    def test_phone_is_contact(self, service):
        assert service._is_contact_info("Telefon: 0312 123 45 67")

    def test_fax_is_contact(self, service):
        assert service._is_contact_info("Faks: 0312 987 65 43")
        assert service._is_contact_info("Belgegeçer: 0312 111 22 33")

    def test_address_is_contact(self, service):
        assert service._is_contact_info("Adres: Ankara Mah. Atatürk Cad. No:12")
        assert service._is_contact_info("İstanbul Mah. Cumhuriyet Cad.")

    def test_kep_is_contact(self, service):
        assert service._is_contact_info("KEP: kurum@hs01.kep.tr")

    def test_posta_kodu_is_contact(self, service):
        assert service._is_contact_info("Posta Kodu: 34000")
        assert service._is_contact_info("PK: 06500")

    def test_internet_bilgi_is_contact(self, service):
        assert service._is_contact_info("İnternet Adresi: www.kurum.gov.tr")
        assert service._is_contact_info("Bilgi İçin: Ahmet Yılmaz")

    def test_sayfa_is_contact(self, service):
        assert service._is_contact_info("Sayfa 1 / 3")

    def test_e_imza_is_contact(self, service):
        assert service._is_contact_info("Elektronik İmza: Mehmet Demir")
        assert service._is_contact_info("e-imza: Ayşe Kaya")

    def test_document_code_is_not_contact(self, service):
        assert not service._is_contact_info("0-CS-C-001-1034 Rev A Boru Hattı Planı")
        assert not service._is_contact_info("1-ME-E-002-2056 Rev B Elektrik Şeması")

    def test_project_name_is_not_contact(self, service):
        assert not service._is_contact_info("Boru Hattı Güzergah Planı")
        assert not service._is_contact_info("Mekanik Ekipman Listesi Rev 0")
