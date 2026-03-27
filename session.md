# Session Guide

Bu dosya, oturum başlangıcı, çalışma sırasında bağlam yönetimi ve oturum kapanışı için kullanılır.
Uzun veya bölünebilir görevlerde burası handoff kaydı gibi düşünülmelidir.

## Session Start Checklist

- `skill.md` oku
- `agents.md` oku
- `architecture.md` içinden görevle ilgili modülleri tara
- `test.md` içinden uygun doğrulama adımlarını seç
- `review.md` içinden risk checklistini hatırla
- `tasks/lessons.md` içinde benzer hata veya uyarı var mı bak
- Aktif görevi `tasks/todo.md` içine yaz

## Investigation Notes Template

- Date:
- Goal:
- Related files:
- Constraints:
- Risks:
- Assumptions:
- Verification plan:

## Session Execution Rules

- İlk 10-15 dakikada koda dalmadan önce harita çıkar
- Büyük dosyalarda önce giriş noktalarını, sınıfları ve bağımlılıkları tara
- Kullanıcının bıraktığı yerel değişiklikleri bozma
- Bir şey beklenmedik şekilde davranıyorsa log, traceback, build output veya git diff ile doğrula

## Handoff Template

- Last completed step:
- Current status:
- Files touched:
- Verified:
- Not verified:
- Open risks:
- Recommended next step:

## Current Session Notes

- Date: 2026-03-25
- Goal: Continue stabilization work using the markdown workflow files as the primary operating guide.
- Related files: `main_window.py`, `README.md`, `rapor.py`, `tasks/todo.md`, `todo.md`
- Constraints: Keep surface area small, avoid destabilizing `main_window.py`, prefer delegation to existing helper methods rather than broad rewrites.
- Risks: `main_window.py` contains duplicate legacy methods; changing the wrong one can create regressions or confusion.
- Assumptions: The final method definitions in `AnaPencere` are the runtime-effective implementations and should remain the canonical behavior.
- Verification plan: Update planning docs, clean one low-risk legacy block, run `py_compile`, then run a short application smoke test.
- Last completed step: Removed the duplicate final preview/document-open method block from `main_window.py` after aligning the earlier canonical methods to the shared helper path.
- Current status: `v2.0.2` kaynak kodu origin `main` dalına push edildi, `v2.0.2` tag'i gönderildi, GitHub Release oluşturuldu ve ZIP/checksum asset'leri yüklendi. `update.md` repo içi update sözleşmesini dokümante ediyor.
- Verified: Kaynak push (`main`), tag push (`v2.0.2`), GitHub Release oluşturma, `ProjeTakip-v2.0.2-windows-x64.zip` ve `SHA256SUMS` asset yükleme, mevcut updater config'inin aynı repo (`karkajinho/Proje_Takip`) için ayarlı olması.
- Open risks: Paketli `.exe` içinde `Dokümanı Görüntüle` butonunun gerçek tıklama akışı hâlâ manuel teyit ister; ayrıca uygulama içi updater sadece release akışını doğrular, kullanıcı etkileşimini otomatik test etmez.
- Recommended next step: GitHub Release üstünden indirilen `v2.0.2` paketiyle gerçek kullanıcı senaryosunda manuel update ve doküman açma testi yap.
