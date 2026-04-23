import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Qt, Signal, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app_paths import get_user_data_path


LOG_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - "
    r"(?P<logger>.+?) - (?P<level>[A-Z]+) - (?P<message>.*)$"
)


def normalize_log_source(logger_name: str) -> str:
    if not logger_name:
        return "root"
    if logger_name == "__main__":
        return "main"
    return logger_name.rsplit(".", 1)[-1]


class QtLogHandler(QObject, logging.Handler):
    log_received = Signal(object)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.setLevel(logging.DEBUG)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created).strftime(
                    "%Y-%m-%d %H:%M:%S,%f"
                )[:-3],
                "logger_name": record.name,
                "source": normalize_log_source(record.name),
                "level": record.levelname,
                "message": record.getMessage(),
            }
            if record.exc_info:
                entry["message"] = (
                    f"{entry['message']}\n{self.formatException(record.exc_info)}"
                )
            self.log_received.emit(entry)
        except Exception:
            return


class LogPanel(QWidget):
    """Show application logs with live updates and source filtering."""

    def __init__(self, parent=None, log_path: Optional[str] = None):
        super().__init__(parent)
        self.log_path = Path(log_path or get_user_data_path("proje_takip.log", create_parent=True))
        self._entries: List[Dict[str, str]] = []
        self._pending_live_entries: List[Dict[str, str]] = []
        self._live_batch_entries: List[Dict[str, str]] = []
        # UI'da tutulacak maksimum log satırı (fazlası otomatik kırpılır)
        self._max_entries = 2000
        self._handler: Optional[QtLogHandler] = None
        self._source_names = {"Tum kaynaklar"}
        self._disk_loaded = False
        self._last_disk_signature: Optional[tuple[int, int]] = None
        self._live_updates_enabled = False
        self._performance_mode = False
        self._flush_live_timer = QTimer(self)
        self._flush_live_timer.setSingleShot(True)
        self._flush_live_timer.setInterval(120)
        self._flush_live_timer.timeout.connect(self._flush_live_entries)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        toolbar.addWidget(QLabel("Sinif/Logger:"))
        self.source_combo = QComboBox()
        self.source_combo.addItem("Tum kaynaklar")
        self.source_combo.currentTextChanged.connect(self._apply_filters)
        toolbar.addWidget(self.source_combo)

        toolbar.addWidget(QLabel("Seviye:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(
            ["Tum seviyeler", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        self.level_combo.currentTextChanged.connect(self._apply_filters)
        toolbar.addWidget(self.level_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Log ara...")
        self.search_input.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self.search_input, 1)

        self.auto_scroll = QCheckBox("Oto kaydir")
        self.auto_scroll.setChecked(True)
        toolbar.addWidget(self.auto_scroll)

        self.refresh_btn = QPushButton("Yenile")
        self.refresh_btn.clicked.connect(lambda: self.refresh_from_disk(force=True))
        toolbar.addWidget(self.refresh_btn)

        # Yeni: log temizleme
        self.clear_btn = QPushButton("Logları Temizle")
        self.clear_btn.setToolTip("Tablodaki ve dosyadaki logları boşalt")
        self.clear_btn.clicked.connect(self.clear_logs)
        toolbar.addWidget(self.clear_btn)

        layout.addLayout(toolbar)

        self.summary_label = QLabel("Log kaydi yuklenmedi.")
        layout.addWidget(self.summary_label)

        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(
            ["Zaman", "Kaynak", "Seviye", "Mesaj"]
        )
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.log_table.setSelectionMode(QTableWidget.SingleSelection)
        self.log_table.setWordWrap(False)
        self.log_table.verticalHeader().setVisible(False)
        header = self.log_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.log_table, 1)

    def attach_live_logging(self):
        if self._handler:
            return
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, QtLogHandler):
                self._handler = handler
                break

        if not self._handler:
            self._handler = QtLogHandler()
            root_logger.addHandler(self._handler)

        self._handler.log_received.connect(self._append_live_entry)

    def detach_live_logging(self):
        if self._handler:
            try:
                self._handler.log_received.disconnect(self._append_live_entry)
            except Exception:
                pass
            self._handler = None

    def set_live_updates_enabled(self, enabled: bool):
        enabled = bool(enabled)
        if enabled and self._performance_mode:
            enabled = False
        if enabled == self._live_updates_enabled:
            return

        self._live_updates_enabled = enabled
        if enabled:
            self.attach_live_logging()
            self.ensure_loaded_from_disk()
        else:
            self._flush_live_timer.stop()
            self._live_batch_entries.clear()
            self.detach_live_logging()
        self._update_summary()

    def set_performance_mode(self, enabled: bool):
        enabled = bool(enabled)
        if enabled == self._performance_mode:
            return
        self._performance_mode = enabled
        if enabled:
            self.set_live_updates_enabled(False)
        self._update_summary()

    def closeEvent(self, event):
        self._flush_live_timer.stop()
        self.detach_live_logging()
        super().closeEvent(event)

    def ensure_loaded_from_disk(self):
        if not self._disk_loaded:
            self.refresh_from_disk(force=True)

    def refresh_from_disk(self, force: bool = False):
        if not force and not self._should_reload_from_disk():
            return
        entries = self._load_entries_from_disk()
        entries = self._merge_pending_live_entries(entries)
        self._entries = entries[-self._max_entries :]
        self._disk_loaded = True
        self._rebuild_source_filter()
        self._apply_filters()

    def entry_count(self) -> int:
        return len(self._entries)

    def available_sources(self) -> List[str]:
        return sorted(self._source_names)

    def _load_entries_from_disk(self) -> List[Dict[str, str]]:
        if not self.log_path.exists():
            self._last_disk_signature = None
            return []

        text = self.log_path.read_text(encoding="utf-8-sig", errors="replace")
        self._last_disk_signature = self._get_disk_signature()
        return self._parse_log_text(text)

    def _get_disk_signature(self) -> Optional[tuple[int, int]]:
        try:
            stat = self.log_path.stat()
            return (stat.st_size, stat.st_mtime_ns)
        except OSError:
            return None

    def _should_reload_from_disk(self) -> bool:
        if not self._disk_loaded:
            return True
        return self._get_disk_signature() != self._last_disk_signature

    def _merge_pending_live_entries(
        self, disk_entries: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        if not self._pending_live_entries:
            return disk_entries

        seen = {
            (
                entry.get("timestamp", ""),
                entry.get("logger_name", ""),
                entry.get("level", ""),
                entry.get("message", ""),
            )
            for entry in disk_entries
        }
        merged = list(disk_entries)
        for entry in self._pending_live_entries:
            identity = (
                entry.get("timestamp", ""),
                entry.get("logger_name", ""),
                entry.get("level", ""),
                entry.get("message", ""),
            )
            if identity in seen:
                continue
            merged.append(entry)
            seen.add(identity)

        self._pending_live_entries = self._pending_live_entries[-200:]
        return merged

    def _parse_log_text(self, text: str) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []
        current: Optional[Dict[str, str]] = None

        for raw_line in text.splitlines():
            match = LOG_LINE_RE.match(raw_line)
            if match:
                if current:
                    entries.append(current)
                logger_name = match.group("logger").strip()
                current = {
                    "timestamp": match.group("ts"),
                    "logger_name": logger_name,
                    "source": normalize_log_source(logger_name),
                    "level": match.group("level").strip(),
                    "message": match.group("message"),
                }
                continue

            if current:
                current["message"] = f"{current['message']}\n{raw_line}".rstrip()

        if current:
            entries.append(current)
        return entries

    def _append_live_entry(self, entry: Dict[str, str]):
        self._pending_live_entries.append(entry)
        if len(self._pending_live_entries) > 200:
            self._pending_live_entries = self._pending_live_entries[-200:]
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]
        self._live_batch_entries.append(entry)
        if self._live_updates_enabled and not self._flush_live_timer.isActive():
            self._flush_live_timer.start()

    def _flush_live_entries(self):
        batch = self._live_batch_entries
        self._live_batch_entries = []
        if not batch:
            return

        for entry in batch:
            source = entry.get("source") or "root"
            if source not in self._source_names:
                self._source_names.add(source)

        self._rebuild_source_filter()
        self._apply_filters()

    def _rebuild_source_filter(self):
        self._source_names = {"Tum kaynaklar"}
        for entry in self._entries:
            self._source_names.add(entry.get("source") or "root")

        current_source = self.source_combo.currentText()
        items = self.available_sources()
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItems(items)
        self.source_combo.setCurrentText(
            current_source if current_source in items else "Tum kaynaklar"
        )
        self.source_combo.blockSignals(False)

    def _matches_filters(self, entry: Dict[str, str]) -> bool:
        selected_source = self.source_combo.currentText()
        if selected_source and selected_source != "Tum kaynaklar":
            if entry.get("source") != selected_source:
                return False

        selected_level = self.level_combo.currentText()
        if selected_level and selected_level != "Tum seviyeler":
            if entry.get("level") != selected_level:
                return False

        search_text = self.search_input.text().strip().lower()
        if search_text:
            haystack = " ".join(
                [
                    entry.get("timestamp", ""),
                    entry.get("logger_name", ""),
                    entry.get("source", ""),
                    entry.get("level", ""),
                    entry.get("message", ""),
                ]
            ).lower()
            if search_text not in haystack:
                return False

        return True

    def _apply_filters(self):
        filtered = [entry for entry in self._entries if self._matches_filters(entry)]
        self.log_table.setUpdatesEnabled(False)
        self.log_table.setRowCount(0)
        for entry in filtered:
            self._append_row(entry, scroll=False)
        self.log_table.setUpdatesEnabled(True)
        if filtered and self.auto_scroll.isChecked():
            self.log_table.scrollToBottom()
        self._update_summary(filtered_count=len(filtered))

    def _append_row(self, entry: Dict[str, str], *, scroll: bool = True):
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)

        values = [
            entry.get("timestamp", ""),
            entry.get("source", ""),
            entry.get("level", ""),
            entry.get("message", ""),
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col != 3:
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.log_table.setItem(row, col, item)

        self._style_row(row, entry.get("level", "INFO"))
        if scroll and self.auto_scroll.isChecked():
            self.log_table.scrollToBottom()

    def _style_row(self, row: int, level: str):
        colors = {
            "DEBUG": QColor("#5f6b7a"),
            "INFO": QColor("#1f5f99"),
            "WARNING": QColor("#a15c00"),
            "ERROR": QColor("#b42318"),
            "CRITICAL": QColor("#7a0019"),
        }
        color = colors.get(level)
        if not color:
            return
        level_item = self.log_table.item(row, 2)
        if level_item:
            level_item.setForeground(color)
        source_item = self.log_table.item(row, 1)
        if source_item and level in {"ERROR", "CRITICAL"}:
            source_item.setForeground(color)

    def _update_summary(self, filtered_count: Optional[int] = None):
        visible_count = filtered_count if filtered_count is not None else self.log_table.rowCount()
        summary = (
            f"Toplam log: {len(self._entries)} | Gosterilen: {visible_count} | Dosya: {self.log_path.name}"
        )
        if self._performance_mode:
            summary += " | Canli izleme kapali (Performans Modu)"
        self.summary_label.setText(summary)

    def clear_logs(self):
        """UI ve disk loglarını temizle; büyük dosyalarda performans kazancı sağlar."""
        try:
            self._entries.clear()
            self._pending_live_entries.clear()
            self._live_batch_entries.clear()
            self._flush_live_timer.stop()
            self.log_table.setRowCount(0)
            self._source_names = {"Tum kaynaklar"}
            self._rebuild_source_filter()
            self._update_summary()
            try:
                self.log_path.write_text("", encoding="utf-8")
                self._last_disk_signature = self._get_disk_signature()
            except Exception:
                pass
        except Exception:
            pass
