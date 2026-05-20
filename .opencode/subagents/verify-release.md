# Release Verification Subagent

Bu subagent, release öncesi doğrulama adımlarını yürütür.

## Verification Checklist
- [ ] `python3 -m py_compile` tüm modüller başarılı mı?
- [ ] `config.py` APP_VERSION güncel mi?
- [ ] `docs/releases/vX.Y.Z.md` mevcut mu?
- [ ] `guncelleme_notlari.txt` güncel mi?
- [ ] CHANGELOG.md güncel mi?
- [ ] Tag `vX.Y.Z` oluşturuldu mu?
- [ ] SHA256SUMS dosyası mevcut mu?
- [ ] Asset pattern regex ile uyumlu mu? (ProjeTakip-.*\.(msi|exe|zip)$)

## GitHub Release Kontratı
- Tag: `vX.Y.Z` (v prefix)
- Asset naming: `ProjeTakip-vX.Y.Z-windows-x64.exe`
- SHA256SUMS: `<hash>  <filename>` formatı
- ZIP: `ProjeTakip-vX.Y.Z-windows-x64.zip`

## Output
- ✓ veya ✗ her adım için
- Başarısız adımlar için düzeltme önerisi
- Release hazır mı? Evet/Hayır
