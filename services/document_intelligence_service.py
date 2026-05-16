import io
import logging
import os
import re
import tempfile
from typing import Any, Dict, Optional

from services.tesseract_backend import TesseractBackend
from utils import dosyadan_proje_bilgisi_cikar, dosyadan_tarih_sayi_cikar, get_class_logger


class DocumentIntelligenceService:
    """Extract lightweight metadata from project and letter documents."""

    _PROJECT_FILENAME_PATTERN = re.compile(r"([0-4]-.+?-\d{4})_(.+)$", re.IGNORECASE)

    # Legacy simple code pattern (fallback)
    _PROJECT_CODE_PATTERN = re.compile(
        r"\b([0-4]-[A-Z0-9\xc7\u011e\u0130\xd6\u015e\xdc]+(?:-[A-Z0-9\xc7\u011e\u0130\xd6\u015e\xdc]+)*-\d{3,})\b",
        re.IGNORECASE,
    )

    # ── Title-block field label patterns ──────────────────────────────────────
    # Matches: "Dokuman No:", "Döküman No:", "Document No:", "Dok. No:", "Doc. No:"
    _TB_DOKUMAN_NO = re.compile(
        r"(?:d[oö]k[\u00fc]?man|document|dok|doc)[\.\s]*no[\s]*[:\-]?[\s]*(.+)",
        re.IGNORECASE,
    )
    # Compound document-code pattern: digit(s)-LETTERS ... digit(s)-LETTERS-...
    # Handles both space-separated compound codes AND single segment codes.
    _TB_DOC_CODE = re.compile(
        r"(\d[-\s][A-Z][A-Z0-9\-]+(?:\s+\d[-\s][A-Z][A-Z0-9\-]+)*)",
        re.IGNORECASE,
    )
    # Revision table: "Rev A", "Revision: B", standalone "A" after rev header
    _TB_REV = re.compile(
        r"(?:rev(?:izyon)?[\s\.:\-]*|revision[\s\.:\-]*)([A-Z0-9]{1,3})",
        re.IGNORECASE,
    )
    # Contract / yapim isi: any text ending with "yap\u0131m i\u015fi" or "yap\u0131m i\u015fleri"
    _TB_YAPIM_ISI = re.compile(
        r"(.{8,200}?\byap[\u0131i]m\s+i\u015f(?:i|leri)?)",
        re.IGNORECASE,
    )
    _LETTER_DATE_NO_PATTERNS = (
        # Pattern 1: "DD.MM.YYYY ... 12345 sayılı" or "DD.MM.YYYY tarihli 12345"
        re.compile(
            r"(\d{2}[\./]\d{2}[\./]\d{4})\s*(?:tarih(?:li)?\s*(?:ve)?\s*)?([0-9]{1,12})\s*(?:sayılı|sayili|no'?lu|nolu)?",
            re.IGNORECASE,
        ),
        # Pattern 2: Full "Sayı: CODE/NUMBER" — captures the full code then trailing digits
        # E.g. "Sayı: B.19.5.BÜ.0.001/12345"  →  yazi_no=12345
        re.compile(
            r"(?:sayı|sayi|evrak\s*no|yazı\s*no|yazi\s*no)\s*[:\-]?\s*([A-Z0-9\xc7\u011e\u0130\xd6\u015e\xdc\.\-_/]+(?:[/\-][0-9]+)+)",
            re.IGNORECASE,
        ),
        # Pattern 3: Sayı followed immediately by digits (legacy)
        re.compile(
            r"(?:sayı|sayi|evrak\s*no|yazı\s*no|yazi\s*no)\s*[:\-]?\s*([0-9]{1,12}).{0,80}?(\d{2}[\./]\d{2}[\./]\d{4})",
            re.IGNORECASE | re.DOTALL,
        ),
    )

    # ── Header-aware patterns: look for "Sayı : CODE", "Tarih: DD.MM.YYYY" in title block ──
    _HEADER_SAYI = re.compile(
        r"(?:^|\n)\s*(?:sayı|sayi)\s*:\s*([Ee]?[-]?\d+(?:\.\d+)*(?:[-/]\d+)*)\s*\n",
        re.IGNORECASE,
    )
    _HEADER_SAYI_COMPOUND = re.compile(
        r"(?:^|\n)\s*(?:sayı|sayi)\s*:\s*([A-Z0-9\xc7\u011e\u0130\xd6\u015e\xdc\.\-_/]+?)\s*\n",
        re.IGNORECASE,
    )
    # "Evrak Tarih ve Sayısı: DD.MM.YYYY - NNN" format
    _EVRAK_TARIH_SAYI = re.compile(
        r"(?:^|\n)\s*(?:evrak\s*tarih\s*(?:ve)?\s*(?:sayı|sayi)(?:sı|si)?)\s*:\s*(\d{2}[\./]\d{2}[\./]\d{4})\s*[-–]\s*([0-9]+)",
        re.IGNORECASE,
    )
    _HEADER_TARIH = re.compile(
        r"(?:^|\n)\s*(?:tarih)\s*:\s*(\d{2}[\./]\d{2}[\./]\d{4})\s*\n",
        re.IGNORECASE,
    )
    _HEADER_KONU_SINGLE = re.compile(
        r"(?:^|\n)\s*(?:konu|subject)\s*:\s*(.+?)(?=\n\s*(?:sayı|sayi|tarih|ilgi|referans|ek|dağıtım|dagitim|imza)\s*:|\n\s*\n|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    _HEADER_KONU_MULTILINE = re.compile(
        r"(?:^|\n)\s*(?:konu|subject)\s*:\s*(.+?)(?=\n\s*(?:sayı|sayi|tarih|ilgi|referans)\s*:|\n\s*\n|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    # Trailing-number extractor: from full sayı code take last /NUMBER or -NUMBER
    _SAYI_TRAILING = re.compile(r"[/\-]([0-9]+)\s*$")
    _PROJECT_NAME_PATTERNS = (
        re.compile(
            r"(?:proje\s*adı|proje\s*adi|proje\s*ismi|işin\s*adı|isin\s*adi)\s*[:\-]\s*(.+)",
            re.IGNORECASE,
        ),
        re.compile(r"(?:proje\s*konusu|konu)\s*[:\-]\s*(.+)", re.IGNORECASE),
    )
    _LETTER_SUBJECT_PATTERNS = (
        re.compile(r"(?:konu|subject)\s*[:\-]\s*(.+)", re.IGNORECASE),
        re.compile(r"(?:proje\s*konusu)\s*[:\-]\s*(.+)", re.IGNORECASE),
    )
    _LETTER_INSTITUTION_PATTERNS = (
        re.compile(
            r"(?:kurum|muhatap|alıcı|alici|gönderilen|gonderilen|hitap)\s*[:\-]\s*(.+)",
            re.IGNORECASE,
        ),
        re.compile(r"(?:sayın|sayin)\s*[:\-]?\s*(.+)", re.IGNORECASE),
    )
    _LETTER_SKIP_PATTERNS = (
        re.compile(r"^\d{2}\.\d{2}\.\d{4}$"),
        re.compile(r"^(?:konu|subject|sayı|sayi|evrak|tarih)\b", re.IGNORECASE),
        re.compile(r"^[0-9./ -]+$"),
    )

    # ── Contact / footer / address filter patterns ──────────────────────────
    # Lines matching any of these are NOT attachments.
    _CONTACT_PATTERNS = (
        re.compile(r"@"),                                                       # e-posta
        re.compile(r"www\.", re.IGNORECASE),                                     # web
        re.compile(r"\.(?:com|gov|org|net|edu|tr)\b", re.IGNORECASE),           # domain
        re.compile(r"\b(?:telefon|tel|faks|fax|belgegeçer|belgegecer)\s*[:\-]?\s*[\d\s\(\)\+]+", re.IGNORECASE),
        re.compile(r"\b(?:e[\-\s]?posta|e[\-\s]?mail)\s*[:\-]?", re.IGNORECASE),
        re.compile(r"\b(?:kep|kayıtlı\s*elektronik)\b", re.IGNORECASE),
        re.compile(r"\b(?:mah|mahalle)(?:[\.\s]|$)", re.IGNORECASE),
        re.compile(r"\b(?:cad|cadde)(?:[\.\s]|$)", re.IGNORECASE),
        re.compile(r"\b(?:sok|sokak)(?:[\.\s]|$)", re.IGNORECASE),
        re.compile(r"\b(?:apartman|apt|blok|daire|kat)\b", re.IGNORECASE),
        re.compile(r"\b(?:posta\s*(?:kodu|kodu)|pk)\s*[:\-]?\s*\d", re.IGNORECASE),
        re.compile(r"\b(?:adres|address)\s*[:\-]", re.IGNORECASE),
        re.compile(r"\b(?:internet|web)\s*(?:adresi|sayfası|sitesi)?\s*[:\-]?", re.IGNORECASE),
        re.compile(r"\b(?:bilgi\s*için|iletişim|irtibat)\b", re.IGNORECASE),
        re.compile(r"\b(?:sayfa\s*\d+|page\s*\d+)\b", re.IGNORECASE),
        re.compile(r"\b(?:elektronik\s*imza|e[\-\s]?imza)\b", re.IGNORECASE),
    )

    def __init__(self):
        self.logger = get_class_logger(self)
        self._fitz = None
        self._tesseract_backend = None
        self._tesseract_backend_checked = False
        self._pytesseract = None
        self._pil_image = None
        self._ocr_configured = False

    def analyze_project_document(self, file_path: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "kod": "",
            "isim": "",
            "revizyon": "",
            "yapim_isi": "",
            "source": "",
            "used_ocr": False,
            "source_note": "",
        }
        file_name = os.path.basename(file_path)

        filename_info = self._parse_project_filename(file_name)
        if filename_info.get("kod"):
            result["kod"] = filename_info["kod"]
        if filename_info.get("isim"):
            result["isim"] = filename_info["isim"]
        if result["kod"] or result["isim"]:
            result["source"] = "filename"
            result["source_note"] = "Proje bilgileri dosya adindan alindi."

        # Always scan document content for rich title-block fields
        extracted = self.extract_text(file_path, analysis_kind="project")
        text = extracted.get("text", "")
        if text:
            text_info = self.parse_project_text(text)
            if text_info.get("kod") and not result["kod"]:
                result["kod"] = text_info["kod"]
            if text_info.get("isim") and not result["isim"]:
                result["isim"] = text_info["isim"]
            if text_info.get("revizyon") and not result["revizyon"]:
                result["revizyon"] = text_info["revizyon"]
            if text_info.get("yapim_isi") and not result["yapim_isi"]:
                result["yapim_isi"] = text_info["yapim_isi"]
            if result["kod"] or result["isim"]:
                result["source"] = extracted.get("source", "text")
                result["used_ocr"] = bool(extracted.get("used_ocr"))
                result["source_note"] = self._describe_text_source(extracted)

        return result

    def analyze_letter_document(self, file_path: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "yazi_no": "",
            "yazi_tarih": "",
            "konu": "",
            "kurum": "",
            "aciklama": "",
            "ekler": "",
            "ilgi": "",
            "source": "",
            "used_ocr": False,
            "source_note": "",
        }
        file_name = os.path.basename(file_path)
        filename_info = dosyadan_tarih_sayi_cikar(file_name) or {}
        if filename_info.get("sayi"):
            result["yazi_no"] = filename_info["sayi"]
        if filename_info.get("tarih"):
            result["yazi_tarih"] = filename_info["tarih"]
        if result["yazi_no"] or result["yazi_tarih"]:
            result["source"] = "filename"
            result["source_note"] = "Yazi bilgileri dosya adindan alindi."

        extracted = self.extract_text(file_path, analysis_kind="letter")
        text = extracted.get("text", "")
        text_info = {}
        if text:
            text_info = self.parse_letter_text(text)
            
            # If text was from native PDF but failed to find yazi_no, force OCR
            if not extracted.get("used_ocr") and not text_info.get("yazi_no"):
                ocr_extracted = self.extract_text(file_path, analysis_kind="letter", force_ocr=True)
                ocr_text = ocr_extracted.get("text", "")
                if ocr_text:
                    ocr_info = self.parse_letter_text(ocr_text)
                    if ocr_info.get("yazi_no"):
                        text_info = ocr_info
                        extracted = ocr_extracted
                        text = ocr_text

        if text:
            if text_info.get("yazi_no") and not result["yazi_no"]:
                result["yazi_no"] = text_info["yazi_no"]
            if text_info.get("yazi_tarih") and not result["yazi_tarih"]:
                result["yazi_tarih"] = text_info["yazi_tarih"]
            if text_info.get("konu"):
                result["konu"] = text_info["konu"]
            if text_info.get("kurum"):
                result["kurum"] = text_info["kurum"]
            if text_info.get("aciklama"):
                result["aciklama"] = text_info["aciklama"]
            if text_info.get("ekler"):
                result["ekler"] = text_info["ekler"]
            if "ekler_listesi" in text_info:
                result["ekler_listesi"] = text_info["ekler_listesi"]
            if text_info.get("ilgi"):
                result["ilgi"] = text_info["ilgi"]
            if any(
                result.get(key)
                for key in ("yazi_no", "yazi_tarih", "konu", "kurum", "aciklama", "ekler", "ilgi")
            ):
                result["source"] = extracted.get("source", "text")
                result["used_ocr"] = bool(extracted.get("used_ocr"))
                result["source_note"] = self._describe_text_source(extracted)

        return result

    def parse_project_text(self, text: str) -> Dict[str, str]:
        """
        Smart title-block parser for engineering drawings.

        Typical pafta (drawing sheet) title block (bottom-right corner)::

            ┌──────────────────────────────────────────────┐
            │  BOUNDARY FENCE LAYOUT PLAN & GATE HOUSE DOOR │  ← document name
            ├───────────────────┬──────────────────────────┤
            │  Dok\u00fcman No:       │  0-NGTL 0-CS-C-001-1033  │  ← compound code
            ├───────────────────┼──────────────────────────┤
            │  Rev              │  A                        │  ← revision
            ├───────────────────┼──────────────────────────┤
            │  ... Yap\u0131m \u0130\u015fi      │                          │  ← contract name
            └──────────────────────────────────────────────┘

        Returns dict with keys: kod, isim, revizyon, yapim_isi
        """
        normalized = self._normalize_text(text)
        tb = self._parse_titleblock(normalized)

        # If title-block extraction failed, fall back to legacy regex
        if not tb.get("kod"):
            code_match = self._PROJECT_CODE_PATTERN.search(normalized)
            if code_match:
                tb["kod"] = code_match.group(1).strip()
        if not tb.get("isim"):
            tb["isim"] = self._extract_project_name(normalized, tb.get("kod", ""))

        return tb

    # ── Title-block parsing ──────────────────────────────────────────────────

    def _parse_titleblock(self, text: str) -> Dict[str, str]:
        """Extract all title-block fields from normalized drawing text."""
        lines = [ln.strip() for ln in text.splitlines()]
        non_empty = [ln for ln in lines if ln]

        kod = self._tb_extract_document_code(non_empty)
        isim = self._tb_extract_document_name(non_empty, kod)
        revizyon = self._tb_extract_revision(non_empty)
        yapim_isi = self._tb_extract_yapim_isi(non_empty)

        return {
            "kod": kod,
            "isim": isim,
            "revizyon": revizyon,
            "yapim_isi": yapim_isi,
        }

    def _tb_extract_document_code(self, lines: list) -> str:
        """
        Look for a 'Dok\u00fcman No:' label line and extract the code value that follows
        on the same line or the very next non-empty line.
        Handles compound codes like '0-NGTL 0-CS-C-001-1033'.
        """
        for idx, line in enumerate(lines):
            m = self._TB_DOKUMAN_NO.search(line)
            if m:
                candidate = m.group(1).strip()
                # If the value is on the same line after the label
                if candidate:
                    code = self._clean_doc_code(candidate)
                    if code:
                        return code
                # Otherwise look at the next line
                if idx + 1 < len(lines):
                    code = self._clean_doc_code(lines[idx + 1])
                    if code:
                        return code

        # Fallback: scan all lines for a code-shaped token
        for line in lines:
            cm = self._TB_DOC_CODE.search(line)
            if cm:
                code = self._clean_doc_code(cm.group(1))
                if code and len(code) >= 6:
                    return code
        return ""

    def _clean_doc_code(self, raw: str) -> str:
        """Normalise a raw document code candidate."""
        cleaned = raw.strip().upper()
        # Remove surrounding punctuation except hyphens and spaces
        cleaned = re.sub(r"^[^A-Z0-9]+", "", cleaned)
        cleaned = re.sub(r"[^A-Z0-9\- ]+$", "", cleaned)
        # A valid code must start with a digit and a hyphen
        if not re.match(r"\d[-\s]", cleaned):
            return ""
        # Must have at least one letter segment
        if not re.search(r"[A-Z]{2,}", cleaned):
            return ""
        return cleaned[:80]

    def _tb_extract_document_name(self, lines: list, code: str) -> str:
        """
        The document name sits ABOVE the 'Dok\u00fcman No' row.
        It is usually ALL-CAPS (or Title-Case), longer than 6 chars,
        and appears on the line immediately before the label.

        Strategy:
        1. Find the Dok\u00fcman No label line index.
        2. Walk upwards for the first line that looks like a title.
        3. If not found that way, look for an ALL-CAPS line with 3+ words.
        """
        dokno_idx = None
        for idx, line in enumerate(lines):
            if self._TB_DOKUMAN_NO.search(line):
                dokno_idx = idx
                break

        if dokno_idx is not None:
            # Search upward (up to 5 lines) and collect contiguous title lines
            title_parts = []
            for offset in range(1, min(6, dokno_idx + 1)):
                candidate = lines[dokno_idx - offset]
                if self._looks_like_document_title(candidate):
                    title_parts.append(candidate)
                elif title_parts:
                    # Found the top of the contiguous title block
                    break
            
            if title_parts:
                title_parts.reverse()
                combined = " ".join(title_parts)
                return self._clean_project_name(combined)

        # Fallback: first ALL-CAPS line with 3+ words and length >= 10
        for line in lines:
            if self._looks_like_document_title(line) and len(line.split()) >= 3:
                return self._clean_project_name(line)

        return ""

    def _looks_like_document_title(self, line: str) -> bool:
        """Heuristic: does this line look like a document title?"""
        s = line.strip()
        if len(s) < 6:
            return False
        # Reject pure numbers / dates / short codes
        if re.fullmatch(r"[0-9\s\./:,\-]+", s):
            return False
        # Reject single-word lines that look like labels
        words = s.split()
        if len(words) < 2:
            return False
            
        # Reject lines that are entirely common title-block labels
        common_labels = {"yapan", "kontrol", "onay", "tarih", "ölçek", "scale", "drawn", "checked", "approved", "designed", "rev", "revision", "imza", "signature", "checkedby", "designedby", "approvedby"}
        cleaned_words = [re.sub(r"[^a-zöçşığü]", "", w.lower()) for w in words]
        if all(cw in common_labels or not cw for cw in cleaned_words):
            return False

        # Should be mostly alphabetic (with common punctuation)
        alpha = sum(c.isalpha() for c in s)
        if alpha / max(len(s), 1) < 0.40:
            return False
        # Prefer ALL-CAPS or Title-Case (not mixed lowercase prose)
        upper_words = sum(1 for w in words if w.isupper() or (len(w) > 1 and w[0].isupper()))
        return upper_words >= max(1, len(words) // 2)

    def _tb_extract_revision(self, lines: list) -> str:
        """
        Find the revision code from the title-block revision table.
        Looks for a 'Rev' label followed by a 1-3 char alphanumeric value.
        Returns the most recent / highest revision found.
        """
        candidates = []
        for idx, line in enumerate(lines):
            m = self._TB_REV.search(line)
            if m:
                rev = m.group(1).strip().upper()
                if len(rev) <= 3 and rev not in ("NO", "ISI", "THE", "FOR", "REV"):
                    candidates.append(rev)
                    # Also check the next line if the value is on a separate cell
                    if idx + 1 < len(lines):
                        next_line = lines[idx + 1].strip()
                        if re.fullmatch(r"[A-Z0-9]{1,3}", next_line):
                            candidates.append(next_line)
        if not candidates:
            return ""
        # Return the latest revision (simple lexicographic sort gives A < B < ... < Z < 0 < 1...)
        return sorted(set(candidates))[-1]

    def _tb_extract_yapim_isi(self, lines: list) -> str:
        """Extract the construction contract name ending with 'yap\u0131m i\u015fi / yap\u0131m i\u015fleri'."""
        # Try full-line match first
        for line in lines:
            m = self._TB_YAPIM_ISI.search(line)
            if m:
                return self._clean_text_field(m.group(1), limit=240)
        # Try across joined consecutive lines (label might be on one line, value on next)
        for idx in range(len(lines) - 1):
            combined = lines[idx] + " " + lines[idx + 1]
            m = self._TB_YAPIM_ISI.search(combined)
            if m:
                return self._clean_text_field(m.group(1), limit=240)
        return ""

    def parse_letter_text(self, text: str) -> Dict[str, str]:
        normalized = self._normalize_text(text)
        # First 15 lines considered the header/title-block area
        header_lines = normalized.split("\n")[:15]
        header_text = "\n".join(header_lines)
        yazi_no = ""
        yazi_tarih = ""

        # ── Phase 1: Header-based extraction (most reliable for formal letters) ──
        # Sayı extraction from header
        sayi_m = self._HEADER_SAYI.search(header_text)
        if sayi_m:
            yazi_no = sayi_m.group(1).strip().upper()
        else:
            sayi_m2 = self._HEADER_SAYI_COMPOUND.search(header_text)
            if sayi_m2:
                raw = sayi_m2.group(1).strip()
                # Clean trailing punctuation/fragments
                raw = re.sub(r'[,;\s]+$', '', raw)
                yazi_no = raw.upper()
        # Normalize E- prefix in sayı codes (handle lower case e too)
        if yazi_no and not yazi_no.startswith("E-") and re.match(r"^E\d", yazi_no, re.IGNORECASE):
            yazi_no = "E-" + yazi_no[1:]

        # Tarih extraction from header
        tarih_m = self._HEADER_TARIH.search(header_text)
        if tarih_m:
            yazi_tarih = tarih_m.group(1)
            if yazi_tarih:
                yazi_tarih = yazi_tarih.replace("/", ".")

        # ── Phase 1b: "Evrak Tarih ve Sayısı: DD.MM.YYYY - NNN" format ──
        if not yazi_no:
            evrak_m = self._EVRAK_TARIH_SAYI.search(header_text)
            if evrak_m:
                evrak_tarih = evrak_m.group(1).replace("/", ".")
                evrak_sayi = evrak_m.group(2)
                if not yazi_tarih:
                    yazi_tarih = evrak_tarih
                yazi_no = evrak_sayi

        # ── Phase 2: Fallback to existing patterns if header didn't match ──
        if not yazi_no or not yazi_tarih:
            for pattern in self._LETTER_DATE_NO_PATTERNS:
                match = pattern.search(normalized)
                if not match:
                    continue
                if pattern is self._LETTER_DATE_NO_PATTERNS[0]:
                    if not yazi_tarih:
                        yazi_tarih = match.group(1)
                    if not yazi_no:
                        yazi_no = match.group(2)
                elif pattern is self._LETTER_DATE_NO_PATTERNS[1]:
                    full_code = match.group(1).strip()
                    if not yazi_no:
                        yazi_no = full_code
                    if not yazi_tarih:
                        date_m = re.search(r"(\d{2}\.\d{2}\.\d{4})", normalized[:600])
                        yazi_tarih = date_m.group(1) if date_m else ""
                else:
                    if not yazi_no:
                        yazi_no = match.group(1)
                    if not yazi_tarih:
                        yazi_tarih = match.group(2)
                if yazi_no and yazi_tarih:
                    break

        # ── Phase 3: Last-resort fallbacks ──
        if not yazi_no:
            sayi_m = re.search(
                r"(?:sayı|sayi|evrak\s*no|yazı\s*no|yazi\s*no)\s*[:\-]?\s*([A-Z0-9\xc7\u011e\u0130\xd6\u015e\xdc\.\-_/]+)",
                normalized,
                re.IGNORECASE
            )
            if sayi_m:
                full_code = sayi_m.group(1).strip()
                yazi_no = re.sub(r'[\s\.\-_/]+$', '', full_code)
                
        if not yazi_tarih:
            date_m = re.search(r"(\d{2}[\./]\d{2}[\./]\d{4})", normalized[:1000])
            if date_m:
                yazi_tarih = date_m.group(1)
                
        # Standardize slashes to dots in date
        if yazi_tarih:
            yazi_tarih = yazi_tarih.replace("/", ".")

        konu = self._extract_letter_subject(normalized)
        if not konu:
            # Try header-specific multiline subject extraction
            konu_m = self._HEADER_KONU_MULTILINE.search(header_text)
            if konu_m:
                konu = self._clean_text_field(konu_m.group(1), limit=400)
        if not konu:
            # Try single-line subject from header
            konu_m2 = self._HEADER_KONU_SINGLE.search(header_text)
            if konu_m2:
                konu = self._clean_text_field(konu_m2.group(1), limit=400)

        kurum = self._extract_letter_institution(normalized, konu)
        aciklama = self._build_letter_description(normalized, konu, kurum)
        ekler_listesi = self._extract_letter_attachments_structured(normalized)
        ilgi = self._extract_letter_references(normalized)

        # Backward-compat string (pipe-joined raw text)
        ekler_str = " | ".join(
            e.get("ham_metin", "") for e in ekler_listesi if e.get("ham_metin")
        )

        return {
            "yazi_no": (yazi_no or "").strip(),
            "yazi_tarih": (yazi_tarih or "").strip(),
            "konu": konu,
            "kurum": kurum,
            "aciklama": aciklama,
            "ekler": ekler_str,
            "ekler_listesi": ekler_listesi,
            "ilgi": ilgi,
        }


    def extract_text(self, file_path: str, max_pages: int = 3, analysis_kind: str = "generic", force_ocr: bool = False) -> Dict[str, Any]:
        """
        Extracts text from a file (PDF or Image).
        Returns:
            Dict: {"text": "...", "source": "pdf_text"|"pdf_tesseract"|"image_ocr", "used_ocr": bool}
        """
        extension = os.path.splitext(file_path)[1].lower()
        if extension == ".pdf":
            return self._extract_text_from_pdf(
                file_path,
                max_pages=max_pages,
                analysis_kind=analysis_kind,
                force_ocr=force_ocr,
            )
        if extension in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
            return self._extract_text_from_image(file_path, analysis_kind=analysis_kind)
        return {"text": "", "source": "", "used_ocr": False}

    def is_ocr_available(self) -> bool:
        return self._get_tesseract_backend() is not None or self._is_pytesseract_available()

    def _parse_project_filename(self, file_name: str) -> Dict[str, str]:
        info = dosyadan_proje_bilgisi_cikar(file_name) or {}
        if info.get("kod") or info.get("isim"):
            return info

        stem = os.path.splitext(file_name)[0]
        match = self._PROJECT_FILENAME_PATTERN.search(stem)
        if not match:
            return {"kod": "", "isim": ""}
        return {
            "kod": match.group(1).strip(),
            "isim": self._clean_project_name(match.group(2)),
        }

    def _extract_text_from_pdf(
        self,
        file_path: str,
        max_pages: int = 3,
        analysis_kind: str = "generic",
        force_ocr: bool = False,
    ) -> Dict[str, Any]:
        fitz = self._load_fitz()
        if fitz is None:
            return {"text": "", "source": "", "used_ocr": False}

        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            self.logger.warning("PDF acilamadi (%s): %s", file_path, exc)
            return {"text": "", "source": "", "used_ocr": False}

        try:
            chunks = []
            if not force_ocr:
                for page_index in range(min(max_pages, doc.page_count)):
                    page = doc.load_page(page_index)
                    page_text = self._extract_pdf_page_text(page, analysis_kind=analysis_kind)
                    if page_text.strip():
                        chunks.append(page_text)
                combined = "\n".join(chunks).strip()
                
                # Taranmış PDF'lerde fitz get_text() boş veya çok az çöp karakter döndürebilir.
                # Metnin gerçekten dijital olduğunu doğrulamak için yeterince harf/rakam içerdiğine bakıyoruz.
                alphanumeric_count = sum(c.isalnum() for c in combined)
                if alphanumeric_count >= 15:
                    return {"text": combined, "source": "pdf_text", "used_ocr": False}

            tesseract_chunks = []
            for page_index in range(min(max_pages, doc.page_count)):
                page = doc.load_page(page_index)
                text = self._ocr_pdf_page(page, analysis_kind=analysis_kind)
                if text.strip():
                    tesseract_chunks.append(text)
            if tesseract_chunks:
                return {
                    "text": "\n".join(tesseract_chunks).strip(),
                    "source": "pdf_tesseract",
                    "used_ocr": True,
                }

            if not self._is_pytesseract_available():
                return {"text": "", "source": "", "used_ocr": False}

            ocr_chunks = []
            for page_index in range(min(max_pages, doc.page_count)):
                page = doc.load_page(page_index)
                text = self._ocr_pdf_page_with_pytesseract(
                    page, analysis_kind=analysis_kind
                )
                if text.strip():
                    ocr_chunks.append(text)
            return {
                "text": "\n".join(ocr_chunks).strip(),
                "source": "pdf_ocr",
                "used_ocr": bool(ocr_chunks),
            }
        finally:
            try:
                doc.close()
            except Exception:
                pass

    def _extract_text_from_image(
        self,
        file_path: str,
        analysis_kind: str = "generic",
    ) -> Dict[str, Any]:
        backend = self._get_tesseract_backend()
        if backend is not None:
            try:
                return {
                    "text": self._ocr_image_path_with_tesseract(
                        file_path, analysis_kind=analysis_kind
                    ),
                    "source": "image_tesseract",
                    "used_ocr": True,
                }
            except Exception as exc:
                self.logger.warning("Tesseract OCR basarisiz (%s): %s", file_path, exc)

        if not self._is_pytesseract_available():
            return {"text": "", "source": "", "used_ocr": False}

        try:
            with self._pil_image.open(file_path) as image:
                if analysis_kind == "project":
                    # We might need to copy the cropped region if we are returning it,
                    # but _ocr_image reads the image immediately.
                    processed_image = self._crop_project_image_region(image)
                else:
                    processed_image = image
                
                return {
                    "text": self._ocr_image(processed_image),
                    "source": "image_ocr",
                    "used_ocr": True,
                }
        except Exception as exc:
            self.logger.warning("Resim OCR basarisiz (%s): %s", file_path, exc)
            return {"text": "", "source": "", "used_ocr": False}

    def _ocr_pdf_page(self, page, analysis_kind: str = "generic") -> str:
        backend = self._get_tesseract_backend()
        if backend is None:
            return ""

        try:
            pixmap = self._render_pdf_page_to_pixmap(page, analysis_kind=analysis_kind)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as handle:
                temp_path = handle.name
            pixmap.save(temp_path)
            try:
                return backend.run_ocr(temp_path)
            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
        except Exception as exc:
            self.logger.debug("PDF OCR sayfa donusturmesi basarisiz: %s", exc)
            return ""

    def _ocr_pdf_page_with_pytesseract(self, page, analysis_kind: str = "generic") -> str:
        self._configure_ocr_runtime()
        if self._pytesseract is None or self._pil_image is None:
            return ""

        try:
            pixmap = self._render_pdf_page_to_pixmap(page, analysis_kind=analysis_kind)
            image = self._pil_image.open(io.BytesIO(pixmap.tobytes("png")))
            return self._ocr_image(image)
        except Exception as exc:
            self.logger.debug("PDF OCR sayfa donusturmesi basarisiz: %s", exc)
            return ""

    def _ocr_image(self, image) -> str:
        self._configure_ocr_runtime()
        if self._pytesseract is None:
            return ""
        try:
            return self._pytesseract.image_to_string(image, lang="tur+eng")
        except Exception:
            try:
                return self._pytesseract.image_to_string(image, lang="eng")
            except Exception as exc:
                self.logger.debug("OCR okunamadi: %s", exc)
                return ""

    def _configure_ocr_runtime(self) -> None:
        if self._ocr_configured:
            return
        self._ocr_configured = True

        try:
            import pytesseract

            self._pytesseract = pytesseract
        except Exception:
            self._pytesseract = None
            return

        try:
            from PIL import Image

            self._pil_image = Image
        except Exception:
            self._pil_image = None
            self._pytesseract = None
            return

        tess_cmd = os.environ.get("TESSERACT_CMD", "").strip()
        if not tess_cmd and os.name == "nt":
            candidates = (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            )
            for candidate in candidates:
                if os.path.exists(candidate):
                    tess_cmd = candidate
                    break

        if tess_cmd:
            try:
                self._pytesseract.pytesseract.tesseract_cmd = tess_cmd
            except Exception as exc:
                self.logger.debug("Tesseract yolu atanamadi: %s", exc)

    def _is_pytesseract_available(self) -> bool:
        self._configure_ocr_runtime()
        return self._pytesseract is not None and self._pil_image is not None

    def _get_tesseract_backend(self):
        if self._tesseract_backend_checked:
            return self._tesseract_backend

        self._tesseract_backend_checked = True
        try:
            self._tesseract_backend = TesseractBackend.discover()
            if self._tesseract_backend is not None:
                runtime = self._tesseract_backend.runtime_info
                self.logger.info(
                    "Tesseract runtime bulundu (%s, langs=%s, source=%s)",
                    runtime.executable_path,
                    "+".join(runtime.languages),
                    runtime.source,
                )
        except Exception as exc:
            self.logger.warning("Tesseract runtime kesfi basarisiz: %s", exc)
            self._tesseract_backend = None
        return self._tesseract_backend

    def _load_fitz(self):
        if self._fitz is not None:
            return self._fitz
        try:
            import fitz

            self._fitz = fitz
            return self._fitz
        except Exception as exc:
            self.logger.warning("PyMuPDF yuklenemedi: %s", exc)
            self._fitz = None
            return None

    def _extract_project_name(self, text: str, project_code: str) -> str:
        for pattern in self._PROJECT_NAME_PATTERNS:
            match = pattern.search(text)
            if match:
                cleaned = self._clean_project_name(match.group(1))
                if cleaned:
                    return cleaned

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if project_code:
            for index, line in enumerate(lines):
                if project_code.casefold() in line.casefold():
                    remainder = line.replace(project_code, " ").strip(" -:\t")
                    cleaned_remainder = self._clean_project_name(remainder)
                    if cleaned_remainder:
                        return cleaned_remainder
                    if index + 1 < len(lines):
                        cleaned_next = self._clean_project_name(lines[index + 1])
                        if cleaned_next:
                            return cleaned_next

        return ""

    def _extract_letter_subject(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for pattern in self._LETTER_SUBJECT_PATTERNS:
            match = pattern.search(text)
            if match:
                raw = match.group(1).strip()
                # If the subject is very short, try to capture next line too
                if len(raw) < 20:
                    m_start = match.end()
                    remaining = text[m_start:].lstrip()
                    next_line_end = remaining.find('\n')
                    if next_line_end > 0 and next_line_end < 200:
                        continuation = remaining[:next_line_end].strip()
                        if continuation and len(continuation) > 3:
                            raw = f"{raw} {continuation}"
                cleaned = self._clean_text_field(raw, limit=400)
                if cleaned:
                    return cleaned

        for line in lines[:12]:
            folded = line.casefold()
            if " hakkında" in folded or " hakkinda" in folded:
                cleaned = self._clean_text_field(line, limit=400)
                if cleaned:
                    return cleaned
        return ""

    # ── Structured attachment extraction ─────────────────────────────────────
    # Regex to strip leading ek-number prefix: "1-", "1)", "1.", "Ek 2:", etc.
    _EK_PREFIX = re.compile(
        r"^(?:ek(?:\s*[-.:])\s*\d+\s*[:.-]?\s*|\d+\s*[)./-]\s*|[a-z][).:]\s*)",
        re.IGNORECASE,
    )
    # Revision at end of ek line: "Rev A", "Rev.B", "R-C"
    _EK_REV = re.compile(r"\brev(?:izyon)?[\s.:\-]*([A-Z0-9]{1,3})\s*$", re.IGNORECASE)
    # Document-code token anywhere in ek line (compound space-separated codes supported)
    _EK_CODE = re.compile(
        r"(\d[-][A-Z][A-Z0-9\-]+(?:\s+\d[-][A-Z][A-Z0-9\-]+)*|\d[-][A-Z0-9\-]{3,})",
        re.IGNORECASE,
    )

    def _is_contact_info(self, line: str) -> bool:
        """Bir satırın iletişim/temas bilgisi olup olmadığını kontrol et."""
        for pattern in self._CONTACT_PATTERNS:
            if pattern.search(line):
                return True
        return False

    def _extract_letter_attachments_structured(self, text: str) -> list:
        """
        Parse the Ek / Ekler section of a letter into a structured list.

        Each entry is a dict::

            {
                "sira":     int,   # 1-based attachment order
                "ham_metin": str,  # raw text after stripping ek prefix
                "kod":      str,   # document code if found
                "ad":       str,   # document name (text minus code/rev)
                "revizyon": str,   # revision code if found
            }

        Attachment numbers (1-, 2), Ek-1:, etc.) are discarded per requirements.
        """
        lines = text.splitlines()
        raw_ekler: list = []
        in_ekler = False

        for line in lines:
            ls = line.strip()
            if not ls:
                continue
            lower = ls.casefold()

            # Detect section header (only when not already inside ekler)
            if not in_ekler and re.match(r"^(?:ek|ekler)[\s:;\-]", lower):
                in_ekler = True
                # Content after the colon on the same line
                after = ls.split(":", 1)[1].strip() if ":" in ls else ""
                if after and not self._is_contact_info(after):
                    raw_ekler.append(after)
                continue

            if in_ekler:
                # Stop section on known other headers
                # Handles both Turkish dotted/dotless I via explicit alternation
                if re.match(
                    r"^(?:ilgi|referans|da[ğg]it[iıİ]m|da[ğg][ıiİ]t[ıiİ]m|DAĞITIM|konu|say[ıiİ]|sayi|imza|bilgi|not)\s*[:;]",
                    ls,  # use original (not casefolded) for Turkish uppercase matching
                ):
                    break

                # Skip contact / footer boilerplate lines using regex patterns
                if self._is_contact_info(ls):
                    continue

                # Skip lines matching legacy keyword filter (backward compat)
                if any(word in lower for word in ["elektronik imza", "adres", "sayfa"]):
                    continue
                    
                # Over-indented (signature block) — stop
                if len(line) - len(line.lstrip()) > 20:
                    break
                if len(ls) >= 3:
                    raw_ekler.append(ls)

        # Parse each raw line
        result = []
        sira = 0
        for raw in raw_ekler:
            # Strip leading ek-number prefix
            cleaned = self._EK_PREFIX.sub("", raw).strip()
            if not cleaned or len(cleaned) < 3:
                continue
            # Skip lines that are too short and have no digit or code-like content
            if len(cleaned) < 5 and not re.search(r"[0-9]", cleaned):
                continue
            sira += 1

            # Extract document code
            kod = ""
            kod_m = self._EK_CODE.search(cleaned)
            rev = ""
            
            if kod_m:
                kod = kod_m.group(1).strip().upper()
                after_code = cleaned[kod_m.end():]
                # Look for a standalone 1-3 char token that might be revision (e.g. " - P0 - ")
                rev_m = re.search(r"(?:[-_/\s]|^)(?:rev(?:izyon)?[\s.:\-]*|)([A-Z0-9]{1,3})(?:[-_/\s]|$)", after_code, re.IGNORECASE)
                if rev_m:
                    rev = rev_m.group(1).upper()
                    # Remove the revision part from the name
                    ad_after = after_code[:rev_m.start()] + after_code[rev_m.end():]
                    ad = (cleaned[:kod_m.start()] + ad_after).strip()
                else:
                    ad = (cleaned[:kod_m.start()] + after_code).strip()
            else:
                ad = cleaned
                # Fallback to ending revision
                rev_m = self._EK_REV.search(ad)
                if rev_m:
                    rev = rev_m.group(1).upper()
                    ad = ad[:rev_m.start()].strip()

            # Clean up name
            ad = re.sub(r"[\-_]+$", "", ad).strip()
            ad = re.sub(r"^[\s\-_]+", "", ad).strip()
            # If name is completely wrapped in parentheses, remove them
            if ad.startswith("(") and ad.endswith(")"):
                ad = ad[1:-1].strip()

            result.append({
                "sira": sira,
                "ham_metin": raw,
                "kod": kod,
                "ad": ad,
                "revizyon": rev,
            })

        return result

    def _extract_letter_attachments(self, text: str) -> str:
        """Backward-compat string form (pipe-joined ham_metin)."""
        structured = self._extract_letter_attachments_structured(text)
        return " | ".join(e["ham_metin"] for e in structured)

    def _extract_letter_references(self, text: str) -> str:
        lines = text.splitlines()
        ilgi = []
        in_ilgi = False
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue
            lower_line = line_strip.casefold()
            if lower_line.startswith("ilgi:") or lower_line.startswith("referans:"):
                in_ilgi = True
                content = line_strip.split(":", 1)[1].strip()
                if content:
                    ilgi.append(content)
                continue
            
            if in_ilgi:
                if lower_line.startswith(("ek:", "ekler:", "dağıtım:", "dagitim:", "konu:", "sayı:", "sayi:")):
                    break
                if len(line) - len(line.lstrip()) > 20:
                    break
                if len(line_strip) < 3:
                    continue
                ilgi.append(line_strip)
                
        return self._clean_text_field(" | ".join(ilgi), limit=1000)

    def _extract_letter_institution(self, text: str, konu: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for pattern in self._LETTER_INSTITUTION_PATTERNS:
            match = pattern.search(text)
            if match:
                cleaned = self._clean_text_field(match.group(1), limit=180)
                if cleaned:
                    return cleaned

        for line in lines[:12]:
            if konu and line.casefold() == konu.casefold():
                continue
            alpha_chars = sum(1 for ch in line if ch.isalpha())
            if alpha_chars == 0:
                continue
            upper_ratio = sum(1 for ch in line if ch.isupper()) / alpha_chars
            if (
                len(line) >= 8
                and upper_ratio >= 0.65
                and not self._line_looks_like_letter_noise(line)
            ):
                return self._clean_text_field(line, limit=180)
        return ""

    def _build_letter_description(self, text: str, konu: str, kurum: str) -> str:
        if konu and kurum:
            return self._clean_text_field(f"{kurum} - {konu}", limit=240)
        if konu:
            return self._clean_text_field(konu, limit=240)

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        informative = []
        for line in lines[:18]:
            if self._line_looks_like_letter_noise(line):
                continue
            informative.append(self._clean_text_field(line, limit=240))
            if len(informative) == 2:
                break
        return self._clean_text_field(" / ".join(informative), limit=240)

    def _extract_pdf_page_text(self, page, analysis_kind: str = "generic") -> str:
        if analysis_kind != "project":
            return page.get_text("text") or ""

        blocks = page.get_text("blocks") or []
        if not blocks:
            return page.get_text("text") or ""

        width = float(page.rect.width)
        height = float(page.rect.height)
        preferred = []
        fallback = []
        for block in blocks:
            try:
                x0, y0, _x1, _y1, text = block[:5]
            except Exception:
                continue
            cleaned = self._normalize_text(text or "").strip()
            if not cleaned:
                continue
            if x0 >= width * 0.42 and y0 >= height * 0.42:
                preferred.append(cleaned)
            else:
                fallback.append(cleaned)
        return "\n".join(preferred + fallback).strip()

    def _render_pdf_page_to_pixmap(self, page, analysis_kind: str = "generic"):
        fitz = self._load_fitz()
        clip = None
        if analysis_kind == "project":
            clip = self._get_project_pdf_clip(page)
        return page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False, clip=clip)

    def _get_project_pdf_clip(self, page):
        rect = page.rect
        width = float(rect.width)
        height = float(rect.height)
        return self._load_fitz().Rect(
            rect.x0 + width * 0.42,
            rect.y0 + height * 0.42,
            rect.x1,
            rect.y1,
        )

    def _ocr_image_path_with_tesseract(
        self,
        file_path: str,
        analysis_kind: str = "generic",
    ) -> str:
        backend = self._get_tesseract_backend()
        if backend is None:
            return ""
        if analysis_kind != "project":
            return backend.run_ocr(file_path)

        self._configure_ocr_runtime()
        if self._pil_image is None:
            return backend.run_ocr(file_path)

        try:
            image = self._pil_image.open(file_path)
            cropped = self._crop_project_image_region(image)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as handle:
                temp_path = handle.name
            try:
                cropped.save(temp_path)
                return backend.run_ocr(temp_path)
            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
        except Exception:
            return backend.run_ocr(file_path)

    def _crop_project_image_region(self, image):
        width, height = image.size
        left = int(width * 0.42)
        top = int(height * 0.42)
        return image.crop((left, top, width, height))

    def _clean_project_name(self, value: Optional[str]) -> str:
        cleaned = (value or "").replace("_", " ").strip()
        cleaned = re.split(r"[|;]", cleaned, maxsplit=1)[0].strip()
        cleaned = re.sub(r"^(?:Proje\s*(?:Adı|Adi|İsmi|Ismi|Ad|İsim)\s*[:\-]*\s*)", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned[:160]

    def _clean_text_field(self, value: Optional[str], limit: int = 160) -> str:
        cleaned = (value or "").replace("_", " ").strip(" -:\t")
        cleaned = re.split(r"[|;]", cleaned, maxsplit=1)[0].strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned[:limit]

    def _line_looks_like_letter_noise(self, line: str) -> bool:
        normalized = self._clean_text_field(line, limit=240)
        if not normalized:
            return True
        for pattern in self._LETTER_SKIP_PATTERNS:
            if pattern.search(normalized):
                return True
        return len(normalized) < 4

    def _normalize_text(self, text: str) -> str:
        normalized = text.replace("\r", "\n")
        normalized = normalized.replace("\x00", " ")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized

    def _describe_text_source(self, extracted: Dict[str, Any]) -> str:
        source = extracted.get("source")
        if source == "pdf_text":
            return "Bilgiler PDF icindeki metinden alindi."
        if source == "pdf_tesseract":
            return "Bilgiler Tesseract OCR ile PDF sayfasindan alindi."
        if source == "pdf_ocr":
            return "Bilgiler PDF OCR ile alindi."
        if source == "image_tesseract":
            return "Bilgiler Tesseract OCR ile gorselden alindi."
        if source == "image_ocr":
            return "Bilgiler gorsel OCR ile alindi."
        return "Bilgiler belgeden alindi."
