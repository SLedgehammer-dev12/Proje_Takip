# Update Flow

Bu dosya, Proje Takip Sistemi için GitHub tabanlı güncelleme akışını tek yerde özetler.

## Source Of Truth

- Kod deposu: `https://github.com/SLedgehammer-dev12/Proje_Takip`
- Uygulama içi update kontrolü: GitHub Releases
- Config anahtarları: `config.py`
  - `UPDATE_REPO_OWNER = "SLedgehammer-dev12"`
  - `UPDATE_REPO_NAME = "Proje_Takip"`
  - `UPDATE_RELEASE_ASSET_PATTERN = r"ProjeTakip-.*\.(msi|exe|zip)$"`

## Release Contract

Her yeni sürüm için aşağıdakiler hazırlanmalıdır:

1. `config.py` içinde `APP_VERSION` güncellenir
2. `docs/releases/vX.Y.Z.md` oluşturulur
3. Windows build alınır
4. En az şu artefaktlar hazırlanır:
   - `dist/vX.Y.Z/ProjeTakip/ProjeTakip.exe`
   - `release/vX.Y.Z/ProjeTakip-vX.Y.Z-windows-x64.zip`
   - `release/vX.Y.Z/SHA256SUMS`
5. GitHub üzerinde aynı tag adıyla release açılır: `vX.Y.Z`
6. ZIP ve `SHA256SUMS` release asset olarak yüklenir

## In-App Behavior

Uygulama update kontrolünde:

- GitHub Releases içinden en yeni sürümü arar
- Asset adını regex ile eşleştirir
- Checksum dosyasını doğrular
- Yeni sürüm varsa kullanıcıya release notlarını gösterir
- Asset dosyasını `Downloads` klasörüne indirir

## Current v2.1.6 Notes

- Kalıcı Türkçe/İngilizce dil seçimi eklendi
- Merkezi i18n katmanı ile mojibake görünen metinler toparlandı
- `v2.1.5` istemcilerinin yeni release paketini görebileceği updater sözleşmesi korundu

## Operational Reminder

Repo push işlemi tek başına uygulama içi update için yeterli değildir.
Uygulamanın yeni sürümü indirebilmesi için ilgili `GitHub Release` ve release asset dosyaları da yayınlanmalıdır.
