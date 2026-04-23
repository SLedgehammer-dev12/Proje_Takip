# Release Guide

Bu dosya, Windows build ve dagitim surecini guvenli ve tekrar uretilebilir bicimde yurutmek icin kullanilir.

## Primary Rule

Guvenlik yazilimlarini atlatmaya calisilmaz.
Bunun yerine mesru dagitim kalitesi artirilir:

- temiz build
- dogru metadata
- checksum
- mumkunse code signing
- izlenebilir release notlari

## Build Flow

### Dependencies
```powershell
pip install -r requirements/requirements.txt
pip install -r requirements-dev.txt
```

### Standard Windows build
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_onefile_release.ps1
```

## Expected Outputs

- `dist/vX.Y.Z_onefile/ProjeTakip-vX.Y.Z-windows-x64.exe`
- `release/vX.Y.Z/ProjeTakip-vX.Y.Z-windows-x64.exe`
- `release/vX.Y.Z/ProjeTakip-vX.Y.Z-windows-x64.zip`
- `release/vX.Y.Z/SHA256SUMS`

## Release Validation

- Build gercekten tamamlandi mi?
- `.exe` acilis smoke testi yapildi mi?
- EXE, ZIP ve checksum olustu mu?
- `docs/releases/vX.Y.Z.md` mevcut mu?
- Asset ismi updater regex ile uyumlu mu?

## Packaging Quality Rules

- Varsayilan dagitim paketi one-file `.exe` + uyumluluk `.zip` ciftidir
- UPX veya agresif sikistirma kullanma
- Version metadata ekle
- Gereksiz dev/test bagimliliklarini pakete sokmamaya calis
- Build boyutu anormal buyuyorsa import zincirini analiz et

## Operational Notes

- `docs/RELEASING.md` ve `docs/UPDATER.md` ana referanstir
- Build script degisirse once yerelde dogrula
- Release ciktilari calisma verisinden ayri tutulmalidir
- Checksum dosyasi release surecinin zorunlu parcasidir

## Future Improvements

- Code signing certificate ile imzalama
- Daha hafif build icin PyInstaller exclude stratejisi
- Release pipeline standardizasyonu
- Installer tabanli dagitim karari
