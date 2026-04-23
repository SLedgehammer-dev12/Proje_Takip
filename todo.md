# Project Backlog

Bu dosya, tek bir oturuma değil proje genelindeki açık işleri ve teknik borçları takip etmek içindir.
Anlık görev yürütme planı için `tasks/todo.md` kullanılır.

## Current Priorities

- [ ] `main_window.py` içindeki büyük iş kurallarını daha küçük katmanlara ayırma planı çıkar
- [ ] Build boyutunu artıran bağımlılıkları analiz edip güvenli azaltma stratejisi belirle
- [ ] `DejaVuSans.ttf` dosyasının eksik veya bozuk olma durumunu düzelt
- [ ] Gerçek otomatik test kapsamı için en az temel smoke test seti tanımla
- [ ] Release çıktıları için code signing yaklaşımını netleştir

## Technical Debt

- [ ] `database.py` ve `main_window.py` için modülerleşme roadmap'i yaz
- [x] `main_window.py` içindeki duplicate preview/document-open metodlarını tek kanonik implementasyona indir
- [x] Doküman açma akışındaki temp-file/OS açma detayını `services/file_service.py` gibi daha küçük bir katmana taşı
- [x] Doküman açma akışındaki DB lookup ve payload kurma detayını `main_window.py` dışına çıkar
- [x] Preview-state senkronizasyonunu `main_window.py` dışına daha küçük bir UI helper katmanına taşı
- [x] Preview cache ve render hazırlık mantığını `main_window.py` dışına daha küçük bir helper katmanına taşı
- [ ] `main_window.py` içindeki sonraki düşük riskli ayrıştırma hedefini yeniden değerlendir
- [x] Export/reporting akışında ilk güvenli lazy import temizliğini uygula (`services/report_service.py` / `pandas`)
- [x] Boş `DejaVuSans.ttf` asset'ini gerçek bir font dosyasıyla değiştir
- [x] Repo/update sözleşmesini `update.md` ile dokümante et
- [x] `v2.0.2` kaynak, tag ve release asset'lerini GitHub'a yayınla
- [ ] Export/reporting akışında kalan lazy import fırsatlarını belirle
- [ ] Paketli `.exe` üzerinde `Dokümanı Görüntüle` akışını gerçek kullanıcı tıklamasıyla doğrula
- [ ] Update ve release akışını daha sıkı verification checklist ile güçlendir
- [ ] Eski `Archive/` içeriğinin hangilerinin korunacağına karar ver

## Notes

- Buradaki maddeler proje seviyesinde kalıcı backlog içindir
- Bir madde aktif implementasyona dönüşürse ayrıntıları `tasks/todo.md` içine taşınır
