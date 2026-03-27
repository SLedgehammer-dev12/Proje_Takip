# Release Akışı

Bu proje için uygulama içi güncelleme kontrolü GitHub `Release` kanalını kullanır. Sadece `push` veya `tag` yeterli değildir.

## 1. Windows paketini üret

Windows makinede:

```powershell
pip install -r requirements/requirements.txt
pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

Üretilen dosyalar:
- `release/vX.Y.Z/ProjeTakip-vX.Y.Z-windows-x64.zip`
- `release/vX.Y.Z/SHA256SUMS`

## 2. GitHub release oluştur

`gh` CLI varsa:

```powershell
gh release create vX.Y.Z `
  ".\release\vX.Y.Z\ProjeTakip-vX.Y.Z-windows-x64.zip" `
  ".\release\vX.Y.Z\SHA256SUMS" `
  --title "vX.Y.Z" `
  --notes-file ".\docs\releases\vX.Y.Z.md"
```

## 3. Kontrol et

- GitHub release public görünmeli
- Asset adı `ProjeTakip-...zip|exe|msi` formatında olmalı
- Checksum dosyası release içinde bulunmalı
- Uygulamadaki `Güncellemeleri Kontrol Et` akışı yeni release'i görmeli
