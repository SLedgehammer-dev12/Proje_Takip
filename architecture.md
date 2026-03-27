# Architecture Guide

Bu dosya, kod tabanının pratik haritasını ve kritik değişmezlerini özetler.

## High-Level Map

- `main.py`: Uygulama giriş noktası, `QApplication`, login akışı, stil ve exception hook kurulumu
- `main_window.py`: Ana pencerenin büyük kısmı; UI wiring, event handling, DB çağrıları ve iş akışı burada yoğunlaşır
- `database.py`: SQLite bağlantısı, şema, indexler, transaction yönetimi, backup entegrasyonu ve çekirdek veri erişimi
- `models.py`: `ProjeModel` ve `RevizyonModel` dataclass sözleşmeleri
- `filters.py` ve `AdvancedFilterDialog.py`: gelişmiş filtreleme UI + SQL üretimi
- `dialogs/`: proje, revizyon, export, login ve diğer modal akışlar
- `services/`: auth, backup, excel import, export, report, updater ve hata yönetimi
- `ui/` ve `ui/panels/`: panel bazlı UI bileşenleri ve stil
- `widgets.py`: özel widgetlar ve PDF render worker
- `scripts/`: build, release, repo bakım ve güvenlik yardımcı scriptleri

## Critical Invariants

- `models.py` içindeki dataclass alan sırası, SQL sorgularının döndürdüğü kolon sırasıyla uyumlu olmalıdır
- PDF preview sinyalleri `rev_id` benzeri bağlam bilgisini kaybetmemelidir
- Veritabanı değişikliklerinde migration veya idempotent schema guard düşünülmelidir
- Update ve release akışı `docs/UPDATER.md` ile `docs/RELEASING.md` doğrultusunda kalmalıdır
- Yerel veritabanı, Excel ve backup dosyaları çalışma verisidir; deneysel dosya gibi ele alınmamalıdır

## Hotspots

- `main_window.py`: çok büyük, yüksek regresyon riski
- `database.py`: veri bütünlüğü ve performans için kritik
- `services/report_service.py`: ağır bağımlılıklar ve export davranışı burada
- `services/update_client.py`: updater ve release güveni açısından önemli
- `scripts/build_release.ps1`: Windows paketleme için kritik

## Refactor Priorities

- `main_window.py` içindeki iş kurallarını kademeli olarak `controllers/` ve `services/` katmanına taşımak
- Report/export bağımlılıklarını lazy import ile daha sınırlı toplamak
- UI bileşenleri ile DB erişimini daha temiz ayırmak
- Test kapsamı olmayan kritik yollar için smoke test veya küçük otomasyonlar eklemek

## Dependency Notes

- Core runtime: `PySide6`, `sqlite3`, `bcrypt`
- Document/preview: `PyMuPDF`
- Excel/reporting: `pandas`, `xlsxwriter`, `openpyxl`
- Packaging side effects: `pandas` ekosistemi build boyutunu ciddi artırabilir

## Before Editing These Areas

- Startup/login: `main.py`, `dialogs/login_dialog.py`, `services/auth_service.py`
- DB schema/query: `database.py`, `models.py`, `filters.py`
- Preview/PDF: `widgets.py`, `ui/panels/preview_panel.py`, `main_window.py`
- Reporting/export: `services/report_service.py`, `rapor.py`, `services/project_export_service.py`
- Release/updater: `scripts/build_release.ps1`, `services/update_client.py`, `docs/RELEASING.md`, `docs/UPDATER.md`
