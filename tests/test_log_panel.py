import os

import pytest
from PySide6.QtWidgets import QApplication

from ui.panels.log_panel import LogPanel


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_log_panel_lazy_disk_load_merges_live_entries(qapp, tmp_path):
    log_path = tmp_path / "proje_takip.log"
    log_path.write_text(
        "2026-03-31 10:00:00,000 - main - INFO - disk kaydi\n",
        encoding="utf-8",
    )

    panel = LogPanel(log_path=str(log_path))
    assert panel.entry_count() == 0

    panel._append_live_entry(
        {
            "timestamp": "2026-03-31 10:00:01,000",
            "logger_name": "main_window",
            "source": "main_window",
            "level": "INFO",
            "message": "canli kayit",
        }
    )
    assert panel.entry_count() == 1

    panel.ensure_loaded_from_disk()
    messages = [entry["message"] for entry in panel._entries]

    assert messages == ["disk kaydi", "canli kayit"]

    panel.ensure_loaded_from_disk()
    assert [entry["message"] for entry in panel._entries] == ["disk kaydi", "canli kayit"]
    panel.close()


def test_log_panel_live_updates_are_opt_in_and_batched(qapp, tmp_path):
    panel = LogPanel(log_path=str(tmp_path / "proje_takip.log"))
    assert panel._live_updates_enabled is False
    assert panel._handler is None

    panel.set_live_updates_enabled(True)
    assert panel._live_updates_enabled is True
    assert panel._handler is not None

    panel._append_live_entry(
        {
            "timestamp": "2026-03-31 10:00:02,000",
            "logger_name": "database.ProjeTakipDB",
            "source": "ProjeTakipDB",
            "level": "ERROR",
            "message": "foreign key",
        }
    )
    assert panel.log_table.rowCount() == 0

    panel._flush_live_entries()
    assert panel.log_table.rowCount() == 1

    panel.set_live_updates_enabled(False)
    assert panel._handler is None
    panel.close()


def test_log_panel_performance_mode_disables_live_updates(qapp, tmp_path):
    panel = LogPanel(log_path=str(tmp_path / "proje_takip.log"))

    panel.set_performance_mode(True)
    panel.set_live_updates_enabled(True)

    assert panel._live_updates_enabled is False
    assert panel._handler is None
    assert "Performans Modu" in panel.summary_label.text()
    panel.close()
