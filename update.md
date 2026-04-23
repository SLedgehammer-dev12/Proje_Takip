# Update Flow

Bu dosya, Proje Takip Sistemi icin GitHub tabanli guncelleme akisinin kanonik ozetidir.

## Source Of Truth

- Kod deposu: `https://github.com/SLedgehammer-dev12/Proje_Takip`
- Uygulama ici update kontrolu: GitHub Releases
- Config anahtarlari: `config.py`
  - `UPDATE_REPO_OWNER = "SLedgehammer-dev12"`
  - `UPDATE_REPO_NAME = "Proje_Takip"`
  - `UPDATE_RELEASE_ASSET_PATTERN = r"ProjeTakip-.*\.(msi|exe|zip)$"`

## Release Contract

Her yeni surum icin asagidakiler hazirlanmalidir:

1. `config.py` icinde `APP_VERSION` guncellenir
2. `docs/releases/vX.Y.Z.md` olusturulur
3. Windows build alinir
4. En az su artefaktlar hazirlanir:
   - `dist/vX.Y.Z_onefile/ProjeTakip-vX.Y.Z-windows-x64.exe`
   - `release/vX.Y.Z/ProjeTakip-vX.Y.Z-windows-x64.exe`
   - `release/vX.Y.Z/ProjeTakip-vX.Y.Z-windows-x64.zip`
   - `release/vX.Y.Z/SHA256SUMS`
5. GitHub uzerinde ayni tag adiyla release acilir: `vX.Y.Z`
6. EXE, uyumluluk ZIP'i ve `SHA256SUMS` release asset olarak yuklenir

## In-App Behavior

Uygulama update kontrolunde:

- GitHub Releases icinden en yeni surumu arar
- Asset adini regex ile eslestirir
- Checksum dosyasini dogrular
- Yeni surum varsa kullaniciya release notlarini gosterir
- Asset dosyasini `Downloads` klasorune indirir
- Karisik uzunluktaki etiketleri (`v2.1.8.5`, `v2.1.9`, `v2.1.9.0`) sayisal olarak karsilastirir

## Operational Reminder

Repo push islemi tek basina uygulama ici update icin yeterli degildir.
Uygulamanin yeni surumu indirebilmesi icin ilgili `GitHub Release` ve release asset dosyalari da yayinlanmalidir.
