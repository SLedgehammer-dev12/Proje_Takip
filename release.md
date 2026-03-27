# Release Guide

Bu dosya, Windows build ve dağıtım sürecini güvenli ve tekrar üretilebilir biçimde yürütmek için kullanılır.

## Primary Rule

Güvenlik yazılımlarını atlatmaya çalışılmaz.
Bunun yerine meşru dağıtım kalitesi artırılır:

- temiz build
- doğru metadata
- checksum
- mümkünse code signing
- izlenebilir release notları

## Build Flow

### Dependencies
```powershell
pip install -r requirements/requirements.txt
pip install -r requirements-dev.txt
```

### Standard Windows build
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

## Expected Outputs

- `dist/ProjeTakip/ProjeTakip.exe`
- `release/vX.Y.Z/ProjeTakip-vX.Y.Z-windows-x64.zip`
- `release/vX.Y.Z/SHA256SUMS`

## Release Validation

- Build gerçekten tamamlandı mı?
- `.exe` açılış smoke testi yapıldı mı?
- ZIP ve checksum oluştu mu?
- `docs/releases/vX.Y.Z.md` mevcut mu?
- Asset ismi updater regex ile uyumlu mu?

## Packaging Quality Rules

- One-file yerine gerekmedikçe `onedir` paket tercih et
- UPX veya agresif sıkıştırma kullanma
- Version metadata ekle
- Gereksiz dev/test bağımlılıklarını pakete sokmamaya çalış
- Build boyutu anormal büyüyorsa import zincirini analiz et

## Operational Notes

- `docs/RELEASING.md` ve `docs/UPDATER.md` ana referanstır
- Build script değişirse önce yerelde doğrula
- Release çıktıları çalışma verisinden ayrı tutulmalı
- Checksum dosyası release sürecinin zorunlu parçasıdır

## Future Improvements

- Code signing certificate ile imzalama
- Daha hafif build için PyInstaller exclude stratejisi
- Release pipeline standardizasyonu
- Installer tabanlı dağıtım kararı
