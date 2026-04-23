import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from app_paths import get_app_base_dir, get_bundle_dir, get_internal_path, get_resource_path
from utils import get_class_logger


@dataclass
class TesseractRuntimeInfo:
    executable_path: str
    tessdata_dir: Optional[str]
    languages: List[str]
    source: str


class TesseractBackend:
    """Minimal CLI wrapper around a local Tesseract runtime."""

    def __init__(self, runtime_info: TesseractRuntimeInfo):
        self.runtime_info = runtime_info
        self.logger = get_class_logger(self)

    @classmethod
    def discover(cls) -> Optional["TesseractBackend"]:
        for candidate_path, source in cls._iter_executable_candidates():
            if not candidate_path or not os.path.isfile(candidate_path):
                continue

            tessdata_dir = cls._discover_tessdata_dir(candidate_path)
            languages = cls._detect_languages(candidate_path, tessdata_dir)
            if not languages:
                continue

            return cls(
                TesseractRuntimeInfo(
                    executable_path=os.path.abspath(candidate_path),
                    tessdata_dir=tessdata_dir,
                    languages=languages,
                    source=source,
                )
            )
        return None

    def is_available(self) -> bool:
        return os.path.isfile(self.runtime_info.executable_path) and bool(
            self.runtime_info.languages
        )

    def run_ocr(
        self,
        image_path: str,
        *,
        page_seg_mode: int = 6,
        timeout_sec: int = 30,
    ) -> str:
        command = [
            self.runtime_info.executable_path,
            image_path,
            "stdout",
            "--oem",
            "1",
            "--psm",
            str(page_seg_mode),
            "-l",
            "+".join(self.runtime_info.languages),
            "quiet",
        ]
        if self.runtime_info.tessdata_dir:
            command.extend(["--tessdata-dir", self.runtime_info.tessdata_dir])

        env = os.environ.copy()
        if self.runtime_info.tessdata_dir:
            env.setdefault("TESSDATA_PREFIX", self.runtime_info.tessdata_dir)

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            env=env,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(stderr or f"Tesseract exited with code {result.returncode}")
        return (result.stdout or "").strip()

    @staticmethod
    def _iter_executable_candidates():
        explicit = os.environ.get("TESSERACT_CMD", "").strip()
        on_path = shutil.which("tesseract")
        candidates = [
            (explicit, "env:TESSERACT_CMD"),
            (on_path, "system:PATH"),
            (
                get_internal_path("ocr", "tesseract", "tesseract.exe"),
                "bundle:ocr/tesseract",
            ),
            (
                get_resource_path("ocr", "tesseract", "tesseract.exe"),
                "resource:ocr/tesseract",
            ),
            (
                os.path.join(get_app_base_dir(), "tesseract", "tesseract.exe"),
                "resource:tesseract",
            ),
            (
                os.path.join(
                    os.path.dirname(get_app_base_dir()),
                    "tesseract-runtime",
                    "tesseract.exe",
                ),
                "workspace:tesseract-runtime",
            ),
            (
                os.path.join(
                    os.path.dirname(get_app_base_dir()),
                    "tesseract-5.5.2",
                    "bin",
                    "tesseract.exe",
                ),
                "workspace:tesseract-5.5.2/bin",
            ),
            (r"C:\Program Files\Tesseract-OCR\tesseract.exe", "system:ProgramFiles"),
            (
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                "system:ProgramFiles(x86)",
            ),
        ]

        seen = set()
        for candidate_path, source in candidates:
            if not candidate_path:
                continue
            normalized = os.path.abspath(candidate_path)
            if normalized in seen:
                continue
            seen.add(normalized)
            yield normalized, source

    @staticmethod
    def _discover_tessdata_dir(executable_path: str) -> Optional[str]:
        candidates = []
        explicit = os.environ.get("TESSDATA_PREFIX", "").strip()
        if explicit:
            candidates.append(explicit)
            candidates.append(os.path.join(explicit, "tessdata"))

        exe_dir = os.path.dirname(executable_path)
        app_base = get_app_base_dir()
        bundle_dir = get_bundle_dir()
        workspace_root = os.path.dirname(app_base)
        candidates.extend(
            [
                os.path.join(exe_dir, "tessdata"),
                os.path.join(os.path.dirname(exe_dir), "tessdata"),
                get_internal_path("ocr", "tesseract", "tessdata"),
                get_resource_path("ocr", "tesseract", "tessdata"),
                os.path.join(app_base, "ocr", "tesseract", "tessdata"),
                os.path.join(bundle_dir, "ocr", "tesseract", "tessdata"),
                os.path.join(workspace_root, "tesseract-runtime", "tessdata"),
                os.path.join(workspace_root, "tesseract-5.5.2", "tessdata"),
            ]
        )

        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            normalized = os.path.abspath(candidate)
            if normalized in seen:
                continue
            seen.add(normalized)
            if os.path.isdir(normalized):
                return normalized
        return None

    @staticmethod
    def _detect_languages(executable_path: str, tessdata_dir: Optional[str]) -> List[str]:
        available = []
        if tessdata_dir:
            for lang in ("tur", "eng"):
                if os.path.isfile(os.path.join(tessdata_dir, f"{lang}.traineddata")):
                    available.append(lang)
        if available:
            return available

        env = os.environ.copy()
        if tessdata_dir:
            env.setdefault("TESSDATA_PREFIX", tessdata_dir)

        try:
            result = subprocess.run(
                [executable_path, "--list-langs"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                env=env,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            return []

        if result.returncode != 0:
            return []

        detected = []
        for line in (result.stdout or "").splitlines():
            normalized = line.strip().lower()
            if normalized in {"tur", "eng"} and normalized not in detected:
                detected.append(normalized)
        return detected
