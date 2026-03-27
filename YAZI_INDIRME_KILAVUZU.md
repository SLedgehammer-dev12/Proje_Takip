# Yazı Dokümanları İndirme Aracı

## 📋 Genel Bakış

Bu araç, **projeler.db** veritabanındaki yazı dokümanlarını (gelen yazı, onay yazısı, red yazısı, notlu onay yazısı vb.) bilgisayarınıza toplu olarak indirmenizi sağlar.

**Ana proje kodundan tamamen bağımsızdır.** Sadece veritabanını okur, hiçbir değişiklik yapmaz.

---

## ✨ Özellikler

- 📊 **Tüm yazı türlerini listeler** (gelen, onay, red, notlu onay, TSE vb.)
- 🔍 **Yazı türüne göre filtreleme**
- ✓ **Çoklu seçim** (Ctrl/Shift ile seçim yapabilirsiniz)
- 📁 **Alt klasörlere organize indirme** (her yazı türü ayrı klasörde)
- 📈 **İlerleme takibi** (kaç dosya indirildiğini gösterir)
- 🔒 **Salt okunur** (veritabanında değişiklik yapmaz)
- 📝 **Detaylı loglama** (yazi_indirme.log dosyasına kaydedilir)

---

## 🛠️ Kurulum

### 1. Python Gereksinimi

Python 3.8 veya üstü gereklidir. Python yüklü mü kontrol edin:

```powershell
python --version
```

### 2. Gerekli Kütüphaneleri Yükleyin

```powershell
pip install PySide6
```

### 3. Dosyaları Hazırlayın

**yazi_indirme.py** dosyası ile **projeler.db** dosyasının aynı klasörde olduğundan emin olun:

```
proje_takip/
├── projeler.db         ← Mevcut veritabanı
├── yazi_indirme.py     ← Yeni indirme aracı
└── yazi_indirme.log    ← (Otomatik oluşturulur)
```

---

## 🚀 Kullanım

### Adım 1: Programı Başlatın

```powershell
cd C:\Users\alperb.yilmaz\Desktop\proje_takip
python yazi_indirme.py
```

### Adım 2: Yazı Türünü Seçin

- Üst kısımdaki **"Yazı Türü"** açılır menüsünden filtrelemek istediğiniz türü seçin
- **"Tümü"** seçeneği tüm yazıları gösterir

### Adım 3: İndirmek İstediğiniz Yazıları Seçin

- Tabloda yazılar listelenir (Yazı No, Dosya Adı, Tür, Boyut)
- **Tek seçim:** Satıra tıklayın
- **Çoklu seçim:** `Ctrl` tuşuna basılı tutarak birden fazla satır seçin
- **Aralık seçimi:** İlk satıra tıklayın, `Shift` tuşuna basılı tutarak son satıra tıklayın
- **Tümünü seç:** "✓ Tümünü Seç" butonuna tıklayın

### Adım 4: Hedef Klasörü Belirleyin

- **"📁 Hedef Klasör Seç"** butonuna tıklayın
- Dosyaların indirileceği klasörü seçin

### Adım 5: İndirmeyi Başlatın

- **"⬇️ Seçilenleri İndir"** butonuna tıklayın
- Onay penceresinde **"Yes"** seçin
- İlerleme çubuğu indirme durumunu gösterecektir

### Adım 6: Sonuçları Görün

İndirme tamamlandığında:
- Başarılı ve hatalı dosya sayısı gösterilir
- Dosyalar seçtiğiniz klasörde **yazı türüne göre alt klasörlerde** bulunur:

```
Seçtiğiniz_Klasör/
├── Gelen/
│   ├── ABC-2024-001.pdf
│   └── ABC-2024-002.pdf
├── Onay/
│   ├── XYZ-2024-100.pdf
│   └── XYZ-2024-101.pdf
└── Red/
    └── DEF-2024-050.pdf
```

---

## 🔍 İpuçları

### Aynı İsimli Dosyalar

Eğer aynı isimde dosya varsa, program otomatik olarak numara ekler:
- `dosya.pdf`
- `dosya_1.pdf`
- `dosya_2.pdf`

### Dosya Adı Temizliği

Windows ve Linux'ta sorun yaratabilecek karakterler (`< > : " / \ | ? *`) otomatik olarak `_` ile değiştirilir.

### Loglama

Tüm işlemler **yazi_indirme.log** dosyasına kaydedilir. Hata durumunda bu dosyayı kontrol edin:

```powershell
notepad yazi_indirme.log
```

---

## ❓ Sık Sorulan Sorular

### ❌ "Veritabanı dosyası bulunamadı" hatası alıyorum

**Çözüm:** `yazi_indirme.py` dosyasını `projeler.db` ile aynı klasöre koyun veya programı o klasörden çalıştırın.

### ❌ "Veritabanında hiç yazı dokümanı bulunamadı" uyarısı alıyorum

**Çözüm:** Veritabanında henüz yazı dokümanı yok demektir. Ana projeden yazı ekleyin.

### ❓ İndirme sırasında program kapanırsa ne olur?

Program kapanmadan önce onay sorar. İndirmeyi iptal ederseniz, o ana kadar indirilen dosyalar klasörde kalır.

### ❓ Veritabanına zarar verir mi?

**HAYIR!** Program sadece okuma yapar, hiçbir veri değiştirmez veya silmez.

---

## 📊 Veritabanı Yapısı

Program aşağıdaki tabloyu kullanır:

```sql
CREATE TABLE yazi_dokumanlari (
    id INTEGER PRIMARY KEY,
    yazi_no TEXT NOT NULL UNIQUE,
    dosya_adi TEXT NOT NULL,
    dosya_verisi BLOB NOT NULL,
    yazi_turu TEXT NOT NULL
);
```

**Kolonlar:**
- `id`: Benzersiz kimlik
- `yazi_no`: Yazı numarası (örn: "ABC-2024-001")
- `dosya_adi`: Dosya adı (örn: "gelen_yazi.pdf")
- `dosya_verisi`: PDF/Word dosyasının binary verisi
- `yazi_turu`: Yazı türü (Gelen, Onay, Red, Notlu Onay vb.)

---

## 🐛 Sorun Giderme

### 1. Python PySide6 hatası

```powershell
pip install --upgrade PySide6
```

### 2. Veritabanı kilidi hatası

Ana projeyi kapatın, sonra indirme aracını çalıştırın.

### 3. İndirme sırasında "Permission denied" hatası

Hedef klasörün yazma izinlerini kontrol edin veya başka bir klasör seçin.

---

## 📝 Notlar

- **Ana projeden bağımsızdır:** Ana proje koduyla hiçbir ilişkisi yoktur
- **Güvenlidir:** Sadece okuma yapar, silme/güncelleme yapmaz
- **Performans:** Binlerce yazı olsa bile hızlı çalışır
- **Log dosyası:** Her işlem loglanır, sorun yaşarsanız kontrol edin

---

## 📧 Destek

Herhangi bir sorun yaşarsanız:
1. `yazi_indirme.log` dosyasını kontrol edin
2. Hata mesajını not edin
3. Teknik destek ile iletişime geçin

---

**Başarılı indirmeler! 🎉**
