import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from services.report_service import ReportService, _PdfReportWorker


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_pdf_report_worker_emits_error_message_on_exception():
    results = []

    def broken_report(*_args):
        raise RuntimeError("boom")

    worker = _PdfReportWorker("demo.db", "out.pdf", broken_report)
    worker.finished.connect(lambda success, path, error: results.append((success, path, error)))

    worker.run()

    assert results == [(False, "out.pdf", "boom")]


def test_generate_pdf_report_runs_in_background_and_cleans_up(qapp, monkeypatch, tmp_path):
    output_path = tmp_path / "rapor.pdf"
    fake_module = SimpleNamespace(
        REPORTLAB_AVAILABLE=True,
        rapor_olustur=lambda db_path, file_path: Path(file_path).write_bytes(
            f"{db_path}|ok".encode("utf-8")
        ) or True,
    )
    monkeypatch.setitem(sys.modules, "rapor", fake_module)
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(output_path), "PDF"),
    )

    info_calls = []
    warning_calls = []
    opened_files = []

    def fake_information(*args, **kwargs):
        info_calls.append(args[2] if len(args) > 2 else "")
        return QMessageBox.No

    def fake_warning(*args, **kwargs):
        warning_calls.append(args[2] if len(args) > 2 else "")
        return QMessageBox.Ok

    monkeypatch.setattr(QMessageBox, "information", fake_information)
    monkeypatch.setattr(QMessageBox, "warning", fake_warning)

    parent = QWidget()
    service = ReportService(db=SimpleNamespace(db_adi="demo.db"), parent=parent)
    monkeypatch.setattr(service, "_open_file", lambda file_path: opened_files.append(file_path))

    assert service.generate_pdf_report() is True

    deadline = time.time() + 5
    while service._pdf_report_thread is not None and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.01)

    assert service._pdf_report_thread is None
    assert service._pdf_report_worker is None
    assert service._pdf_report_progress is None
    assert output_path.exists()
    assert warning_calls == []
    assert opened_files == []
    assert any("PDF raporu" in message for message in info_calls)
