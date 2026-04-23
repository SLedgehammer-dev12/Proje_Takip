# Test Guide

Bu repo için artık anlamlı bir otomatik test paketi var, ancak GUI ve release davranışları için yine katmanlı doğrulama gerekir.
Bu yüzden doğrulama stratejisi katmanlı ilerlemelidir: en küçük uygun test, sonra daha geniş pytest koşusu, sonra smoke test, sonra gerekirse manuel akış kontrolü.

## Default Testing Order

1. Syntax veya import seviyesinde hızlı kontrol
2. Göreve özel küçük doğrulama
3. Uygulama açılış smoke testi
4. UI veya DB davranışı etkileniyorsa manuel akış testi
5. Release veya updater etkileniyorsa build/doğrulama testi
6. Metin veya i18n değiştiyse encoding hijyeni testi

## Quick Checks

### Python syntax
```powershell
python -m py_compile main.py
```

### General compile sweep
```powershell
python -m compileall .
```

### App smoke test
```powershell
python main.py
```

### Pytest
```powershell
pytest
```

Not: Repo içinde artık anlamlı test dosyaları vardır. Özellikle veritabanı, updater, log paneli, OCR ve metin/encoding hijyeni için pytest koşuları beklenen doğrulama adımıdır.

### Encoding ve i18n hijyeni
```powershell
pytest tests/test_text_encoding_hygiene.py -q
```

Bu test, kaynak dosyalarda legacy mojibake dizilerinin tekrar sızmadığını ve kritik giriş ekranı metinlerinin gerçek Türkçe karakterlerle tutulduğunu doğrular.

## Change-Based Verification Matrix

### If DB logic changes
- Yedekleme ve geri yükleme akışını düşün
- Şema yaratma veya `ALTER TABLE` adımları idempotent mi kontrol et
- Mevcut veriyi bozabilecek sorgular için örnek akışı doğrula

### If UI changes
- Uygulama açılıyor mu kontrol et
- İlgili ekranı elle aç ve ana buton/akışları dene
- Seçim, filtre ve preview senkronizasyonuna dikkat et

### If report/export changes
- Excel export akışını tetikle
- PDF rapor oluşturma akışını dene
- Dosya yolları, Türkçe karakterler ve eksik font/resource durumlarını kontrol et

### If release/build changes
- `scripts/build_release.ps1` ile build al
- Üretilen `dist/` ve `release/` çıktısını kontrol et
- Checksum dosyasının oluştuğunu doğrula
- Mümkünse `.exe` smoke test yap

### If updater changes
- `docs/UPDATER.md` ile davranış uyumunu kontrol et
- Versiyon karşılaştırma, asset seçimi ve checksum mantığını gözden geçir
- Manual download akışını bozmadığından emin ol

## Log Review

- `proje_takip.log` runtime inceleme için ana kaynaktır
- Build veya release görevlerinde terminal çıktısı ayrıca not edilmelidir
- Doğrulanamayan adımlar açıkça `tasks/todo.md` içinde yazılmalıdır

## Done Rule

Bir görev "tamamlandı" sayılmadan önce en az bir gerçek doğrulama kanıtı bırakılmalıdır:

- başarılı komut
- çalışan uygulama süreci
- oluşan çıktı dosyası
- incelenmiş log veya gözlemlenen davranış
