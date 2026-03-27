## Project overview

This is a PySide6-based desktop app for tracking projects and revisions (Turkish UI). Key runtime entrypoint is `main.py` which creates `QApplication` and `AnaPencere` from `main_window.py`.

Core components
- UI: `main_window.py`, `dialogs.py`, `AdvancedFilterDialog.py`, `widgets.py` (custom widgets: `KategoriAgaci`, `ZoomableScrollArea`, `PdfRenderWorker`).
- Data access: `database.py` implements `ProjeTakipDB` (sqlite3, migrations included).
- Domain models: `models.py` contains `ProjeModel` and `RevizyonModel` dataclasses — their field order must match SELECT query column order.
- Business logic / filters: `filters.py` (`AdvancedFilterManager`) — builds parameterized WHERE clauses used by UI.
- Utilities and config: `utils.py`, `config.py` (CHANGELOG and visual constants).

Important patterns & gotchas for code edits
- Dataclass / SQL contract: `ProjeModel`/`RevizyonModel` field order maps directly to SELECT statements in `database.py` and `filters.py`. When changing queries or adding columns, update the dataclass order and all SELECTs that feed it.
- DB migrations: `ProjeTakipDB.__init__` runs migration helpers (`tablolari_olustur`, `_veritabani_gecisi_yap`, `_indeksleri_olustur`, `_hiyerarsi_verisini_tasi`). Add schema changes there and ensure ALTER TABLE idempotence checks match existing pattern.
- Signal propagation for async PDF rendering: `AnaPencere` emits `_start_pdf_render` (bytes, float, rev_id) -> `PdfRenderWorker.render_page` runs in a `QThread` and emits `image_ready(QImage, rev_id)` or `error(str, rev_id)`. Always pass rev_id through to avoid race conditions; if you change any signal signature update all emitters/slots accordingly (search for image_ready, error, _start_pdf_render).
- Category handling: app migrated from storing a text `hiyerarsi` to `kategori_id` integer. UI dialogs (`ProjeDialog`) and tree (`KategoriAgaci`) use `kategori_id` (ComboBox data). When changing code that touches categories, prefer `kategori_id` and consult `_hiyerarsi_verisini_tasi` for migration logic.
- Filters: `AdvancedFilterManager.available_filters` defines UI labels -> DB field mappings used by `build_sql_where_clause`. If you add a filter option, update both `filters.py` and `AdvancedFilterDialog` UI wiring.

Developer workflows
- Run locally: `python main.py` (requires Python + dependencies listed below).
- Logging: app writes runtime logs to `proje_takip.log` (configured in `utils.py` / `config.py`) — inspect it for stack traces and startup failures.
- Database file: default `projeler.db` in working directory; migrations run automatically on DB open. Back up before schema edits.

Dependencies (inferred from imports)
- PySide6 (UI)
- PyMuPDF (imported as `fitz`) for PDF rendering
- pandas (used in `main_window.py` for reporting/exporting)
- xlsxwriter is optionally required for column autosizing when exporting to Excel
- sqlite3 is builtin; other stdlib modules used (logging, datetime, os)

Editing conventions & examples
- When adding a new column to `revizyonlar` SELECTs, update:
  - SQL string in `database.py`/`filters.py`
  - `ProjeModel` / `RevizyonModel` dataclass order in `models.py`
  - Any code that constructs instances from `cursor.fetchall()` (they assume tuple order)

- Example: to add a `tse_gonderildi` filter: ensure `tse_gonderildi` exists in SQL SELECT (see `filters.py` and `database.py`), add `available_filters` entry in `filters.py` and wire UI in `AdvancedFilterDialog`.

Testing & quick debug tips
- To reproduce UI issues: run `python main.py` and watch `proje_takip.log` for errors. Use breakpoints in `AnaPencere` methods where UI actions call DB (`projeleri_yukle`, `revizyonlari_yukle`).
- When modifying threading or signals, test PDF preview race-conditions by rapidly selecting different revisions; verify `render_page` always includes `rev_id` and that `AnaPencere._on_image_ready` checks the current selected rev id (it does).

Where to look first for changes
- UI flows: `main_window.py` (largest, contains wiring between widgets, DB, filters)
- DB logic: `database.py` (transactions, migrations, model-returning queries)
- Filters: `filters.py` + `AdvancedFilterDialog.py` (UI + SQL builder)

If something is unclear, ask before changing:
- Any change touching SQL -> dataclass mapping
- Signal signature changes across widgets/threads

Please review these notes and tell me if you want me to adjust the tone, add examples (code snippets), or include a requirements file (`requirements.txt`).
