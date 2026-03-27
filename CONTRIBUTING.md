# Katkıda Bulunma Rehberi

Teşekkürler! Bu projeye katkı sağlamak istiyorsanız lütfen aşağıdaki kurallara uyun.

## Önemli kurallar
- Veritabanı dosyaları **hiçbir zaman** repoya eklenmemelidir. Bunlar yerel çalışma verileridir ve hassas veya büyük dosyalar içerebilir.
- `projeler.db`, `veritabani_yedekleri/` içeriği, `*.db`, `*.sqlite`, `*.bak` vb. dosyalar repoda takip edilmez.
 - `projeler.db`, `veritabani_yedekleri/` içeriği, `*.db`, `*.sqlite`, `*.bak` vb. dosyalar repoda takip edilmez.
 - Test çıktı dosyaları ve coverage raporları (`test_output.txt`, `coverage/`, `htmlcov/`, `*.coverage` vb.) repoya eklenmez.
 - Test kaynak kodu (`tests/` klasörü) genellikle yerel tutulur ve repoya eklenmez. Eğer bir sebeple test kodu paylaşılacaksa, önce repo sahibine danışın; aksi takdirde lütfen tests/ klasörünü repoya eklemeyin.
- Projeyi klonladıktan sonra `requirements/install_requirements.ps1` veya README'deki talimatları takip ederek geliştirme ortamını kurun.

## İpuçları ve araçlar
- Lokal pre-commit kuralı: `.pre-commit-config.yaml` içinde yer alan `prevent-db-commit` hook'u staged dosyaları kontrol eder ve veritabanı dosyası tespiti durumunda commit işlemini engeller. `pre-commit` kurulu olduğunda otomatik çalışır.
- Eğer veritabanı dosyaları daha önce commit edilmişse, repo’dan kaldırmak için `scripts/untrack_and_push.ps1` betiğini kullanabilirsiniz. Bu betik `git rm --cached` işlemini yapar ve commit atar; isterseniz `-Push` parametresiyle uzak sunucuya push yapar.

## Geliştirme akışı
1. Kendi branch'inizi yaratın:
   - `git checkout -b feat/ozellik-adı`
2. Değişiklikleri yapın, test edin ve commitleyin.
3. Push edip pull request açın.

## Kod konvansiyonları
- Black ve ruff pre-commit hook’ları mevcuttur. Kod biçimlendirme için commit etmeden önce `pre-commit install` komutunu çalıştırın veya CI üzerinde hook'lar tetiklenecektir.

## Yardım veya öneriler
Herhangi bir sorunuz, hata raporunuz veya geliştirme öneriniz varsa GitHub Issues üzerinden açın veya repo sahibine mesaj atın.
