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
    _PROJECT_CODE_PATTERN = re.compile(
        r"\b([0-4]-[A-Z0-9ÇĞİÖŞÜ]+(?:-[A-Z0-9ÇĞİÖŞÜ]+)*-\d{4})\b",
        re.IGNORECASE,
    )
    _LETTER_DATE_NO_PATTERNS = (
        re.compile(
            r"(\d{2}\.\d{2}\.\d{4})\s*(?:tarih(?:li)?\s*(?:ve)?\s*)?([0-9]{1,12})\s*(?:sayılı|sayili|no'?lu|nolu)?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:sayı|sayi|evrak\s*no|yazı\s*no|yazi\s*no)\s*[:\-]?\s*([0-9]{1,12}).{0,80}?(\d{2}\.\d{2}\.\d{4})",
            re.IGNORECASE | re.DOTALL,
        ),
    )
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

        if result["kod"] and result["isim"]:
            return result

        extracted = self.extract_text(file_path, analysis_kind="project")
        text = extracted.get("text", "")
        if text:
            text_info = self.parse_project_text(text)
            if text_info.get("kod") and not result["kod"]:
                result["kod"] = text_info["kod"]
            if text_info.get("isim") and not result["isim"]:
                result["isim"] = text_info["isim"]
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
        if text:
            text_info = self.parse_letter_text(text)
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
            if any(
                result.get(key)
                for key in ("yazi_no", "yazi_tarih", "konu", "kurum", "aciklama")
            ):
                result["source"] = extracted.get("source", "text")
                result["used_ocr"] = bool(extracted.get("used_ocr"))
                result["source_note"] = self._describe_text_source(extracted)

        return result

    def parse_project_text(self, text: str) -> Dict[str, str]:
        normalized = self._normalize_text(text)
        code_match = self._PROJECT_CODE_PATTERN.search(normalized)
        project_code = code_match.group(1).strip() if code_match else ""
        project_name = self._extract_project_name(normalized, project_code)
        return {"kod": project_code, "isim": project_name}

    def parse_letter_text(self, text: str) -> Dict[str, str]:
        normalized = self._normalize_text(text)
        yazi_no = ""
        yazi_tarih = ""
        for pattern in self._LETTER_DATE_NO_PATTERNS:
            match = pattern.search(normalized)
            if not match:
                continue
            if pattern is self._LETTER_DATE_NO_PATTERNS[0]:
                yazi_tarih, yazi_no = match.group(1), match.group(2)
            else:
                yazi_no, yazi_tarih = match.group(1), match.group(2)
            break

        konu = self._extract_letter_subject(normalized)
        kurum = self._extract_letter_institution(normalized, konu)
        aciklama = self._build_letter_description(normalized, konu, kurum)
        return {
            "yazi_no": (yazi_no or "").strip(),
            "yazi_tarih": (yazi_tarih or "").strip(),
            "konu": konu,
            "kurum": kurum,
            "aciklama": aciklama,
        }

    def extract_text(
        self,
        file_path: str,
        max_pages: int = 3,
        analysis_kind: str = "generic",
    ) -> Dict[str, Any]:
        extension = os.path.splitext(file_path)[1].lower()
        if extension == ".pdf":
            return self._extract_text_from_pdf(
                file_path,
                max_pages=max_pages,
                analysis_kind=analysis_kind,
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
            for page_index in range(min(max_pages, doc.page_count)):
                page = doc.load_page(page_index)
                page_text = self._extract_pdf_page_text(page, analysis_kind=analysis_kind)
                if page_text.strip():
                    chunks.append(page_text)
            combined = "\n".join(chunks).strip()
            if combined:
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
            image = self._pil_image.open(file_path)
            if analysis_kind == "project":
                image = self._crop_project_image_region(image)
            return {
                "text": self._ocr_image(image),
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
                cleaned = self._clean_text_field(match.group(1), limit=220)
                if cleaned:
                    return cleaned

        for line in lines[:12]:
            folded = line.casefold()
            if " hakkında" in folded or " hakkinda" in folded:
                cleaned = self._clean_text_field(line, limit=220)
                if cleaned:
                    return cleaned
        return ""

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
