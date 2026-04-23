from pathlib import Path

from i18n import repair_legacy_text


REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_PARTS = {".git", ".venv", "build", "dist", "release", "Archive", "__pycache__"}
BAD_CODEPOINTS = {0x00C2, 0x00C3, 0x00C4, 0x00C5}


def _iter_project_python_files():
    for path in REPO_ROOT.rglob("*.py"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        yield path


def _text_without_allowed_mojibake_examples(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.name != "i18n.py":
        return text

    start_marker = "_MOJIBAKE_REPLACEMENTS = ("
    end_marker = "\n\n_EN_TRANSLATIONS = {"
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1:
        return text
    return text[:start] + text[end:]


def test_project_sources_do_not_contain_legacy_mojibake_sequences():
    offending = []

    for path in _iter_project_python_files():
        text = _text_without_allowed_mojibake_examples(path)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(ord(ch) in BAD_CODEPOINTS for ch in line):
                offending.append(f"{path.relative_to(REPO_ROOT)}:{lineno}:{line}")

    assert offending == []


def test_login_dialog_uses_real_turkish_characters():
    text = (REPO_ROOT / "dialogs" / "login_dialog.py").read_text(encoding="utf-8")

    assert "Giriş" in text
    assert "Kullanıcı" in text
    assert "Şifre" in text
    assert "Lütfen" in text
    assert "Giris" not in text
    assert "Kullanici" not in text
    assert "Sifre" not in text
    assert "Lutfen" not in text


def test_repair_legacy_text_still_covers_common_mojibake_fallbacks():
    assert repair_legacy_text("Giri\u00c5\u0178") == "Giriş"
    assert repair_legacy_text("Kullan\u00c4\u00b1c\u00c4\u00b1") == "Kullanıcı"
    assert repair_legacy_text("Ba\u00c5\u0178ar\u00c4\u00b1l\u00c4\u00b1") == "Başarılı"
