# OCR Entegrasyon Rehberi

Bu belge, Proje Takip icin OCR motoru secimini, neden secildigini ve uygulamaya nasil entegre edilecegini kayda gecirmek icin tutulur.

## Karar Ozeti

- Varsayilan akis `dosya adi -> PDF icindeki gercek metin -> OCR fallback` olarak kalir.
- Varsayilan OCR motoru `Tesseract` olur.
- `PaddleOCR` bu repo icinde arastirildi, ancak varsayilan desktop runtime olarak secilmedi.
- Gerektiginde ikinci seviye gelismis OCR olarak `RapidOCR` ayri bir fazda degerlendirilir.

## Neden Tesseract

- Windows masaustu paketlemede daha hafif ve daha ongorulebilir.
- CPU odakli calisir; dusuk kaynakli bilgisayarlarda daha uygun davranir.
- Tek tek alan cikarmaya yonelik kullanimda yeterli dogruluk sunar.
- CLI tabanli oldugu icin PyInstaller onefile paketine gomulmesi kolaydir.
- `tur` ve `eng` dil paketleri ile mevcut belge tiplerimizi kapsar.

## Neden PaddleOCR Varsayilan Degil

- Python bagimlilik zinciri belirgin bicimde daha agir.
- Model dosyalari ve runtime yuklemesi release boyutunu ciddi arttirir.
- Diger OCR seceneklerine gore daha yuksek RAM kullanimi beklenir.
- Mevcut uygulama hedefi olan `Windows + onefile exe + dusuk donanim` senaryosuna varsayilan motor olarak fazla maliyetlidir.

## Entegrasyon Stratejisi

OCR sadece birincil cozumler yetersiz kaldiginda devreye girer:

1. Dosya adindan alanlari cikar.
2. PDF icinde secilebilir metin varsa onu kullan.
3. Hala alanlar bos ise Tesseract OCR calistir.
4. Gerekirse daha sonraki fazda gelismis OCR backend'i ekle.

Bu sayede:

- normal PDF'lerde hiz kaybi olmaz
- OCR sadece gercekten gerekli oldugunda calisir
- otomatik doldurma davranisi korunur

## Kod Yapisi

- `services/document_intelligence_service.py`
  - otomatik doldurma icin merkez orkestrator
  - PDF metni, goruntu OCR ve kaynak notu uretimini yonetir
- `services/tesseract_backend.py`
  - Tesseract CLI runtime kesfi
  - dil paketi kontrolu
  - goruntu/PDF sayfasi OCR komut cagrisi

## Runtime Yerlesimi

Bundle edilecek Tesseract runtime'i repo icinde su yerde tutulur:

```text
ocr/
└── tesseract/
    ├── tesseract.exe
    ├── *.dll
    └── tessdata/
        ├── tur.traineddata
        └── eng.traineddata
```

Notlar:

- `tesseract-5.5.2/` altindaki kaynak kod tek basina yeterli degildir.
- `tessdata/` altinda en az `tur.traineddata` veya `eng.traineddata` bulunmalidir.
- Bundle yoksa servis sistem kurulumunu ve `PATH` uzerindeki `tesseract.exe` kaydini da arar.

## Build ve Release Davranisi

- `scripts/build_onefile_release.ps1`
- `scripts/build_release.ps1`

Bu scriptler artik `ocr/tesseract/tesseract.exe` varsa runtime agacini PyInstaller paketine otomatik ekler.

Boylece:

- onefile build icinde OCR runtime self-contained olur
- dir-mode build icinde ayni klasor yapisi korunur
- runtime klasoru eksikse build yine devam eder, sadece OCR bundle edilmez

## Operasyonel Kural

- OCR, zorunlu bagimlilik degil; opsiyonel runtime olarak ele alinir.
- Runtime yoksa uygulama PDF ic metni ve dosya adi ayrisimina geri doner.
- Bu fallback davranisi test ile korunur.

## Sonraki Faz

Sadece ornek belge havuzunda Tesseract yetersiz kalirsa:

1. problemli belge tiplerini ayri klasorde topla
2. Tesseract sonucunu olc
3. ayni seti RapidOCR ile karsilastir
4. maliyet/dogruluk kazanci netse ikinci backend ekle
