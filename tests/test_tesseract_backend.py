from pathlib import Path
from types import SimpleNamespace

import services.tesseract_backend as tesseract_backend_module
from services.tesseract_backend import TesseractBackend, TesseractRuntimeInfo


def test_discover_uses_env_runtime_and_tessdata(monkeypatch, tmp_path):
    exe_path = tmp_path / "tesseract.exe"
    exe_path.write_bytes(b"")
    tessdata_dir = tmp_path / "tessdata"
    tessdata_dir.mkdir()
    (tessdata_dir / "tur.traineddata").write_bytes(b"")
    (tessdata_dir / "eng.traineddata").write_bytes(b"")

    monkeypatch.setenv("TESSERACT_CMD", str(exe_path))
    monkeypatch.setenv("TESSDATA_PREFIX", str(tessdata_dir))

    backend = TesseractBackend.discover()

    assert backend is not None
    assert backend.runtime_info.executable_path == str(exe_path.resolve())
    assert backend.runtime_info.tessdata_dir == str(tessdata_dir.resolve())
    assert backend.runtime_info.languages == ["tur", "eng"]
    assert backend.runtime_info.source == "env:TESSERACT_CMD"


def test_detect_languages_falls_back_to_cli(monkeypatch, tmp_path):
    exe_path = tmp_path / "tesseract.exe"
    exe_path.write_bytes(b"")

    def fake_run(command, **kwargs):
        assert command == [str(exe_path), "--list-langs"]
        return SimpleNamespace(
            returncode=0,
            stdout="List of available languages in C:\\\\OCR\\\\tessdata (2):\neng\ntur\nosd\n",
            stderr="",
        )

    monkeypatch.setattr(tesseract_backend_module.subprocess, "run", fake_run)

    languages = TesseractBackend._detect_languages(str(exe_path), None)

    assert languages == ["eng", "tur"]


def test_run_ocr_invokes_tesseract_cli(monkeypatch, tmp_path):
    captured = {}
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"png")
    tessdata_dir = tmp_path / "tessdata"
    tessdata_dir.mkdir()

    runtime = TesseractRuntimeInfo(
        executable_path=str((tmp_path / "tesseract.exe").resolve()),
        tessdata_dir=str(tessdata_dir.resolve()),
        languages=["tur", "eng"],
        source="test",
    )
    backend = TesseractBackend(runtime)

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="Algilanan metin\n", stderr="")

    monkeypatch.setattr(tesseract_backend_module.subprocess, "run", fake_run)

    result = backend.run_ocr(str(image_path), page_seg_mode=4, timeout_sec=15)

    assert result == "Algilanan metin"
    assert captured["command"] == [
        runtime.executable_path,
        str(image_path),
        "stdout",
        "--oem",
        "1",
        "--psm",
        "4",
        "-l",
        "tur+eng",
        "quiet",
        "--tessdata-dir",
        runtime.tessdata_dir,
    ]
    assert captured["kwargs"]["timeout"] == 15
    assert captured["kwargs"]["env"]["TESSDATA_PREFIX"] == runtime.tessdata_dir
