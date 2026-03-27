# Proje Takip Sistemi – Kullanım Kılavuzu

Bu kılavuz, uygulamanın temel özelliklerini hızlıca öğrenmeniz için hazırlanmıştır.

## 1. Arayüz Genel Yapısı
- Sol panel: Proje listesi ve Kategori Görünümü (sekmeler)
- Sağ üst: Revizyonlar ve detaylar
- Sağ alt: PDF önizleme alanı (yakınlaştır/uzaklaştır destekli)
- Üst: Menü çubuğu ve araç çubuğu (bellek göstergesi)

## 2. Sekmeler
- "Tüm Projeler": Düz liste halinde projeler
- "Kategori Görünümü": Projeleri hiyerarşik kategori ağacında gör ve sürükle-bırak ile taşı
- "Gösterge Paneli": Toplam, onaylı, red, onaysız sayıları ve tür dağılımı
- "Kullanım Kılavuzu": Bu sayfa

## 3. Arama ve Filtreleme
- Arama kutusuna yazdıkça filtrelenir (Ctrl+F kısayolu).
- Gelişmiş filtreler: Gelişmiş filtre dialogundan çeşitli alanlara göre filtre uygulayın.
- "Filtre: X aktif" göstergesi, aktif filtre sayısını gösterir; temizlemek için ilgili menüyü kullanın.

## 4. Proje ve Revizyon İşlemleri
- Proje ekleme/düzenleme/silme: Bağlam menüleri ve ilgili diyaloglar ile yönetilir.
- Kategori taşıma: Kategori Görünümü'nde projeleri sürükleyip kategoriye bırakın.
- Revizyon durumu ve kodu: Revizyonu seçip "Durumu Değiştir" işlemi ile güncelleyin.

## 5. PDF Önizleme
- Revizyon seçildiğinde PDF önizlemesi otomatik yüklenir.
- Yakınlaştırma: Ctrl + Fare Tekerleği
- Performans için büyük PDF'lerde önizleme ölçeklendirilir.

## 6. Raporlama ve Dışa Aktarma
- Excel'e aktarım: Menüden dışa aktarım; xlsxwriter varsa otomatik sütun genişletme yapılır.

## 7. Kısayollar
- Ctrl+F: Arama kutusuna odaklan
- F5 / Ctrl+R: Yenile

## 8. Sorun Giderme
- Günlük dosyası: `proje_takip.log` (uygulama klasöründe)
- Hata durumunda bu dosyayı inceleyebilir veya paylaşabilirsiniz.
  
Not: Uygulama günlükleri UTF-8 (BOM) formatında yazılmaktadır; bazı eski metin görüntüleyiciler dosyayı farklı bir kodlama ile açınca Türkçe karakterler bozulabilir (ör. "başarıyla" yerine "ba�ar�yla"). Günlük dosyasını doğru şekilde görüntülemek için aşağıdakileri kullanabilirsiniz:

- PowerShell (UTF-8 ile oku):
	```powershell
	Get-Content -Path .\proje_takip.log -Encoding utf8 -Tail 50
	```
- Notepad++ / VS Code gibi UTF-8 destekli editörleri kullanın.
- Windows Notepad bazı eski sürümlerde BOM kullanılmadan UTF-8 algılamayabilir; bu durumda `-Encoding utf8` ile PowerShell gösterimi önerilir.

## 9. İpuçları
- Kategori kimlikleri veritabanında tutulur; sürükle-bırak ile hızlı kategori yönetimi yapın.
- PDF önizleme sırasında başka revizyona geçtiyseniz sistem doğru revizyonu kontrol eder.

## 10. Gelişmiş: Snapshot & Temizlik (v1.2)

- Çalışma dizininde gereksiz geçici dosyalar veya çalışma DB'leri oluşabilir. Proje temizlik ve güvenlik amaçlı olarak `scripts/cleanup_repo.py` komut dosyası ile çalıştırılabilir.
- Manuel yedekleme (snapshot) almak için `scripts/create_snapshot.ps1` betiğini kullanabilirsiniz (PowerShell). Betik otomatik olarak `backup/manual-<timestamp>` adında bir branch oluşturur ve `pre-change-manual-<timestamp>` etiketi ekler.
- Örnek PowerShell çalıştırma:
```powershell
# Yeni bir snapshot al
.\scripts\create_snapshot.ps1

# Veya elle, aynı işlemi uygularsanız (örnek komut)
git checkout -b backup/manual-$(Get-Date -Format "yyyyMMdd-HHmmss")
git tag -a pre-change-manual-$(Get-Date -Format "yyyyMMdd-HHmmss") -m "Manual pre-change snapshot $(Get-Date -Format \"yyyyMMdd-HHmmss\")"
```

- Geri dönmek isterseniz (non-destructive):
```powershell
# Çalışma dizininizi snapshot'a eşitle (geçerli dalı değiştirir)
git restore --source backup/manual-20251125-195036 -- .
```

---
Sürüm: v1.2
