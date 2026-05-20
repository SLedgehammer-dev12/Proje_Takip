# Proje Takip Dev Agent

Bu ajan, Proje Takip Sistemi'nin ana geliştirme ajanıdır.

## Primary Responsibilities
- Kod tabanında değişiklik yapmadan önce `skill.md`, `architecture.md`, `agents.md` oku
- Mevcut kod desenlerine ve mimarisine saygı duy
- Modüler yapıyı koru: `controllers/` -> `services/` -> `database.py` katman hiyerarşisi
- Her değişiklikten sonra `py_compile` ile syntax doğrulaması yap

## Codebase Map
- `main.py`: Giriş noktası, QApplication, exception hooks
- `main_window.py`: Ana pencere (büyük - dikkatli düzenle)
- `database.py`: SQLite veritabanı (şema, sorgular, migration)
- `models.py`: ProjeModel, RevizyonModel dataclass'ları
- `services/`: Auth, backup, update, report, preview, file services
- `dialogs/`: Login, project, revision, export dialogları
- `ui/panels/`: Panel bileşenleri (project, revision, preview, log, red_flag)

## Critical Rules
- `models.py` dataclass alan sırası SQL SELECT sırasıyla eşleşmeli
- `database.py` migration'ları idempotent olmalı
- `Update release` akışı `update.md`'deki kontrata uygun olmalı
- Geriye dönük uyumluluk korunmalı
- Yerel veritabanı dosyalarına zarar verme
