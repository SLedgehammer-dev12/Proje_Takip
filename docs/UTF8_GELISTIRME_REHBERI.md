# UTF-8 Geliştirme Rehberi

Bu repo UTF-8 kaynak dosyaları kullanır. Karakterlerin `GiriÅŸ`, `TÃ¼rkÃ§e` veya benzeri bozuk görünmesi genelde dosya içeriğinden değil, editör veya terminal encoding ayarından gelir.

## Repo Ayarları

- `.editorconfig` UTF-8 ve LF satır sonunu zorlar.
- `.vscode/settings.json` VS Code için `utf8` dosya encoding ayarı verir.
- `scripts/use_utf8_terminal.ps1` PowerShell oturumunda UTF-8 çıkışını ve Python UTF-8 environment değişkenlerini açar.

## PowerShell Kullanımı

Repo içinde yeni bir terminal açtıktan sonra şu komutu dot-source ederek çalıştırın:

```powershell
. .\scripts\use_utf8_terminal.ps1
```

Execution policy engeline takılırsanız şu komutla yeni bir PowerShell oturumunda çalıştırın:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { Set-Location '<repo>'; . .\scripts\use_utf8_terminal.ps1 }"
```

Bu komut mevcut oturum için şunları ayarlar:

- `[Console]::InputEncoding`
- `[Console]::OutputEncoding`
- `$OutputEncoding`
- `PYTHONUTF8=1`
- `PYTHONIOENCODING=utf-8`

## Doğrulama

UTF-8 davranışını kontrol etmek için:

```powershell
. .\scripts\use_utf8_terminal.ps1
python -c "print('Giriş Şifre Türkçe İndir')"
pytest tests/test_text_encoding_hygiene.py -q
```

İkinci komut Türkçe karakterleri bozmadan göstermelidir. Son komut kaynak dosyalarda legacy mojibake tekrar sızmadığını doğrular.
