# Release Manager Agent

Bu ajan, build, paketleme, checksum ve GitHub release akışını yönetir.

## Release Contract (from update.md)
Her yeni sürüm için:
1. `config.py` içinde `APP_VERSION` güncellenir
2. `docs/releases/vX.Y.Z.md` oluşturulur
3. Windows build alınır (`scripts/build_onefile_release.ps1`)
4. Release artefaktları:
   - `release/vX.Y.Z/ProjeTakip-vX.Y.Z-windows-x64.exe`
   - `release/vX.Y.Z/ProjeTakip-vX.Y.Z-windows-x64.zip`
   - `release/vX.Y.Z/SHA256SUMS`
5. GitHub release açılır: tag `vX.Y.Z`
6. EXE, ZIP ve SHA256SUMS asset olarak yüklenir

## Version Pattern
- Asset pattern: `ProjeTakip-.*\.(msi|exe|zip)$`
- SHA256SUMS format: `<hash>  <filename>` (GNU coreutils format)

## Build Verification
- `pytest` tam suite çalışır mı?
- `.exe` açılış smoke testi
- `py_compile` tüm modüller
- CHANGELOG.md güncel mi?
- `guncelleme_notlari.txt` güncel mi?
