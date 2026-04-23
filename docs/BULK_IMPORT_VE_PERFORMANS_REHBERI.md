# Bulk Import ve Performans Rehberi

Bu belge, coklu proje yukleme akisinda gorulen `FOREIGN KEY constraint failed` hatasinin kok nedenini, uygulanan cozumleri ve performans tarafinda alinmasi gereken teknik kararları toplar.

## Problem Ozeti

- Semptom: Coklu dosya secimi ile yeni proje olustururken `sqlite3.IntegrityError: FOREIGN KEY constraint failed`
- Etki: Toplu proje ekleme akisi transaction seviyesinde geri alinıyor, kullanici birden fazla dosya icin art arda hata goruyor
- Risk: Hata yalnizca UI'da degil, veri modeli seviyesinde de korunmasiz oldugu icin benzer bug baska akislarca tekrar tetiklenebilir

## Kok Neden

- Bulk dialog `Kategorisiz` secenegini veritabanina `kategori_id = 0` olarak iletiyordu
- `projeler.kategori_id` alani `kategoriler.id` alanina foreign key ile bagli
- `kategoriler` tablosunda `id = 0` kaydi yok, dogru "kategorisiz" degeri `NULL`
- Sonuc olarak yeni proje insert'i daha ilk adimda FK ihlaline dusuyordu

## Uygulanan Cozum

### Veritabani Koruma Katmani

- `database.py` icine merkezi kategori normalizasyonu eklendi
- `0`, `"0"`, bos, `None`, gecersiz veya silinmis kategori kimlikleri artik guvenli sekilde `NULL` olarak ele aliniyor
- Koruma su yazma noktalarina uygulandi:
  - `proje_ekle`
  - `dosyadan_proje_ve_revizyon_ekle`
  - `projeyi_guncelle`
  - `projeyi_kategoriye_tasi`
  - `add_kategori`

### Bulk Dialog Koruma Katmani

- `dialogs/proje_dialogs.py` icinde `Kategorisiz` secenegi `None` ile temsil ediliyor
- Kullanici editable kategori alanina olmayan bir kategori yazarsa satir dogrulama bunu hata olarak isaretliyor
- Boylece veri tabanina gecersiz kategori kimligi gonderilmeden once UI seviyesinde hata yakalaniyor

### Log Performansi ve UI Yuku

- `utils.py` tarafinda log yazimi `QueueHandler + QueueListener` ile arka plan kuyruğuna tasindi
- `ui/panels/log_panel.py` tarafinda canli log dinleme artik sekme aktifken aciliyor
- Canli log satirlari tek tek tabloya islenmek yerine kisa araliklarla toplu sekilde cizdiriliyor
- Buyuyen log dosyalarinin UI uzerindeki etkisini azaltmak icin `RotatingFileHandler` ile dosya boyutu sinirlandi

## Olcum Notlari

Asagidaki mikro olcumler ayni makinede yapildi:

- Eski senkron model benzeri olcum:
  - `5000` log kaydi
  - dosya + stream handler
  - toplam `0.2396 s`
  - kayit basina yaklasik `0.0479 ms`

- Kuyruklu model:
  - `5000` log kaydi
  - emit eden thread suresi `0.1031 s`
  - kayit basina yaklasik `0.0206 ms`

- Sonuc:
  - log cagrisi yapan ana thread uzerindeki maliyet yaklasik `%57` azaldi
  - esas kazanc, disk I/O'nun ve formatlama/yazma isinin UI thread'inden alinmasi

Ek gozlem:

- Ham dosya okuma tek basina ana darboğaz degil
- Yaklasik `12.1 MB` log dosyasi okumasi olcumde `0.0398 s` surdu
- Asil pahali kisim, buyuk log veri setinin tabloya satir satir cizdirilmesi ve canli log handler'in surekli aktif kalmasi

## Stabilite Kurallari

- UI'daki sentinelleri (`0`, bos metin, placeholder) dogrudan DB foreign key alanlarina yazma
- UI validasyonu tek savunma olmamali; DB katmaninda ikinci bir normalize/dogrulama kalkanı bulunmali
- Toplu islem akislarinda tek bir bozuk satirin tum transaction'i dusurebilecegi unutulmamali
- Canli loglama, varsayilan olarak surekli acik degil, ihtiyac halinde etkin olmali

## Canli Log Yerine Ne Kullanilabilir

Surekli akan canli log tablosu yerine veya buna ek olarak su yaklasimlar daha verimli olabilir:

- Son 100 kritik kaydi gosteren sabit boyutlu "hatanin ozeti" paneli
- DEBUG yerine default olarak `INFO` ve ustu tutan filtreli oturum logu
- Talep aninda uretilen tanilama paketi:
  - son log dosyasi
  - `PRAGMA integrity_check`
  - uygulama surumu
  - aktif veritabani yolu
- UI icinde satir satir log yerine:
  - hata sayaci
  - warning sayaci
  - son kritik hata karti
  - "Ayrintili logu ac" butonu

## Sonraki Performans Adimlari

- Revizyon ve proje listelerinde gereksiz tam yenileme yerine daha fazla parcali guncelleme
- Buyuk rapor ve onizleme akislarinda is parcacigi / worker kullanimini tek standarda baglama
- Log panelde istenirse diskten tum dosya yerine sadece son N kaydi okuyacak tail mantigi ekleme
- Buyuk bulk islerde ilerleme metriği ve satir bazli sonuc ozeti ekleme

## Gelistirme Direktifleri Icin Hazir Alan

Kullanicidan yeni direktif geldiginde asagidaki format korunmali:

- Direktif:
- Neden gerekli:
- Koda etkisi:
- Test etkisi:
- Dokumantasyon etkisi:
- Kabul kriteri:

Yeni direktifler geldikce bu belgeye eklenmeli, ardindan `README.md`, `tasks/lessons.md` ve gerekiyorsa `session.md` ile uyumlu hale getirilmelidir.
