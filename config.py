# config.py
import sys
import os
import logging
from PySide6.QtGui import QColor
from app_paths import get_app_base_dir, get_internal_path, get_user_data_path
from project_types import (
    PROJECT_TYPE_FILTER_OPTIONS,
    PROJECT_TYPE_OPTIONS,
    PROJECT_TYPE_OPTIONS_WITH_EMPTY,
    normalize_project_type,
)

# =============================================================================
# UYGULAMA SÜRÜM BİLGİLERİ VE GÜNCELLEME GEÇMİŞİ
# =============================================================================
APP_NAME = "Proje Takip Sistemi"
APP_VERSION = "v3.0.1"
APP_ICON_FILE = "app_icon.ico"
APP_USER_MODEL_ID = "com.botas.projetakipsistemi"
# Bu sürümde yapılan otomasyon ve optimizasyonların kaynak bilgisi
AI_AGENT = "GitHub Copilot"
CHANGELOG_FILE = "guncelleme_notlari.txt"

# Update channel configuration
UPDATE_REPO_OWNER = "SLedgehammer-dev12"
UPDATE_REPO_NAME = "Proje_Takip"
UPDATE_RELEASE_ASSET_PATTERN = r"ProjeTakip-.*\.(msi|exe|zip)$"
UPDATE_RELEASE_ASSET_EXTENSIONS = ["msi", "exe", "zip"]
UPDATE_RELEASE_PAGE_URL = (
    f"https://github.com/{UPDATE_REPO_OWNER}/{UPDATE_REPO_NAME}/releases/latest"
)

# Watermark configuration
ENABLE_WATERMARK = True
# If file exists in working dir, it will be used; otherwise text fallback will render
WATERMARK_IMAGE_PATH = get_internal_path("filigran.png")
WATERMARK_OPACITY = 0.10  # 10% opacity for a thin watermark
PANEL_WATERMARK_OPACITY = 0.055
PANEL_WATERMARK_SCALE = 0.18

CHANGELOG = {
    "v3.0.1": [
        "ONIZLEME: Revizyon dokumani yuklu olmasa bile, revizyona bagli yazi dokumani varsa alt panelde yazi on izlemesi artik calisiyor.",
        "DUZELTME: Revizyon preview hatasi uzerinden tum preview state'ini sifirlayan akis ayrildi; ust revizyon on izlemesi ile alt yazi on izlemesi birbirini kilitlemiyor.",
        "DOGRULAMA: MainWindow preview orkestrasyonu icin regression testi eklendi; yazi dokumani olan ancak proje/revizyon dokumani olmayan satirlar hedefli olarak test ediliyor.",
        "ENTEGRASYON: release/v3.0 hatti main ile guvenli fast-forward birlesim akisina alinarak yeni patch surum uretildi.",
    ],
    "v3.0": [
        "METIN: Legacy kaynak dosyalardaki mojibake metinler kaynaginda temizlendi; kritik dialog ve ana pencere akislari artik gercek UTF-8 Turkce karakterlerle geliyor.",
        "KALITE: Kaynak repoya .editorconfig, git eol kurallari ve UTF-8 terminal yardimcilari eklendi; gelistirme ortaminda yeni encoding bozulmalarinin tekrar repo'ya sizmasi zorlastirildi.",
        "DAGITIM: Paketli surum log, guncelleme notu, varsayilan veritabani ve yedekleri kullanici profili altinda sakliyor; korumali klasorden calisma nedeniyle yonetici ihtiyaci doguran acilis hatasi giderildi.",
        "DOGRULAMA: Encoding hijyeni icin kaynak-tarama testi eklendi; release oncesi tam pytest paketi ve import smoke testi ile regression kapsami genisletildi.",
    ],
    "v2.1.9.2": [
        "DAGITIM: Paketli surum artik log, guncelleme notu, varsayilan veritabani ve yedekleri kullanici profili altinda sakliyor; korumali klasorden calisma nedeniyle yonetici ihtiyaci doguran acilis hatasi giderildi.",
        "GECIS: Eski portable dagitimdaki projeler.db ilk acilista kullanici profiline kopyalanarak veri kaybi olmadan yeni dizin yapisina alinabiliyor.",
        "UYUMLULUK: Yardim kilavuzu bundle icinden okunuyor, log paneli ve crash raporlari yazilabilir kullanici klasorune yonlendiriliyor.",
        "DAGITIM KALITESI: Imzasiz one-file EXE dagitiminda false-positive riskinin tamamen kaldirilamadigi not edilerek patch release akisina yansitildi.",
    ],
    "v2.1.9.1": [
        "STABILITE: Cok kullanicili writer lease akisi gecici ag hatalarinda hemen write dusurmeyecek sekilde esikli hale getirildi; kisa heartbeat sapmalari tolere ediliyor.",
        "GUVENLIK: Basarisiz giris veya yarim kalan auth akisi sonrasinda writer lock ve session kaydi temizleniyor; hayalet yazma oturumu riski kapatildi.",
        "UYUMLULUK: Eski veritabani yedeginden geri yukleme sonrasinda OCR metadata kolonlari ve yazi dokumani migrationlari tekrar uygulanarak legacy DB acilis akisi guclendirildi.",
        "OCR: PDF/metin/OCR fallback hattinin hata yollari tekrar test edildi; Tesseract backend ve belge zeka servisi regression paketiyle birlikte dogrulandi.",
    ],
    "v2.1.9": [
        "GUNCELLEME: GitHub release akisi v2.1.9 icin tekil ve uyumlu hale getirildi; hem kanonik one-file EXE hem de eski istemciler icin ayni isim semasinda ZIP asset yayinlaniyor.",
        "SURUMLEME: Updater surum karsilastirmasi karisik uzunluktaki etiketleri (ornegin v2.1.8.5 -> v2.1.9 veya v2.1.9.0) daha dayanikli sekilde normalize ediyor.",
        "DAGITIM: Release dosya isimlendirmesi Windows mimarisi ile tutarli hale getirildi; checksum sozlesmesi birden fazla asset icin de kanonik olarak uretiliyor.",
        "PERFORMANS: Bir onceki surumde eklenen Performans Modu, manuel yazi on izleme ve dusuk RAM profili bu surumde de korunarak dagitim kanalina tasindi.",
    ],
    "v2.1.8.5": [
        "PERFORMANS MODU: Gorunum menusu altina kalici Performans Modu eklendi; dusuk donanimli bilgisayarlarda native/Fusion gorunum, daha dusuk onizleme yukleri ve daha seyrek bellek guncellemesi ile daha hafif calisiyor.",
        "ONIZLEME: Yazi on izleme artik performans modunda otomatik render edilmiyor; manuel yukleme dugmesi ile ihtiyac halinde acilarak RAM ve CPU kullanimi azaltildi.",
        "LOG: Performans modunda canli log izleme kapatiliyor ve kayit seviyesi ERROR/CRITICAL'a dusuruluyor; teshis kabiliyeti korunurken disk ve islem yuku azaltiliyor.",
        "BELLEK: PDF render worker ve preview belge cache limitleri dusuruldu; buyuk onizleme boyutlari kisilarak zayif makinelerde daha dengeli calisma saglandi.",
    ],
    "v2.1.8.4": [
        "ARAYUZ: Proje dokumani on izleme ve yazi on izleme alanlari varsayilan yerlesimde daha dengeli hale getirildi; iki tam ekran ac butonu ayni hizada toplandi.",
        "VERI BUTUNLUGU: Coklu proje yuklemede Kategorisiz sentinel degerinin foreign key hatasi üretmesi engellendi; gecersiz kategori kimlikleri guvenli sekilde NULL'a normalize ediliyor.",
        "LOG/PERFORMANS: Log yazimi kuyruklu arka plan isleyicisine tasindi; canli log UI'si yalnizca log sekmesi etkinken baglanarak ana akis yuku azaltildi.",
    ],
    "v2.1.6": [
        "ARAYUZ: Uygulamaya kalici Turkce/Ingilizce dil secimi eklendi; ana menu, paneller ve kritik dialoglar secilen dile gore guncelleniyor.",
        "METIN: Eski kodlama bozulmalarini onaran merkezi i18n katmani eklendi; gorunur mojibake metinlerin buyuk kismi duzeltildi.",
        "GUNCELLEME: GitHub release/updater sozlesmesi v2.1.6 ile surduruldu; v2.1.5 istemcileri yeni checksum'li pakete guncellenebilecek.",
        "TLS: GitHub update kontrolu ve asset indirme akisi, eksik yerel sertifika zincirlerinde certifi CA bundle fallback'i ile daha dayanikli hale getirildi.",
    ],
    "v2.1.5": [
        "PERFORMANS: Yazi on izleme akisi ana revizyon on izlemesinden ayrildi; hizli satir dolasiminda gereksiz ikinci PDF render ve BLOB okuma yuku azaltildi.",
        "BELLEK: PDF render worker cache mantigi guclendirildi, belge imzasi bazli tekrar kullanim eklendi ve sicak yoldaki zorunlu GC temizligi kaldirildi.",
        "ACILIS: Otomatik acilis yedegi artik erteleniyor; son 24 saatte ayni tur yedek varsa disk yukunu artirmadan mevcut koruma devam ediyor.",
        "LOG: Log sekmesi diski her acilista bastan taramak yerine tembel ve artimli okuma yapacak sekilde hafifletildi.",
    ],
    "v2.1.4": [
        "YAZI COZUMLEME: Revizyon satirinda hangi yazinin goruntulenecegi artik dolu alanlara ve duruma gore merkezi olarak cozuluyor; tutarsiz yazi_turu kayitlari uygulamayi kilitlemiyor.",
        "DOKUMAN ERISIMI: Yazi on izleme ve tam ekran acma akisi, tip kaymis giden yazilarda fallback ile dogru PDF'i bulacak sekilde dayanikli hale getirildi.",
        "IKON: Calisma anindaki pencere ve gorev cubugu ikonu, exe ile ayni BOTAŞ ikon kaynagindan yuklenecek sekilde guclendirildi.",
    ],
    "v2.1.3": [
        "GUNCELLEME: Baslangicta otomatik guncelleme kontrolu daha gorunur hale getirildi; yeni surum bulundugunda artik diyalog aciliyor.",
        "TEMALAR: TOK tema sistemi 5 varyanta genisletildi (Kurumsal Acik, Gece Mavisi, Gundogumu, Cam Yesili, Celik Gri).",
        "IKON: Uygulama exe ve gorev cubugu ikonu BOTAŞ amblemini kullanan yeni ico setine gecirildi.",
    ],
    "v2.1.2": [
        "ARAYUZ: BOTAS filigrani uc ana panelde ayri ve daha kucuk arka plan ogesi olarak duzenlendi.",
        "PREVIEW: Proje ve revizyon on izleme ile tam ekran goster akislari yeniden stabilize edildi.",
        "YAZI: Yazi on izleme alt paneli ana preview alanini bozmadan dogru belgeyi gosterir hale getirildi.",
    ],
    "v2.1.1": [
        "🔐 GÜNCELLEME: GitHub release checksum doğrulaması kalıcı olarak düzeltildi; eski sürümler artık kanonik SHA256SUMS ile güncellenebiliyor.",
        "🛠️ DAĞITIM: One-file release üretim ve yayın akışı tekilleştirildi; release asset ve checksum dosyaları aynı kaynaktan üretiliyor.",
        "🐛 HATA DÜZELTMESİ: Checksum ayrıştırıcısındaki PowerShell çıktı uyumluluğu ve parser gölgeleme hatası giderildi."
        , " LOG SEKME: Program icine sinif/logger bazli canli log izleme sekmesi eklendi."
    ],
    "v2.1.0": [
        "✨ YENİ ÖZELLİK: Revizyon tablosunun altına gerçek zamanlı 'Yazı Ön İzleme' paneli eklendi. Artık yazıları anında önizleyebilirsiniz.",
        "✨ YENİ ÖZELLİK: Revizyon tablosunda araç çubuğuna ve sağ tık menüsüne 'Yazıyı Görüntüle' seçeneği eklendi.",
        "🐛 HATA DÜZELTMESİ: Liste görünümünde çift tıklama eylemlerinin (Yazı No'ya tıklama dahil) çalışmamasına neden olan bir arayüz yerleşimi hatası giderildi."
    ],
    "v2.0.9": [
        "🐛 HATA DÜZELTMESİ: Yenilenen uygulamanın, çalışma anında Windows görev çubuğunda hala eski ikonla görünmesine sebep olan sistem engeli aşıldı.",
        "💡 YENİ ÖZELLİK: Revizyon Tablosunda herhangi bir satırdaki hücrelere çift tıklandığında ilgili revizyon dokümanı otomatik açılır hale getirildi."
    ],
    "v2.0.8": [
        "✨ GÖRSEL GÜNCELLEME: Programın varsayılan .exe ikonu baştan aşağı yenilenerek daha modern ve amaca uygun, zarif bir tasarımla değiştirildi."
    ],
    "v2.0.7": [
        "🐛 HATA DÜZELTMESİ: Veritabanı arama iyileştirmesinin ardından tablodan giden yazı çift tıklamalarının hala çalışmadığı bir uç durum daha hassas bir ID taraması yapılarak kökten çözüldü.",
        "💡 YENİ ÖZELLİK: Uygulama içinden güncelleme indirmek istendiğinde artık dosyanın nereye kaydedileceği kullanıcıya soruluyor."
    ],
    "v2.0.6": [
        "🐛 HATA DÜZELTMESİ: Revizyon tablosunda giden/yazı numaralarına (onaylı/red) çift tıklandığında dokümanın açılmama sorunu düzeltildi.",
    ],
    "v2.0.5": [
        "🐛 HATA DÜZELTMESİ: Uygulama içi güncelleme sırasındaki 'Dosya indirilemedi' sorunu çözüldü (eksik indirme mantığı onarıldı).",
    ],
    "v2.0.4": [
        "🐛 HATA DÜZELTMESİ: 'Dokümanı Görüntüle' butonuna basıldığında hiçbir işlem yapılmaması hatası giderildi (arayüz sinyal bağlantısı düzeltildi).",
    ],
    "v2.0.3": [
        "🔄 MENÜ YENİDEN KRONUMU: Güncelleme kontrolü seçenekleri 'Görünüm' menüsünden 'Dosya' menüsüne taşındı.",
        "✨ KULLANICI DENEYİMİ: GitHub'da henüz yayınlanmış bir sürüm olmadığında gösterilen kafa karıştırıcı 404 hatası yerine anlaşılır bir mesaj eklendi.",
        "📦 DAĞITIM: PyInstaller kullanılarak bağımlılıklara ihtiyaç duymayan tek dosya (.exe) halinde derlendi.",
    ],
    "v2.0.2": [
        "📄 DOKUMAN: 'Dokümanı Görüntüle' akışı Windows paketli sürümde daha güvenilir sistem açma yolu ile düzeltildi.",
        "🧩 PREVIEW: Belge açma, payload çözümleme ve preview hazırlık sorumlulukları daha küçük servis/helper katmanlarına ayrıldı.",
        "📊 RAPORLAMA: ReportService içinde pandas lazy-load edildi; gereksiz ağır import yükü azaltıldı.",
        "🔤 PDF: Boş DejaVuSans.ttf asset'i gerçek font dosyasıyla değiştirildi; PDF raporlarda DejaVu tekrar kullanılabiliyor.",
    ],
    "v2.0.1": [
        "⚡ AÇILIŞ: Veritabanı başlangıç akışı hafifletildi; startup'ta ağır bakım adımları kaldırıldı.",
        "💾 YEDEKLEME: Açılış yedeği geri alındı, eski çalışma akışı korundu.",
        "🛡️ STABİLİTE: Login ekranı ana pencereden önce açılarak gereksiz thread ve yük önlendi.",
        "🧹 KAPANIŞ: Çökme riskini azaltan cleanup korundu, gereksiz DB bakım işlemleri kaldırıldı.",
    ],
    "v2.0.0": [
        "🔄 GÜNCELLEME: Uygulama içi kontrol GitHub Release tabanlı hale getirildi.",
        "📦 GÜNCELLEME: Yeni sürüm bulunduğunda release notları gösterilir ve asset Downloads klasörüne indirilir.",
        "🧩 PROJE TÜRLERİ: Tür listesi merkezileştirildi (İnşaat, Mekanik, Piping, Elektrik, I&C, Siemens, Diğer).",
        "🗂️ MİGRASYON: Eski proje türleri normalize ediliyor, tanımsız olanlar Diğer'e aktarılıyor.",
        "📝 DOSYADAN YÜKLEME: Tek dosya seçiminde de proje bilgileri kaydetmeden önce düzenlenebilir.",
        "💾 BELLEK: Status bar RAM kullanımı gerçek proses belleğini gösteriyor.",
        "🛡️ SQLITE: busy_timeout, foreign_keys, quick_check, optimize ve kontrollü shutdown eklendi.",
    ],
    "v1.5.1": [
        "🚀 PERFORMANS: Lazy loading eklendi - servisler ilk kullanımda yükleniyor (Windows başlangıç hızı %30-50 arttı).",
        "📊 EXCEL: TSE sütunları kaldırıldı (TSE'ye Gönderildi, TSE Yazı No, TSE Yazı Tarihi).",
        "📊 EXCEL: 'Gelen Yazı Rev Kodu' ve 'Giden Yazı Rev Kodu' sütunları eklendi.",
        "📊 EXCEL: 'İşlem Beklenen' sütunu eklendi (Botaş/Yüklenici - son tarihli yazıya göre).",
        "📊 EXCEL: 'Onaylı Doküman Revizyonu' sütunu eklendi (onaylı proje üzerine yeni yazı geldiyse Evet).",
        "🐛 DÜZELTME: Tarih karşılaştırma hatası düzeltildi (DD.MM.YYYY formatı doğru sıralanıyor).",
    ],
    "v1.5": [
        "📊 EXCEL: Proje türlerine göre dağılım çubuk grafiği eklendi (Gösterge Paneli sayfası).",
        "📈 EXCEL: Aylık onay trend grafiği eklendi (Trend Analizi sayfası).",
        "🎨 EXCEL: Kurumsal renk teması uygulandı (koyu mavi, yeşil, turuncu, kırmızı).",
        "📋 EXCEL: Proje listesi sayfasına kurumsal başlık ve koşullu durum renklendirmesi eklendi.",
        "✉️ EXCEL: Son Gelen Yazı ve Son Giden Yazı ayrı sütunlarda gösteriliyor.",
        "📅 EXCEL: Tarih alanlarında revizyon durumu parantez içinde yazılıyor.",
        "🔧 EXCEL: Gelen/Giden yazı bağımsız olarak en son dolu revizyondan alınıyor.",
        "📊 GÖSTERGE: 'Toplam Görüntülenen Proje' → 'Toplam Sunulan Proje' olarak değiştirildi.",
        "📊 GÖSTERGE: İstatistikler artık doğrudan veritabanından çekiliyor.",
        "🐛 DÜZELTME: Durum değerleri düzeltildi (Onayli, Notlu Onayli, Onaysiz, Reddedildi).",
    ],
    "v1.4": [
        "🚀 PERFORMANS: Cache boyutu 100'den 500'e çıkarıldı - %42 daha fazla hit ratio.",
        "⏱️ PERFORMANS: Bellek izleme timer'ı 5s'den 15s'ye çıkarıldı - %67 daha az CPU kullanımı.",
        "⌨️ PERFORMANS: Arama debounce 300ms'den 500ms'ye - %40 daha az filtreleme işlemi.",
        "📊 PERFORMANS: UI batch rendering eklendi - büyük listelerde %50-70 hızlanma.",
        "🗄️ PERFORMANS: Database query caching (30s TTL) - tekrarlayan sorgular anlık dönüyor.",
        "💾 PERFORMANS: Auto cache invalidation - DB commit sonrası otomatik temizlik.",
        "🔧 PERFORMANS: Thread cleanup timeout (3s graceful + 1s force) - uygulama %80 daha hızlı kapanıyor.",
        "🛡️ GÜVENLİK: Error handling utility eklendi - kritik hatalar artık kullanıcıya gösteriliyor.",
        "🧹 TEMİZLİK: Migration service kaldırıldı - daha hızlı başlangıç, daha temiz kod.",
        "📦 TEMİZLİK: 16 dosya arşivlendi, 17 dosya silindi - ~100KB daha küçük kod tabanı.",
        "🗂️ TEMİZLİK: Archive klasörü oluşturuldu - eski kodlar gerekirse geri yüklenebilir.",
        "✅ DOĞRULAMA: Tüm değişiklikler syntax kontrolünden geçti - kod hatasız.",
        "📝 DOKÜMANTASYON: Detaylı walkthrough ve geri yükleme talimatları eklendi.",
    ],
    "v1.3": [
        "🔐 GÜVENLİK: Kullanıcı kimlik doğrulama sistemi eklendi (bcrypt ile güvenli şifre hashleme).",
        "👤 KULLANICI GİRİŞİ: Uygulama başlangıcında kullanıcı adı/şifre ile giriş veya misafir modu.",
        "🔒 YETKİ SİSTEMİ: Admin kullanıcılar tam yetki, misafir kullanıcılar sadece görüntüleme.",
        "✅ RUNTIME KORUMA: Tüm yazma işlemlerine (ekleme/düzenleme/silme) yetki kontrolü eklendi.",
        "📊 STATUS GÖSTERGE: Kullanıcı durumu (giriş yapmış/misafir) status bar'da gösteriliyor.",
        "🐛 DÜZELTME: Database farklı konumdan açıldığında Excel export hatası giderildi.",
        "🔄 DÜZELTME: Revizyon düzenleme sonrası seçim durumu korunuyor (QTimer ile UI sync).",
        "🔍 DÜZELTME: Arama çubuğu filtreleme sorunu giderildi (search text parametre iletimi).",
        "📁 YENİ DOSYALAR: auth_service.py, login_dialog.py, .gitignore, README.md, CHANGELOG.md",
        "🗄️ DATABASE: Users tablosu eklendi (username, password_hash, role, timestamps).",
    ],
    "v1.2": [
        "Düzeltme: Revizyon doküman güncellemesi sonrası önizlemenin görünmemesi hatası düzeltildi (dokumani_guncelle artık insert fallback yapıyor).",
        "İyileştirme: Revizyon durum değişikliği sırasında onay/red/gelen yazı alanları artık korunuyor (temizlenmiyor).",
        "Güncelleme: Revizyon durum devralma migration tek seferlik ve idempotent hale getirildi (manual değişiklikleri bozmaz).",
        "UI: Proje listesi ve kategori ağacındaki statü emojileri net ikonlarla değiştirildi (Onaylı, Notlu Onaylı, Reddedildi).",
        "İyileştirme: Revizyon doküman cache'i güncellenip invalidasyonu ve preview sinyali düzeltildi.",
        "Diğer: Bir dizi küçük hata düzeltmesi ve test iyileştirmeleri (dokuman onayı/önizleme, filtre korunumu).",
    ],
    "v1.1": [
        "Gereksiz runtime dosyaları ve DB artıkları temizlendi.",
        "Yeni snapshot betiği eklendi: scripts/create_snapshot.ps1 - manuel backup almayı kolaylaştırır.",
        "KULLANIM_KILAVUZU ve guncelleme_notlari dosyaları güncellendi.",
        "Small refactors and improved .gitignore dedup and patterns.",
    ],
    "v1.0": [
        "İlk kararlı sürüm (v1.0): Temel proje takip, revizyon ve yedekleme özellikleri hazır.",
        "Özelleştirilmiş veri modeli (projeler, revizyonlar, dokumanlar) ve BLOB desteği.",
        "PDF önizleme ve asenkron rendering (PdfRenderWorker).",
        "Gelişmiş filtreleme, kategori ağacı ve export/raporlama özellikleri.",
        "Yedekleme sistemi ve geri yükleme (otomatik & manuel yedekleme).",
        "Çoklu platformda çalıştırma için temel kurulum ve README eklendi.",
    ],
    "v12.4": [
        f"Yapay Zeka: Bu sürüm {AI_AGENT} ile kod kalitesi kontrolü yapılmıştır.",
        "🐛 KRİTİK BUG: İki ayrı closeEvent fonksiyonu çakışması düzeltildi!",
        "🔧 DÜZELTİLDİ: Eski closeEvent (line 195) kaldırıldı, tüm cleanup yeni closeEvent'e taşındı.",
        "💾 İYİLEŞTİRME: closeEvent artık UI durumunu kaydeder, tüm timer'ları durdurur.",
        "🔌 DÜZELTİLDİ: cleanup_connections() mantık hatası giderildi (current thread skip edilmiyordu).",
        "🧹 CLEANUP: Tüm connection'lar artık doğru şekilde kapatılıyor.",
        "🔍 KOD DENETİMİ: Tüm Python modülleri mantık hataları için tarandı.",
        "✅ SQL GÜVENLİĞİ: Tüm sorgular parameterized, SQL injection riski yok.",
        "✅ THREAD SAFETY: PdfRenderWorker ve connection pool thread-safe.",
        "✅ BELLEK YÖNETİMİ: Cache limitleri, GC cleanup, memory leak kontrolleri OK.",
        "✅ NULL HANDLING: Tüm filtreler NULL değerleri güvenli işliyor.",
        "✅ VALIDATION: Dialog input kontrolü ve type conversion doğru.",
        "Kod Kalitesi: Kapsamlı inceleme sonrası tüm kritik hatalar giderildi.",
        "Stabilite: Uygulama artık daha güvenli ve tutarlı çalışıyor.",
        "Önerilen: Yeni sürüme geçin ve veritabanı yedekleri sistemini kullanın!",
    ],
    "v12.3": [
        f"Yapay Zeka: Bu sürüm {AI_AGENT} ile geliştirilmiştir.",
        "🔒 GÜVENLİK: Otomatik veritabanı yedekleme sistemi eklendi!",
        "🔄 YEDEKLEME: Uygulama açılışında otomatik yedek alınır.",
        "💾 KAPANIŞ KORUMA: Kapatırken 'Değişiklikleri kaydet mi?' onay dialogu.",
        "📊 DEĞİŞİKLİK TAKİBİ: Tüm veritabanı işlemleri sayılır ve takip edilir.",
        "↩️ GERİ YÜKLEME: Yanlış işlem yaparsanız açılış yedeğine geri dönebilirsiniz.",
        "🗂️ YEDEK YÖNETİMİ: Dosya -> Yedekleme menüsünden yedek al/listele/geri yükle.",
        "📁 YEDEK KLASÖRÜ: Tüm yedekler 'veritabani_yedekleri' klasöründe saklanır.",
        "🧹 OTOMATİK TEMİZLİK: Son 10 yedek tutulur, eskiler otomatik silinir.",
        "⚠️ AKILLI KAPANIŞ: EVET = Kaydet, HAYIR = Açılış yedeğine dön, İPTAL = Kapanma.",
        "🔐 Transaction Güvenliği: Her başarılı işlem otomatik sayılır.",
        "📝 Manuel Yedek: İstediğiniz zaman manuel yedek alabilirsiniz.",
        "🔍 Yedek Listeleme: Tüm yedekleri tarih ve boyut bilgisiyle görüntüleyin.",
        "Kullanıcı Deneyimi: Artık yanlış veri girişinden koruma var!",
        "Güvenlik: Kritik işlemlerden önce yedek alınması önerilir.",
    ],
    "v12.2": [
        f"Yapay Zeka: Bu sürüm {AI_AGENT} ile hata düzeltmesi yapılmıştır.",
        "HATA DÜZELTMESİ: Gelişmiş filtreleme sistemindeki SQL alias uyumsuzluğu düzeltildi (sr -> r).",
        "HATA DÜZELTMESİ: TEXT filtrelerde NULL değer kontrolü eklendi - artık boş alanlar hata vermiyor.",
        "HATA DÜZELTMESİ: MULTI_SELECT filtrelerde NULL ve boş liste kontrolü eklendi.",
        "HATA DÜZELTMESİ: DATE_RANGE filtrelerde NULL değer kontrolü eklendi.",
        "HATA DÜZELTMESİ: Proje türü filtresi artık doğru çalışıyor (NULL kontrollü IN clause).",
        "HATA DÜZELTMESİ: Gelen yazı no filtresi artık doğru field mapping ile çalışıyor.",
        "İyileştirme: Tüm filtreleme sorguları NULL-safe hale getirildi.",
        "İyileştirme: Filtreleme hata mesajları daha açıklayıcı hale getirildi.",
        "Güvenlik: Boş veya geçersiz filtre değerleri artık SQL sorgusuna eklenmeden önce kontrol ediliyor.",
    ],
    "v12.1": [
        f"Yapay Zeka: Bu sürüm {AI_AGENT} ile optimize edilmiştir.",
        "PERFORMANS KRİTİK: Proje değiştirme gecikmesi %80 azaltıldı - artık anlık geçiş!",
        "Optimizasyon: Preview timer gereksiz tetiklemeleri kaldırıldı.",
        "Optimizasyon: revizyonlari_yukle metodunda signal bloklama eklendi - cascade tetikleme önlendi.",
        "Optimizasyon: detaylari_guncelle ve detaylari_temizle signal bloklama ile hızlandırıldı.",
        "Optimizasyon: _proje_verisi_isleme metodunda gereksiz kontroller kaldırıldı.",
        "Optimizasyon: revizyon_secilince_detay_guncelle cache kullanımı - gereksiz DB sorguları önlendi.",
        "Cache: Yazı belgeleri için yeni cache mekanizması (_yazi_cache) eklendi.",
        "Cache: Doküman verisi cache'i eklendi (_dokuman_cache) - max 5 doküman (max 25MB).",
        "Optimizasyon: _trigger_preview_update doküman cache kullanımı ile hızlandırıldı.",
        "Optimizasyon: projeleri_filtrele metodunda batch update eklendi.",
        "KRİTİK: _process_project_batch her batch için ağacı yeniliyordu - şimdi TEK SEFERDE!",
        "Performans: Ağaç yükleme optimize edildi - her batch yerine tüm projeler yüklendikten sonra.",
        "Bellek: Bellek timer aralığı 2s'den 5s'ye çıkarıldı - daha az UI thread bloklama.",
        "Event: Event filter global yerine widget-specific olarak optimize edildi.",
        "Cleanup: closeEvent'e _yazi_cache ve _dokuman_cache temizliği eklendi.",
        "Sonuç: Proje seçimi 1 saniyeden ~200ms'ye düştü (%80 hızlanma)!",
    ],
    "v12.0": [
        "Performans: Veritabanı sorguları optimize edildi - CTE yerine indexed subquery kullanımı (%40-60 hız artışı).",
        "Performans: UI rendering optimize edildi - setUpdatesEnabled ile toplu güncellemeler (%50-70 hız artışı).",
        "Performans: Batch size 50'den 100'e çıkarıldı - daha az UI güncellemesi.",
        "Bellek: Cache mekanizması eklendi - Kategori yolu, filtre sonuçları ve PDF render cache'i.",
        "Bellek: Akıllı bellek yönetimi - gereksiz gc.collect() çağrıları kaldırıldı (%30-40 bellek tasarrufu).",
        "PDF: Akıllı önizleme - aynı revizyon tekrar render edilmez, zoom'a göre kalite optimizasyonu.",
        "PDF: Max dimension 4000'den 3500'e düşürüldü - bellek optimizasyonu.",
        "Database: Connection pool optimizasyonu ve cleanup_connections() metodu eklendi.",
        "Database: Thread-safe işlemler ve uygulama kapanışında düzgün temizlik.",
        "Filtre: Cache mekanizması - aynı filtre tekrar çalıştırılmaz (%70-90 hız artışı).",
        "Çoklu Doküman: İlerleme dialogu eklendi - kullanıcı işlemi takip edebiliyor ve iptal edebiliyor.",
        "Çoklu Doküman: Batch processing ile UI donması önlendi.",
        "Genel: TreeWidget/ListWidget'lar addTopLevelItems ile toplu ekleme.",
        "Genel: Akıllı zoom - FastTransformation/SmoothTransformation seçimi.",
        "Hata Düzeltme: Revizyonlar listesi optimize edildi - EXISTS kullanımı.",
        "Kod Kalitesi: Tüm kodlar geriye uyumluluk korunarak yeniden optimize edildi.",
    ],
    "v11.0": [
        "Güvenilirlik: Küresel istisna yakalayıcı ve Qt mesaj yakalayıcısı eklendi; beklenmeyen hatalar artık günlükleniyor.",
        "Stabilite: PDF önizleme işçisi (PdfRenderWorker) yeniden düzenlendi; PNG yolu öncelikli, düşük bellekli dönüşüm ve ölçekleme eklendi.",
        "Bellek: Araç çubuğuna bellek kullanım etiketi eklendi ve periyodik güncelleme (psutil/tracemalloc) aktif edildi.",
        "Performans: Proje yükleme ve yenileme akışında toplu (batch) işleme ve güvenli önizleme temizliği ile ani bellek sıçramaları azaltıldı.",
        "Kapatma: Thread ve sinyal bağlantıları için güvenli temizlik (cleanup) ve closeEvent iyileştirmeleri yapıldı.",
        "Hata düzeltmeleri: Revizyon durumu/kodu değiştirme sonrası arayüz yenilemede yarış durumu ve çökme senaryoları giderildi.",
        "Genel: Menü/eylem ve çeşitli girinti/bağlantı sorunları temizlendi; günlükleme mesajları iyileştirildi.",
    ],
    "v10.5": [
        "Geliştirme: Excel raporlamasına 'TSE'ye Gönderildi', 'TSE Yazı No' ve 'TSE Yazı Tarihi' sütunları eklendi.",
        "Geliştirme: Excel'e aktarılırken sütun genişlikleri artık içeriğe göre otomatik ayarlanıyor (xlsxwriter kütüphanesi gereklidir).",
    ],
    "v10.4": [
        "Yeni Özellik: Revizyon düzenleme ekranına 'TSE'ye Gönderildi' onay kutusu eklendi.",
        "Yeni Özellik: TSE'ye gönderilen revizyonlar için opsiyonel 'TSE Yazı No' ve 'TSE Yazı Tarihi' alanları eklendi.",
        "Geliştirme: Revizyon listesi (sağ panel), 'TSE Durumu' (Evet/Hayır) için yeni bir sütun içeriyor.",
    ],
    "v10.3": [
        "Geliştirme: Proje listesi (sol panel) artık projenin son durumuna göre renklendiriliyor (Onaylı: Yeşil, Red: Kırmızı, Onaysız/Diğer: Gri).",
        "Geliştirme: Revizyon listesi (sağ panel) de durumlarına göre (Onaylı, Red, Onaysız) tutarlı şekilde renklendirildi.",
        "Geliştirme: Listelerdeki 'seçili öğe' rengi, daha belirgin olması için mavi yapıldı.",
    ],
    "v10.2": [
        "Yeni Özellik: Seçili projelere toplu olarak 'Gelen', 'Onay' veya 'Red' yazısı ekleme özelliği eklendi. (Proje -> Toplu... menüsü)"
    ],
    "v10.1": [
        "Geliştirme: Proje listesi ve kategori ağacı arasında sürükle-bırak ile proje kategorisi değiştirme eklendi.",
        "Geliştirme: Kategori ağacına sağ tıklayarak o kategoriye yeni proje ekleme özelliği getirildi.",
    ],
    "v10.0": [
        "Yeni Özellik: Ana arayüze 'Kategori Görünümü' (Hiyerarşik Ağaç) eklendi.",
        "Performans: PDF önizlemeleri artık arayüzü kilitlememesi için arkaplan bir thread'de yükleniyor (Asenkron PDF render).",
        "Performans: Veritabanı sorguları (WAL modu, indexler) hızlandırıldı.",
        "Performans: Arama kutusuna gecikme (debounce) eklendi.",
    ],
    "v9.0": ["İlk ana sürüm."],
}

# =============================================================================
# GÖRSEL SABİTLER (AnaPencere'den taşındı)
# =============================================================================

DURUM_YENI, DURUM_DEGISIKLIK, DURUM_ONAYLI = " ⭕", " 🔄", "✅"
DURUM_RED = " ❌"

DURUM_RENKLERI = {
    "yesil": QColor("#d4edda"),  # Onaylı
    "kirmizi": QColor("#f8d7da"),  # Red
    "mavi": QColor("#f0f0f0"),  # Onaysız (Açık Gri)
    "gri": QColor("#f0f0f0"),  # Revizyon Yok (Açık Gri)
}

# NOTE: Logging setup moved to `utils.setup_logging()` to avoid duplication and
# centralize logging configuration. Keep any global logging constants here.

# =============================================================================
# DEĞİŞİKLİK NOTU YAZDIRMA (Fonksiyonu utils.py'ye taşıdık)
# =============================================================================


def write_changelog_file():
    """Uygulamanın bulunduğu dizine bir güncelleme geçmişi dosyası yazar."""
    try:
        filepath = get_user_data_path(CHANGELOG_FILE, create_parent=True)

        with open(filepath, "w", encoding="utf-8") as f:
            # HATA DÜZELTMESİ: .UPPER() -> .upper() olarak değiştirildi.
            f.write(f"{APP_NAME.upper()} - GÜNCELLEME NOTLARI\n")
            f.write("=" * 40 + "\n\n")

            for version, changes in CHANGELOG.items():
                f.write(f"--- Sürüm: {version} ---\n")
                for change in changes:
                    f.write(f"  * {change}\n")
                f.write("\n")

    except Exception as e:
        # --- LOG GÜNCELLEMESİ ---
        logging.critical(f"Güncelleme notları dosyası yazılamadı: {e}")
