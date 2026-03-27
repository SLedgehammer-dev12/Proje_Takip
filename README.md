# Proje Takip Sistemi v2.0.1

Yerelde çalışan, PySide6 tabanlı proje ve revizyon takip uygulaması.

## Öne Çıkan Yenilikler

### v2.0.1
- Açılış veritabanı akışı hafifletildi
- Ağır startup bakım adımları kaldırıldı
- Açılış yedeği geri alındı
- Login ekranı ana pencereden önce açılarak gereksiz yük azaltıldı

### v2.0.0
- GitHub Release tabanlı uygulama güncelleme kontrolü eklendi
- Tekli dosya yüklemede proje kodu, adı, türü ve yazı bilgileri düzenlenebilir hale geldi
- Proje türleri merkezileştirildi: `İnşaat`, `Mekanik`, `Piping`, `Elektrik`, `I&C`, `Siemens`, `Diğer`
- Eski proje türleri veritabanında normalize ediliyor, tanımsız olanlar `Diğer`e alınıyor
- RAM kullanım göstergesi gerçek proses belleğini gösteriyor
- SQLite katmanı `WAL`, `busy_timeout`, `quick_check`, `optimize` ve kontrollü shutdown ile sağlamlaştırıldı

### Önceki Sürümler
- v1.5.1: Excel raporlama alanları ve lazy loading iyileştirmeleri
- v1.5: Grafikler, dashboard ve raporlama iyileştirmeleri
- v1.3: Kullanıcı girişi ve yetkilendirme

## Özellikler

- Proje ve revizyon yönetimi
- Gelen/giden yazı takibi
- PDF doküman saklama ve önizleme
- Kategori bazlı sınıflandırma
- Gelişmiş filtreleme
- Excel/PDF raporlama
- Otomatik ve manuel veritabanı yedekleme
- Kullanıcı girişi ve misafir modu
- GitHub Release tabanlı güncelleme kontrolü

## Teknoloji Yapısı

- Python 3
- PySide6
- SQLite
- bcrypt

## Kurulum

### Gereksinimler

```bash
pip install -r requirements/requirements.txt
pip install bcrypt
```

### Çalıştırma

```bash
python main.py
```

## Güncelleme Mantığı

Uygulama içindeki `Güncellemeleri Kontrol Et` akışı doğrudan GitHub `Release` kaynağını kullanır. Sadece `push` yapmak yeterli değildir. İstemcinin yeni sürümü görebilmesi için GitHub üzerinde yeni bir `Release` yayınlanmalıdır.

Mevcut ayarlar:
- Repo: [karkajinho/Proje_Takip](https://github.com/karkajinho/Proje_Takip)
- Release sayfası: [latest releases](https://github.com/karkajinho/Proje_Takip/releases/latest)

### Release yayınlama kuralları

Güncelleme kontrolünün çalışması için release içinde aşağıdakiler bulunmalıdır:

1. Tag formatı: `v2.0.1` gibi bir sürüm etiketi
2. Uygulama asset'i: `ProjeTakip-...exe`, `ProjeTakip-...msi` veya `ProjeTakip-...zip`
3. Checksum dosyası: `SHA256SUMS`, `checksums.txt`, `<asset>.sha256` veya `<asset>.sha256.txt`

Uygulama yeni release bulduğunda:
- sürümü karşılaştırır
- release notlarını gösterir
- kullanıcı isterse asset'i `Downloads` klasörüne indirir
- otomatik kurulum yapmaz

## Release Üretimi

Windows dağıtımı için hazır scriptler eklendi:

```powershell
pip install -r requirements/requirements.txt
pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

Bu işlem şu dosyaları üretir:
- `release/v2.0.1/ProjeTakip-v2.0.1-windows-x64.zip`
- `release/v2.0.1/SHA256SUMS`

GitHub release adımları için bkz. [`docs/RELEASING.md`](docs/RELEASING.md).

## Varsayılan Kullanıcılar

- `alperb.yilmaz` / `Botas.2025`
- `omer.erbas` / `Botas.2025`

## Proje Türleri

Aktif tür listesi:
- `İnşaat`
- `Mekanik`
- `Piping`
- `Elektrik`
- `I&C`
- `Siemens`
- `Diğer`

## Dizin Yapısı

```text
Proje_Takip-main/
├── main.py
├── main_window.py
├── database.py
├── config.py
├── project_types.py
├── dialogs/
├── controllers/
├── services/
├── ui/
├── docs/
└── utils.py
```

## Güvenlik ve Veri Dayanıklılığı

- Şifreler düz metin olarak tutulmaz, `bcrypt` ile hashlenir
- SQLite `WAL` modunda çalışır
- Açılışta `quick_check`, kapanışta `optimize` ve `checkpoint` uygulanır
- Otomatik yedekleme desteği vardır
- Yedekler geri yüklenebilir

## Geliştirme Notları

- Çalışma veritabanı ve Excel dosyaları `.gitignore` ile dışarıda bırakılır
- Release tabanlı güncelleme için checksum dosyası şarttır
- Public repo kullanıldığında uygulama içi update kontrolü token olmadan da çalışır

## Development Workflow

Bu repo icinde gelistirme yaparken sadece koda bakmak yeterli degildir. Proje kokunde olusturulan calisma dosyalari birlikte okunmalidir:

1. `skill.md`
2. `agents.md`
3. `session.md`
4. `architecture.md`
5. `test.md`
6. `review.md`
7. `release.md` (build, updater veya paketleme isi varsa)
8. `todo.md`
9. `tasks/todo.md`
10. `tasks/lessons.md`

Kural ayrimi:
- `todo.md`: repo seviyesinde kalici backlog
- `tasks/todo.md`: aktif gorevin yurutme plani
- `tasks/lessons.md`: kullanici geri bildirimi ve tekrar eden hata dersleri

Beklenen gelistirme akisi:
- Once ilgili `.md` dosyalarini oku
- Sonra plani yaz
- Ardindan minimum etkili degisikligi uygula
- Test/smoke test/log ile dogrula
- Son olarak review ve follow-up notlarini birak

## Lisans

Bu proje özel kullanım içindir.

## Sürüm

- Son güncelleme: 17 Mart 2026
- Versiyon: `v2.0.1`
