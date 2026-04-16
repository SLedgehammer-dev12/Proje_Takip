# Release Akisi

Bu proje icin uygulama ici guncelleme GitHub `Release` kanalini kullanir. Kalici ve uyumlu yayin icin asset ile checksum ayni kaynaktan uretilmelidir.

## 1. One-file Windows paketini uret

Windows makinede:

```powershell
pip install -r requirements/requirements.txt
pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\scripts\build_onefile_release.ps1
```

Uretilen dosyalar:

- `dist\vX.Y.Z_onefile\ProjeTakip-vX.Y.Z-windows-x64.exe`
- `release\vX.Y.Z\ProjeTakip-vX.Y.Z-windows-x64.exe`
- `release\vX.Y.Z\ProjeTakip-vX.Y.Z-windows-x64.zip`
- `release\vX.Y.Z\SHA256SUMS`

`SHA256SUMS` dosyasinin kanonik formati su olmalidir:

```text
<sha256> *ProjeTakip-vX.Y.Z-windows-x64.exe
<sha256> *ProjeTakip-vX.Y.Z-windows-x64.zip
```

## 2. GitHub release olustur veya guncelle

```powershell
python .\release\upload_release.py --version vX.Y.Z
```

Bu script:

- release notes dosyasini `docs/releases/vX.Y.Z.md` altindan okur
- release yoksa olusturur, varsa gunceller
- mevcut ayni isimli asset'leri silip yeniden yukler
- `SHA256SUMS` dosyasini upload oncesi tekrar kanonik formatta yazar
- hem one-file `.exe` hem de geriye uyumluluk icin `.zip` asset'ini ayni tag altinda yayinlar

## 3. Kontrol et

- GitHub release public gorunmeli
- Asset adlari `ProjeTakip-vX.Y.Z-windows-x64.(exe|zip)` formatinda olmali
- `SHA256SUMS` dosyasi her yayinlanan asset icin kanonik girdiler icermeli
- Uygulamadaki `Guncellemeleri Kontrol Et` akisinda indirme ve checksum dogrulamasi basarili olmali
