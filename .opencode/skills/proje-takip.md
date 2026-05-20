# Proje Takip Skill

Bu skill, Proje Takip Sistemi'nin genel mimarisini ve çalışma prensiplerini tanımlar.

## Stack
- Python 3.10+, PySide6, SQLite, bcrypt
- PyMuPDF (fitz), pandas, xlsxwriter, openpyxl, ReportLab

## Architecture
- `main.py` -> `AnaPencere` -> `controllers/` -> `services/` + `database.py`
- `ui/main_window_ui.py`: UI kurulumu (paneller, toolbar, signal bağlantıları)
- `database.py`: ProjeTakipDB (schema, migration, CRUD, connection pool, WAL)

## Critical Modules
| Module | Risk | Lines |
|--------|------|-------|
| database.py | Yüksek - veri bütünlüğü | 2412 |
| main_window.py | Yüksek - regresyon | 6870 |
| services/report_service.py | Orta - ağır bağımlılıklar | 880+ |
| services/update_client.py | Orta - updater | 589 |

## Data Model
- `ProjeModel`: proje_kodu, proje_ismi, proje_turu, durum, is_flagged
- `RevizyonModel`: revizyon_kodu, durum, yazi_turu, is_flagged, flag_reason, flag_date, flag_user

## Guardrails
- DB dosyalarına (`projeler.db`, `veritabani_yedekleri/`) dokunma
- Migration'lar idempotent olmalı
- Release artefaktlarını repo'ya commit etme (sadece GitHub Release)
