# Klasor Rehberi

Bu dosya, repo icindeki klasorlerin ne amacla tutuldugunu ve hangilerinin surum takibi icin kanonik yer oldugunu hizli gormek icin hazirlandi.

## Kokte Bilerek Birakilanlar

- `main.py`, `main_window.py`, `database.py`, `config.py`, `widgets.py`, `rapor.py`: uygulamanin ana giris ve cekirdek dosyalari
- `projeler.db`, `veritabani_yedekleri/`, `proje_takip.log`: runtime verileri; kaynak kod tarihi yerine calisma verisi olarak dusunulmeli
- `ProjeTakip*.spec`: build konfigurasyonlari kokte tutuluyor cunku packaging scriptleriyle birlikte kullaniliyor
- `skill.md`, `agents.md`, `session.md`, `test.md`, `review.md`, `todo.md`, `update.md`, `release.md`: repo ici calisma akisi dosyalari hizli erisim icin kokte tutuluyor
- `sesion.md`: eski/yanlis adli oturum notu; kanonik dosya `session.md`

## Kaynak Kod Klasorleri

- `controllers/`: pencere ile servisler arasindaki davranis akislari
- `dialogs/`: ayri dialog pencereleri
- `services/`: dosya, yedekleme, rapor, auth gibi servis katmani
- `ui/`: daha moduler arayuz panelleri ve UI yardimcilari
- `tests/`: otomatik testler

## Surec ve Dokumantasyon

- `docs/`: kalici teknik dokumanlar ve `docs/releases/` altindaki resmi surum notlari
- `docs/BULK_IMPORT_VE_PERFORMANS_REHBERI.md`: bulk yukleme, FK butunlugu, log maliyeti ve performans kararlarinin teknik kaydi
- `docs/OCR_ENTEGRASYON_REHBERI.md`: OCR motor secimi, runtime yerlesimi ve release paketleme kurallari
- `tasks/`: aktif gorev plani ve dersler
- `requirements/`: calisma ortami bagimlilik listeleri
- `scripts/`: build, release, push, temizleme ve koruma otomasyonlari

## Uretilen Ciktilar

- `release/`: yayinlanmis surumlere ait kanonik binary ve checksum ciktilari
- `dist/`: paketleme sonucunda uretilen dagitim klasorleri ve exe ciktilari
- `build/`: PyInstaller/Nuitka ara build dosyalari

## Arsiv Alani

- `Archive/debug_scripts/`, `Archive/migration/`, `Archive/one_time_fixes/`, `Archive/utils/`: bir defalik analiz ve yardimci scriptler
- `Archive/release_debug/`: kokten tasinan gecici release denemeleri, hash denemeleri ve crash raporlari

## Yerel Calisma Alani Kurali

Bu repo `@Guncelleme` altinda kullaniliyorsa, repo disindaki push/patch kopyalari artik kardes klasor olan `..\Proje_Takip_Surum_Yonetimi` altinda tutulmalidir. Boylece aktif repo ile release yardimci varliklari birbirine karismaz.
