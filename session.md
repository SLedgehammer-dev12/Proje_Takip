# Session Guide

Bu dosya, oturum baslangici, calisma sirasinda baglam yonetimi ve oturum kapanisi icin kullanilir.
Uzun veya bolunebilir gorevlerde burasi handoff kaydi gibi dusunulmelidir.

## Session Start Checklist

- `skill.md` oku
- `agents.md` oku
- `architecture.md` icinden gorevle ilgili modulleri tara
- `test.md` icinden uygun dogrulama adimlarini sec
- `review.md` icinden risk checklistini hatirla
- `tasks/lessons.md` icinde benzer hata veya uyari var mi bak
- Aktif gorevi `tasks/todo.md` icine yaz

## Investigation Notes Template

- Date:
- Goal:
- Related files:
- Constraints:
- Risks:
- Assumptions:
- Verification plan:

## Session Execution Rules

- Ilk 10-15 dakikada koda dalmadan once harita cikar
- Buyuk dosyalarda once giris noktalarini, siniflari ve bagimliliklari tara
- Kullanicinin biraktigi yerel degisiklikleri bozma
- Bir sey beklenmedik sekilde davraniyorsa log, traceback, build output veya git diff ile dogrula

## Handoff Template

- Last completed step:
- Current status:
- Files touched:
- Verified:
- Not verified:
- Open risks:
- Recommended next step:

## Current Session Notes

- Date: 2026-03-31
- Goal: Uygulamanin kaynak tuketimini davranis bozmadan azaltmak ve bu paketi `v2.1.5` olarak yayinlamak.
- Related files: `main_window.py`, `widgets.py`, `services/preview_render_service.py`, `services/backup_service.py`, `ui/panels/log_panel.py`, `config.py`, `docs/releases/v2.1.5.md`
- Constraints: Yazi/proje on izleme ve tam ekran akislari korunmali, kaynak kullanimi dusurulmeli, yerelde onceden kirli duran `release/v2.1.0/*` dosyalarina dokunulmamalidir.
- Risks: Performans iyilestirmeleri timer ve preview zamanlamasini etkiledigi icin gercek kullanici akisinda manuel gozlem hala degerli.
- Assumptions: Bir sonraki oturumda odak, `v2.1.5` paketinin uzun sureli manuel performans ve kullanim testi olacak.
- Verification plan: `py_compile`, `.venv\\Scripts\\python.exe -m pytest -q`, `QT_QPA_PLATFORM=offscreen` ile ana pencere smoke testi, one-file build, exe surum/checksum dogrulamasi, GitHub release asset kontrolu.
- Last completed step: Performans optimizasyon paketi uygulanip `v2.1.5` olarak build edildi; `main` ve `v2.1.5` GitHub'a gonderildi, release asset'leri yuklendi.
- Current status: Release hazir: `https://github.com/SLedgehammer-dev12/Proje_Takip/releases/tag/v2.1.5`. `main` ve `v2.1.5` tag'i commit `38fa5ec450ce2e90ac296d08682c8d1f982a8d80` uzerinde. Exe surumu `2.1.5.0`, SHA256 `ce7f7e46b2cf8072de3ee0d9ba792a87f1359b309a4bc6dc300e01f2eb4df73d`.
- Verified: `8 passed` pytest, `py_compile`, offscreen smoke, one-file build, canonical `SHA256SUMS`, GitHub release tag ve asset gorunurlugu.
- Not verified: Uzun sureli manuel performans gozlemi, dusuk RAM'li makinelerde saha davranisi, son kullanici tarafinda hissedilen akicilik farki.
- Open risks: Yerelde eski ve ilgisiz iki kirli dosya duruyor: `release/v2.1.0/ProjeTakip-v2.1.0-windows-x64.exe` ve `release/v2.1.0/SHA256SUMS`. Sonraki oturumda bunlarin bilincli olarak disarida birakildigi unutulmamalidir.
- Recommended next step: `v2.1.5` paketini gercek kullanici akisinda acip revizyonlar arasinda hizli gecis, yazi on izleme, log sekmesi ve uzun sure acik kalma senaryolarini manuel gozlemle test et.
