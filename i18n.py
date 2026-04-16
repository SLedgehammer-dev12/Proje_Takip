from __future__ import annotations

import re
from typing import Callable, Optional

from PySide6.QtCore import QEvent, QLocale, QObject, QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTabWidget,
    QTableWidget,
    QTreeWidget,
    QWidget,
)

from config import APP_NAME


LANGUAGE_SETTING_KEY = "ui/language"
LANGUAGE_TURKISH = "tr"
LANGUAGE_ENGLISH = "en"

_SOURCE_TEXT_PROPERTY = "_i18n_source_text"
_SOURCE_TOOLTIP_PROPERTY = "_i18n_source_tooltip"
_SOURCE_PLACEHOLDER_PROPERTY = "_i18n_source_placeholder"
_SOURCE_WINDOW_TITLE_PROPERTY = "_i18n_source_window_title"
_SOURCE_TITLE_PROPERTY = "_i18n_source_title"
_SOURCE_INFO_TEXT_PROPERTY = "_i18n_source_info_text"
_SOURCE_DETAILED_TEXT_PROPERTY = "_i18n_source_detailed_text"
_SOURCE_TAB_TEXTS_PROPERTY = "_i18n_source_tab_texts"
_SOURCE_COMBO_ITEMS_PROPERTY = "_i18n_source_combo_items"
_SOURCE_TABLE_HEADERS_PROPERTY = "_i18n_source_table_headers"
_SOURCE_TREE_HEADERS_PROPERTY = "_i18n_source_tree_headers"

_active_language = LANGUAGE_TURKISH
_event_filter: Optional[QObject] = None
_patches_installed = False

_MOJIBAKE_REPLACEMENTS = (
    ("Ã¼", "ü"),
    ("Ãœ", "Ü"),
    ("Ã¶", "ö"),
    ("Ã–", "Ö"),
    ("Ã§", "ç"),
    ("Ã‡", "Ç"),
    ("Ä±", "ı"),
    ("Ä°", "İ"),
    ("ÅŸ", "ş"),
    ("Å", "Ş"),
    ("ÄŸ", "ğ"),
    ("Ä", "Ğ"),
    ("â€™", "’"),
    ("â€œ", '"'),
    ("â€", '"'),
    ("â€˜", "'"),
    ("â€”", "-"),
    ("â€“", "-"),
    ("â†’", "→"),
    ("âœ…", "✅"),
    ("âœ—", "✗"),
    ("âœ¨", "✨"),
    ("âœ‰ï¸", "✉️"),
    ("âš¡", "⚡"),
    ("âš ï¸", "⚠️"),
    ("âŒ¨ï¸", "⌨️"),
    ("â±ï¸", "⏱️"),
    ("â—", "●"),
    ("Ã—", "×"),
    ("ğŸ”“", "🔒"),
    ("ğŸ‘¤", "👤"),
    ("ğŸ’¡", "💡"),
    ("ğŸ’¾", "💾"),
    ("ğŸ“„", "📄"),
    ("ğŸ“Š", "📊"),
    ("ğŸ“‹", "📋"),
    ("ğŸ“", "📁"),
    ("ğŸ“", "📝"),
    ("ğŸ“¥", "📥"),
    ("ğŸ“¤", "📤"),
    ("ğŸ“¬", "📬"),
    ("ğŸ”", "🔍"),
    ("ğŸ”„", "🔄"),
    ("ğŸ”", "🔐"),
    ("ğŸ”’", "🔒"),
    ("ğŸ”§", "🔧"),
    ("ğŸš€", "🚀"),
    ("ğŸ› ï¸", "🛠️"),
    ("ğŸ§©", "🧩"),
    ("ğŸ§¹", "🧹"),
    ("ğŸ›", "🐛"),
    ("ğŸ—‚ï¸", "🗂️"),
)

_EN_TRANSLATIONS = {
    APP_NAME: "Project Tracking System",
    "Proje Takip Sistemi - Giriş": "Project Tracking System - Sign In",
    "Ana Araç Çubuğu": "Main Toolbar",
    "&Dosya": "&File",
    "Yeni Veritabanı Oluştur...": "Create New Database...",
    "Veritabanı Aç...": "Open Database...",
    "Son Kullanılan Dosyalar": "Recent Files",
    "Excel'e Aktar": "Export to Excel",
    "Takip Listesini Excel'e Aktar...": "Export Tracking List to Excel...",
    "Projeleri Klasöre Çıkar...": "Export Projects to Folder...",
    "Yedekleme": "Backup",
    "Manuel Yedek Al": "Create Manual Backup",
    "Yedekten Geri Yükle...": "Restore from Backup...",
    "Yedekleri Listele...": "List Backups...",
    "🔄 Güncellemeleri Kontrol Et...": "🔄 Check for Updates...",
    "Başlangıçta güncellemeleri kontrol et": "Check for updates at startup",
    "Çıkış": "Exit",
    "&Proje": "&Project",
    "Yeni Proje": "New Project",
    "Dosyadan Proje Oluştur...": "Create Project from File...",
    "Gelen Yazıdan Proje Oluştur...": "Create Project from Incoming Letter...",
    "Giden Yazıdan Proje Oluştur...": "Create Project from Outgoing Letter...",
    "Seçili Projeyi Düzenle...": "Edit Selected Project...",
    "Seçili Projeyi Sil": "Delete Selected Project",
    "Seçili Projelere Toplu Gelen Yazı Ekle...": "Add Incoming Letter to Selected Projects...",
    "Seçili Projelere Toplu Onay Yazısı Ekle...": "Add Approval Letter to Selected Projects...",
    "Seçili Projelere Toplu Notlu Onay Yazısı Ekle...": "Add Approval with Notes Letter to Selected Projects...",
    "Seçili Projelere Toplu Red Yazısı Ekle...": "Add Rejection Letter to Selected Projects...",
    "&Revizyon": "&Revision",
    "Yeni Revizyon Yükle...": "Upload New Revision...",
    "Seçili Revizyonu Düzenle...": "Edit Selected Revision...",
    "Seçili Revizyonu Sil...": "Delete Selected Revision...",
    "Revizyonu Onayla...": "Approve Revision...",
    "Revizyonu Notlu Onayla...": "Approve Revision with Notes...",
    "Revizyonu Reddet...": "Reject Revision...",
    "Revizyon Durumunu Düzelt...": "Fix Revision Status...",
    "Takip Notu Ekle/Güncelle...": "Add/Update Tracking Note...",
    "Takip İşaretini Kaldır": "Remove Tracking Flag",
    "Sadece Takipteki Revizyonları Göster": "Show Only Tracked Revisions",
    "İndir": "Download",
    "Revizyon Dokümanı": "Revision Document",
    "Gelen Yazı Dokümanı": "Incoming Letter Document",
    "Onay/Red Yazı Dokümanı": "Approval/Rejection Letter Document",
    "&Filtre": "&Filter",
    "Gelişmiş Filtreleme...": "Advanced Filtering...",
    "Filtreleri Temizle": "Clear Filters",
    "&Görünüm": "&View",
    "Yenile": "Refresh",
    "Arama Kutusuna Odaklan": "Focus Search Box",
    "Düşük Kontrast": "Low Contrast",
    "TOK Temalari": "TOK Themes",
    "Düzeni Sıfırla": "Reset Layout",
    "Dil": "Language",
    "Türkçe": "Turkish",
    "English": "English",
    "&Rapor": "&Report",
    "Proje Durum Raporu Oluştur...": "Create Project Status Report...",
    "&Yardım": "&Help",
    "Kullanım Kılavuzu": "User Guide",
    "Sürüm Bilgisi": "Version Information",
    "Proje Düzenle": "Edit Project",
    "Yeni Proje Oluştur": "Create New Project",
    "Kategori Seçin...": "Select Category...",
    "Kategori:": "Category:",
    "Yeni Projeleri Yapılandır": "Configure New Projects",
    "Tüm projelere uygulanacak ortak yol (örn: Mekanik/Pompalar)": "Common path to apply to all projects (e.g. Mechanical/Pumps)",
    "<b>Ortak Kategori Yolu (Opsiyonel):</b>": "<b>Common Category Path (Optional):</b>",
    "Seçilen Proje Türlerini Kategori Olarak da Kullan": "Also use selected project types as categories",
    "<b>Proje Bazlı Tür Ataması:</b>": "<b>Project-Based Type Assignment:</b>",
    "Örn: 1-MUH-2024": "Example: 1-MUH-2024",
    "Proje adını girin": "Enter the project name",
    "Proje/Revizyon Yükleme": "Project/Revision Upload",
    "Tek Proje Ekle": "Add Single Project",
    "Çoklu Proje Ekle": "Add Multiple Projects",
    "Revizyon Ekle": "Add Revision",
    "Toplu İşlemler": "Bulk Operations",
    "Kapat": "Close",
    "Gelen Yazıya Proje İlişkilendir": "Link Project to Incoming Letter",
    "Revizyon Açıklamalarını Girin": "Enter Revision Descriptions",
    "📁 Projeleri Klasöre Çıkar": "📁 Export Projects to Folder",
    "Tüm Projeler": "All Projects",
    "Kategori Görünümü": "Category View",
    "Gösterge Paneli": "Dashboard",
    "Loglar": "Logs",
    "📊 Genel İstatistikler": "📊 General Statistics",
    "Toplam Görüntülenen Proje:": "Total Displayed Projects:",
    "Beklemede (Onaysız):": "Pending (Unapproved):",
    "✅ Onay Durumu": "✅ Approval Status",
    "Onaylı:": "Approved:",
    "Notlu Onaylı:": "Approved with Notes:",
    "Reddedilen:": "Rejected:",
    "📤 TSE Durumu": "📤 TSE Status",
    "TSE'ye Gönderilen:": "Sent to TSE:",
    "Henüz Gönderilmeyen:": "Not Yet Sent:",
    "📋 Proje Türü Dağılımı": "📋 Project Type Distribution",
    "Proje Türü": "Project Type",
    "Toplam": "Total",
    "Revizyon": "Revision",
    "Durum": "Status",
    "Açıklama": "Description",
    "Yazı Türü": "Letter Type",
    "Gözat...": "Browse...",
    "Yazı No": "Letter No",
    "Yazı Tarihi": "Letter Date",
    "Doküman": "Document",
    "Yazı Dok.": "Letter Doc.",
    "Uyarı": "Warning",
    "Takip": "Tracking",
    "Takip Notu": "Tracking Note",
    "Takibi Kaldır": "Remove Tracking",
    "📄 Yazıyı Görüntüle": "📄 View Letter",
    "Seçili revizyona takip notu ekle veya güncelle": "Add or update a tracking note for the selected revision",
    "Seçili revizyonu aktif takip listesinden çıkar": "Remove the selected revision from the active tracking list",
    "Seçili revizyona ait gelen/onay/red yazısını tam ekranda aç": "Open the incoming, approval, or rejection letter of the selected revision in full screen",
    "📬 Yazı Ön İzleme": "📬 Letter Preview",
    "Revizyona ait yazı ön izlemesi burada görünür.": "The preview of the revision letter will appear here.",
    "📄 Yazıyı Tam Ekran Aç": "📄 Open Letter Full Screen",
    "Bir revizyon seçerek dokümanı ön izleyin.": "Select a revision to preview the document.",
    "Tam Ekran Görüntüle": "Full Screen View",
    "Doküman Ön İzleme": "Document Preview",
    "Dokümanı Görüntüle": "View Document",
    "Proje Detayları": "Project Details",
    "Proje Kodu:": "Project Code:",
    "Proje İsmi:": "Project Name:",
    "Proje Türü:": "Project Type:",
    "Hiyerarşi Yolu:": "Hierarchy Path:",
    "En Son Gelen Yazı No:": "Latest Incoming Letter No:",
    "En Son Gelen Yazı Tarihi:": "Latest Incoming Letter Date:",
    "En Son Giden Yazı No:": "Latest Outgoing Letter No:",
    "En Son Giden Yazı Tarihi:": "Latest Outgoing Letter Date:",
    "En Son Revizyon Kodu:": "Latest Revision Code:",
    "Onay Durumu:": "Approval Status:",
    "TSE Durumu:": "TSE Status:",
    "Liste Durumu:": "List Status:",
    "Listedeki Tür:": "Type in List:",
    "Proje Ara (Kod veya İsim)...": "Search Project (Code or Name)...",
    "Filtrele": "Filter",
    "Gelişmiş Filtreleme": "Advanced Filtering",
    "Temizle": "Clear",
    "Filtre: Yok": "Filter: None",
    "Kategorisiz": "Uncategorized",
    "Sınıf/Logger:": "Class/Logger:",
    "Tum kaynaklar": "All sources",
    "Seviye:": "Level:",
    "Tum seviyeler": "All levels",
    "Log ara...": "Search logs...",
    "Oto kaydir": "Auto-scroll",
    "Log kaydi yuklenmedi.": "No log records loaded.",
    "Zaman": "Time",
    "Kaynak": "Source",
    "Mesaj": "Message",
    "Genel Durum Raporu": "General Status Report",
    "Bekleyen İşler": "Pending Items",
    "Onaylananlar": "Approved Items",
    "İsim": "Name",
    "Son Revizyon": "Latest Revision",
    "Tarih": "Date",
    "Rapor Oluştur (Excel)": "Create Report (Excel)",
    "🔐 Kullanıcı Girişi": "🔐 User Sign In",
    "Lütfen kullanıcı bilgilerinizi girin veya misafir olarak devam edin": "Enter your user credentials or continue as a guest",
    "Kullanıcı Adı:": "Username:",
    "Kullanıcı adınızı girin": "Enter your username",
    "Şifre:": "Password:",
    "Şifrenizi girin": "Enter your password",
    "🔒 Giriş Yap": "🔒 Sign In",
    "👤 Misafir Olarak Devam Et": "👤 Continue as Guest",
    "💡 <i>Misafir mod: Sadece görüntüleme ve indirme yetkisi</i>": "💡 <i>Guest mode: View and download permissions only</i>",
    "Eksik Bilgi": "Missing Information",
    "Lütfen kullanıcı adı ve şifre girin.": "Please enter a username and password.",
    "Başarılı": "Success",
    "Giriş Başarısız": "Sign-In Failed",
    "Kullanıcı adı veya şifre hatalı.\n\nLütfen tekrar deneyin.": "The username or password is incorrect.\n\nPlease try again.",
    "Misafir Modu": "Guest Mode",
    "Misafir olarak devam etmek istediğinizden emin misiniz?\n\nMisafir modunda sadece görüntüleme ve indirme yetkiniz olacak.\nDüzenleme, ekleme ve silme işlemleri yapamayacaksınız.": "Are you sure you want to continue as a guest?\n\nIn guest mode you will only have permission to view and download.\nYou will not be able to edit, add, or delete items.",
    "Giriş yapmadan çıkmak istediğinizden emin misiniz?\n\nUygulama kapatılacaktır.": "Are you sure you want to exit without signing in?\n\nThe application will be closed.",
    "Güncelleme": "Update",
    "Yeni sürüm bulunamadı.": "No new version was found.",
    "Güncelleme kontrolü zaten devam ediyor.": "Update check is already in progress.",
    "Başlangıçta güncellemeler kontrol ediliyor...": "Checking for updates at startup...",
    "Güncellemeler kontrol ediliyor...": "Checking for updates...",
    "Başlangıç güncelleme kontrolü tamamlandı. Yeni sürüm bulunamadı.": "Startup update check completed. No new version found.",
    "Güncelleme bulunamadı.": "No update found.",
    "Güncelleme Bulundu": "Update Available",
    "Başlangıç kontrolü sırasında yeni bir sürüm bulundu. İndirebilir veya release sayfasını açabilirsiniz.": "A new version was found during startup. You can download it or open the release page.",
    "Yeni sürümü indirebilir veya release sayfasını açabilirsiniz.": "You can download the new version or open the release page.",
    "İndir": "Download",
    "Release Sayfasını Aç": "Open Release Page",
    "Sonra": "Later",
    "Bağlantı Açılamadı": "Unable to Open Link",
    "Sürüm": "Version",
    "Yayın Tarihi": "Published At",
    "Dosya": "File",
    "Release Notları": "Release Notes",
    "Release notu bulunamadı.": "No release notes found.",
    "Yeni sürüm bulundu ancak indirilebilir dosya bulunamadı.": "A new version was found, but no downloadable file was found.",
    "Güncelleme Doğrulanamadı": "Update Could Not Be Verified",
    "Yeni sürüm bulundu ancak checksum doğrulaması yapılamıyor.": "A new version was found, but checksum verification is not available.",
    "İndirme Başlatılamadı": "Download Could Not Start",
    "Güncelleme İndirildi": "Update Downloaded",
    "İndirme Başarısız": "Download Failed",
    "Güncelleme Kontrolü Başarısız": "Update Check Failed",
    "Güncelleme kontrolü başarısız.": "Update check failed.",
    "Güncelleme indirildi.": "Update downloaded.",
    "Güncelleme indirilemedi.": "Update could not be downloaded.",
    "Güncelleme indirme işlemi zaten devam ediyor.": "Update download is already in progress.",
    "İndirme işlemi iptal edildi.": "Download was canceled.",
    "güncelleme paketi": "update package",
    "Açma Hatası": "Open Error",
    "Doküman yok": "No document",
    "Doküman önizlenemiyor: geçersiz dosya": "Document preview is unavailable: invalid file",
    "Doküman önizlenemiyor: bozuk/uyumsuz dosya": "Document preview is unavailable: corrupted/incompatible file",
    "Bilgi": "Info",
    "Hata": "Error",
    "Arama Hatası": "Search Error",
    "Taşıma Hatası": "Move Error",
    "Yeni Kategori": "New Category",
    "Kategori adı:": "Category name:",
    "Kategori adı boş olamaz.": "Category name cannot be empty.",
    "Takipte": "Tracked",
    "Aynı Dosya": "Same File",
    "Eksik": "Missing",
    "Yüklü": "Loaded",
    "Onayli": "Approved",
    "Notlu Onayli": "Approved with Notes",
    "Reddedildi": "Rejected",
    "Onaysiz": "Unapproved",
    "Gelen": "Incoming",
    "Giden": "Outgoing",
    "Gönderildi": "Sent",
    "Gönderilmedi": "Not Sent",
    "Kurumsal Acik": "Corporate Light",
    "Gece Mavisi": "Midnight Blue",
    "Gundogumu": "Sunrise",
    "Cam Yesili": "Glass Green",
    "Celik Gri": "Steel Gray",
    "Sadece Görüntüleme": "View Only",
    "📥 Gelen Yazı": "📥 Incoming Letter",
    "📤 Giden Yazı": "📤 Outgoing Letter",
    "Takip notu boş bırakılamaz.": "Tracking note cannot be empty.",
    "Lütfen bir revizyon seçin.": "Please select a revision.",
    "Revizyon takip listesine eklendi.": "Revision added to the tracking list.",
    "Bu revizyon zaten takipte değil.": "This revision is not currently tracked.",
    "Revizyon takipten çıkarıldı.": "Revision removed from tracking.",
    "Revizyonun yazısı yok.": "This revision has no letter.",
    "Bu revizyona ait yazı dokümanı bulunamadı.": "No letter document was found for this revision.",
    "Açılacak revizyon bulunamadı.": "No revision was available to open.",
    "Bu revizyona ait doküman bulunamadı.": "No document was found for this revision.",
    "Açılacak yazı dokümanı bulunamadı.": "No letter document was available to open.",
    "Yazı dokümanı bilgisi eksik.": "Letter document information is incomplete.",
    "Yazı Bulunamadı": "Letter Not Found",
    "'{yazi_no}' numaralı yazı dokümanı bulunamadı.": "No letter document was found for '{yazi_no}'.",
    "Yazı türü '{logical_type}' yerine '{resolved_lookup}' fallback'i ile çözüldü.": "Letter type was resolved with fallback '{resolved_lookup}' instead of '{logical_type}'.",
    "Yazı ön izlemesi hazırlanıyor...": "Preparing letter preview...",
    "Yazı ön izlemesi yüklenemedi.": "Letter preview could not be loaded.",
    "Yazı ön izleme hatası": "Letter preview error",
    "Ön izleme yükleniyor...": "Loading preview...",
    "Ön izleme hatası": "Preview error",
    "✅ Bu proje listede var": "✅ This project is in the list",
    "✗ Bu proje listede yok": "✗ This project is not in the list",
    "Bu proje listede var": "This project is in the list",
    "Bu proje listede yok": "This project is not in the list",
    "Veritabanı Yedekleri": "Database Backups",
    "Yedekten Geri Yükle": "Restore from Backup",
    "Dosya Adı": "File Name",
    "Boyut (KB)": "Size (KB)",
    "Listeyi Temizle": "Clear List",
    "(Boş)": "(Empty)",
    "Yazı Türü": "Letter Type",
    "Bu giden yazı ne tür bir işlemdir?": "What type of operation is this outgoing letter?",
    "Onay": "Approval",
    "Red": "Rejection",
    "İptal": "Cancel",
    "Kılavuz bulunamadı": "Guide could not be found",
    "Kılavuz okunamadı": "Guide could not be read",
    "Yeni revizyon dokümanı seçin (opsiyonel)...": "Select the new revision document (optional)...",
    "Revizyon dokümanını seçin...": "Select the revision document...",
    "Revizyon Dosyası:": "Revision File:",
    "Revizyon Kodu:": "Revision Code:",
    "Açıklama:": "Description:",
    "TSE'ye Gönderildi": "Sent to TSE",
    "TSE Yazı No:": "TSE Letter No:",
    "TSE Yazı Tarihi:": "TSE Letter Date:",
    "Yeni gelen yazı seç (opsiyonel)...": "Select a new incoming letter (optional)...",
    "İlişkili Gelen Yazı No:": "Related Incoming Letter No:",
    "Gelen Yazı Tarihi:": "Incoming Letter Date:",
    "Gelen Yazı Dosyası:": "Incoming Letter File:",
    "Yeni onay yazısı seç (opsiyonel)...": "Select a new approval letter (optional)...",
    "Onay Yazı No:": "Approval Letter No:",
    "Onay Yazı Tarihi:": "Approval Letter Date:",
    "Onay Yazı Dosyası:": "Approval Letter File:",
    "Yeni red yazısı seç (opsiyonel)...": "Select a new rejection letter (optional)...",
    "Red Yazı No:": "Rejection Letter No:",
    "Red Yazı Tarihi:": "Rejection Letter Date:",
    "Red Yazı Dosyası:": "Rejection Letter File:",
    "Revizyon Dokümanı Seç": "Select Revision Document",
    "Gelen Yazı Dokümanı Seç": "Select Incoming Letter Document",
    "Onay Yazısı Seç": "Select Approval Letter",
    "Red Yazısı Seç": "Select Rejection Letter",
    "Revizyon Durumunu Düzelt": "Fix Revision Status",
    "ALPER BERKAN YILMAZ VE ÖMER ERBAŞ’IN katkıları ile hazırlanmıştır.": "Prepared with the contributions of ALPER BERKAN YILMAZ and ÖMER ERBAŞ.",
}

_EN_PATTERN_TRANSLATIONS: tuple[tuple[re.Pattern[str], Callable[[re.Match[str]], str]], ...] = (
    (
        re.compile(r"^Filtre: (\d+) aktif$"),
        lambda match: f"Filter: {match.group(1)} active",
    ),
    (
        re.compile(r"^Önizleme: (.+)$"),
        lambda match: f"Preview: {match.group(1)}",
    ),
    (
        re.compile(r"^Tema: (.+)$"),
        lambda match: f"Theme: {tr(match.group(1), LANGUAGE_ENGLISH)}",
    ),
    (
        re.compile(r"^Yeni sürüm bulundu: (.+)$"),
        lambda match: f"New version available: {match.group(1)}",
    ),
    (
        re.compile(r"^Proje Takip Sistemi - (v[^ ]+) - \[(.+)\]$"),
        lambda match: f"Project Tracking System - {match.group(1)} - [{match.group(2)}]",
    ),
    (
        re.compile(r"^Proje Bilgisi Gir - (.+)$"),
        lambda match: f"Enter Project Information - {match.group(1)}",
    ),
    (
        re.compile(r"^Rev-(.+) Düzenle(.*)$"),
        lambda match: f"Edit Rev-{match.group(1)}{match.group(2)}",
    ),
    (
        re.compile(r"^Yeni Revizyon Yükle \(Rev-(.+)\)$"),
        lambda match: f"Upload New Revision (Rev-{match.group(1)})",
    ),
    (
        re.compile(r"^(.+) - Yeni Revizyon$"),
        lambda match: f"{match.group(1)} - New Revision",
    ),
    (
        re.compile(r"^Yazı Türü Seç - (.+)$"),
        lambda match: f"Select Letter Type - {match.group(1)}",
    ),
    (
        re.compile(r"^Proje: (\d+) / (\d+)$"),
        lambda match: f"Project: {match.group(1)} / {match.group(2)}",
    ),
    (
        re.compile(r"^Güncelleme indiriliyor: (.+)$"),
        lambda match: f"Downloading update: {match.group(1)}",
    ),
    (
        re.compile(r"^Güncelleme indirmesi başlatılamadı:\n(.+)$", re.DOTALL),
        lambda match: f"Update download could not be started:\n{match.group(1)}",
    ),
    (
        re.compile(r"^Release sayfası açılamadı:\n(.+)$", re.DOTALL),
        lambda match: f"Could not open the release page:\n{match.group(1)}",
    ),
    (
        re.compile(r"^Ağ bağlantısı kurulamadı\.\n\nDetay: (.+)$", re.DOTALL),
        lambda match: f"Could not establish a network connection.\n\nDetails: {match.group(1)}",
    ),
    (
        re.compile(r"^GitHub release bilgisi alınamadı\.\n\nDetay: (.+)$", re.DOTALL),
        lambda match: f"Could not retrieve GitHub release information.\n\nDetails: {match.group(1)}",
    ),
    (
        re.compile(r"^Güncelleme kontrolü sırasında hata oluştu\.\n\nDetay: (.+)$", re.DOTALL),
        lambda match: f"An error occurred while checking for updates.\n\nDetails: {match.group(1)}",
    ),
    (
        re.compile(r"^Henüz yayınlanmış bir güncelleme bulunamadı\.\n\nBu sürüm zaten en güncel halde olabilir veya henüz yeni bir release yayınlanmamış olabilir\.\n\nDetay: (.+)$", re.DOTALL),
        lambda match: "No published update is available yet.\n\n"
        "This version may already be up to date, or a new release may not have been published yet.\n\n"
        f"Details: {match.group(1)}",
    ),
    (
        re.compile(r"^Güncelleme dosyası indirilemedi\.\n\nDetay: (.+)$", re.DOTALL),
        lambda match: f"The update file could not be downloaded.\n\nDetails: {match.group(1)}",
    ),
    (
        re.compile(r"^Güncelleme dosyası indirildi\.\n\nKonum:\n(.+?)\n\nDoğrulama: (.+?)\n\nKurulumu bu dosya üzerinden manuel olarak başlatabilirsiniz\.$", re.DOTALL),
        lambda match: "The update file has been downloaded.\n\n"
        f"Location:\n{match.group(1)}\n\n"
        f"Verification: {match.group(2)}\n\n"
        "You can start the installation manually using this file.",
    ),
    (
        re.compile(r"^Önizleme oluşturulamadı\.\n(.+)$", re.DOTALL),
        lambda match: f"Preview could not be created.\n{match.group(1)}",
    ),
)

_ORIGINAL_QMESSAGEBOX = {}
_ORIGINAL_QINPUTDIALOG = {}
_ORIGINAL_QFILEDIALOG = {}


def normalize_language(language: object) -> str:
    value = str(language or LANGUAGE_TURKISH).strip().lower()
    return LANGUAGE_ENGLISH if value.startswith(LANGUAGE_ENGLISH) else LANGUAGE_TURKISH


def repair_legacy_text(text: object) -> object:
    if not isinstance(text, str):
        return text

    repaired = text
    for source, target in _MOJIBAKE_REPLACEMENTS:
        repaired = repaired.replace(source, target)
    return repaired


def tr(text: object, language: Optional[str] = None) -> object:
    if not isinstance(text, str):
        return text

    repaired = repair_legacy_text(text)
    active_language = normalize_language(language or _active_language)
    if active_language == LANGUAGE_TURKISH:
        return repaired

    if repaired in _EN_TRANSLATIONS:
        return _EN_TRANSLATIONS[repaired]

    for pattern, builder in _EN_PATTERN_TRANSLATIONS:
        match = pattern.match(repaired)
        if match:
            return builder(match)

    return repaired


def get_current_language() -> str:
    return _active_language


def get_language_label(language: str) -> str:
    if normalize_language(language) == LANGUAGE_ENGLISH:
        return "English"
    return "Türkçe"


def load_saved_language() -> str:
    settings = QSettings(APP_NAME, APP_NAME)
    return normalize_language(settings.value(LANGUAGE_SETTING_KEY, LANGUAGE_TURKISH))


def _set_locale_for_language(language: str) -> None:
    if normalize_language(language) == LANGUAGE_ENGLISH:
        locale = QLocale(QLocale.English, QLocale.UnitedStates)
    else:
        locale = QLocale(QLocale.Turkish, QLocale.Turkey)
    QLocale.setDefault(locale)


def set_current_language(language: str, persist: bool = True) -> str:
    global _active_language

    normalized = normalize_language(language)
    _active_language = normalized
    _set_locale_for_language(normalized)

    if persist:
        settings = QSettings(APP_NAME, APP_NAME)
        settings.setValue(LANGUAGE_SETTING_KEY, normalized)

    app = QApplication.instance()
    if app is not None:
        try:
            app.setApplicationDisplayName(tr(APP_NAME))
        except Exception:
            pass

    return normalized


def init_i18n(app: QApplication) -> str:
    global _event_filter

    language = set_current_language(load_saved_language(), persist=False)
    if _event_filter is None:
        _event_filter = _LanguageEventFilter(app)
        app.installEventFilter(_event_filter)

    _install_dialog_patches()
    return language


def set_widget_text(widget: object, source_text: str) -> None:
    if widget is None or not hasattr(widget, "setText"):
        return
    source = repair_legacy_text(source_text)
    try:
        widget.setProperty(_SOURCE_TEXT_PROPERTY, source)
    except Exception:
        pass
    widget.setText(tr(source))


def set_widget_tooltip(widget: object, source_text: str) -> None:
    if widget is None or not hasattr(widget, "setToolTip"):
        return
    source = repair_legacy_text(source_text)
    try:
        widget.setProperty(_SOURCE_TOOLTIP_PROPERTY, source)
    except Exception:
        pass
    widget.setToolTip(tr(source))


def set_placeholder_text(widget: object, source_text: str) -> None:
    if widget is None or not hasattr(widget, "setPlaceholderText"):
        return
    source = repair_legacy_text(source_text)
    try:
        widget.setProperty(_SOURCE_PLACEHOLDER_PROPERTY, source)
    except Exception:
        pass
    widget.setPlaceholderText(tr(source))


def set_window_title(widget: object, source_text: str) -> None:
    if widget is None or not hasattr(widget, "setWindowTitle"):
        return
    source = repair_legacy_text(source_text)
    try:
        widget.setProperty(_SOURCE_WINDOW_TITLE_PROPERTY, source)
    except Exception:
        pass
    widget.setWindowTitle(tr(source))


def apply_language(root: object) -> None:
    if root is None:
        return
    _apply_object(root, set())


def _apply_object(obj: object, visited: set[int]) -> None:
    if obj is None:
        return
    object_id = id(obj)
    if object_id in visited:
        return
    visited.add(object_id)

    if isinstance(obj, QAction):
        _apply_action(obj)
    elif isinstance(obj, QWidget):
        _apply_widget(obj)

    if isinstance(obj, QWidget):
        for action in obj.actions():
            _apply_object(action, visited)
        for child in obj.children():
            if isinstance(child, (QAction, QWidget)):
                _apply_object(child, visited)


def _remember_source(obj: object, property_name: str, current_value: object) -> Optional[str]:
    if not isinstance(current_value, str):
        return None

    source = repair_legacy_text(current_value)
    try:
        existing = obj.property(property_name)
        if isinstance(existing, str) and existing:
            return repair_legacy_text(existing)
        obj.setProperty(property_name, source)
        return source
    except Exception:
        return source


def _apply_action(action: QAction) -> None:
    source_text = _remember_source(action, _SOURCE_TEXT_PROPERTY, action.text())
    if source_text is not None:
        action.setText(tr(source_text))

    source_tooltip = _remember_source(
        action, _SOURCE_TOOLTIP_PROPERTY, action.toolTip()
    )
    if source_tooltip:
        action.setToolTip(tr(source_tooltip))


def _apply_widget(widget: QWidget) -> None:
    source_title = _remember_source(
        widget, _SOURCE_WINDOW_TITLE_PROPERTY, widget.windowTitle()
    )
    if source_title:
        widget.setWindowTitle(tr(source_title))

    source_tooltip = _remember_source(
        widget, _SOURCE_TOOLTIP_PROPERTY, widget.toolTip()
    )
    if source_tooltip:
        widget.setToolTip(tr(source_tooltip))

    if isinstance(widget, QAbstractButton):
        source_text = _remember_source(widget, _SOURCE_TEXT_PROPERTY, widget.text())
        if source_text is not None:
            widget.setText(tr(source_text))
    elif isinstance(widget, QLabel):
        source_text = _remember_source(widget, _SOURCE_TEXT_PROPERTY, widget.text())
        if source_text is not None:
            widget.setText(tr(source_text))

    if isinstance(widget, QLineEdit):
        source_placeholder = _remember_source(
            widget, _SOURCE_PLACEHOLDER_PROPERTY, widget.placeholderText()
        )
        if source_placeholder is not None:
            widget.setPlaceholderText(tr(source_placeholder))

    if isinstance(widget, QMessageBox):
        source_message = _remember_source(widget, _SOURCE_TEXT_PROPERTY, widget.text())
        if source_message is not None:
            widget.setText(tr(source_message))
        source_info = _remember_source(
            widget, _SOURCE_INFO_TEXT_PROPERTY, widget.informativeText()
        )
        if source_info is not None:
            widget.setInformativeText(tr(source_info))
        source_detailed = _remember_source(
            widget, _SOURCE_DETAILED_TEXT_PROPERTY, widget.detailedText()
        )
        if source_detailed is not None:
            widget.setDetailedText(tr(source_detailed))
        _translate_message_box_buttons(widget)

    if isinstance(widget, QGroupBox):
        source_group_title = _remember_source(
            widget, _SOURCE_TITLE_PROPERTY, widget.title()
        )
        if source_group_title is not None:
            widget.setTitle(tr(source_group_title))

    if isinstance(widget, QMenu):
        source_menu_title = _remember_source(
            widget, _SOURCE_TITLE_PROPERTY, widget.title()
        )
        if source_menu_title is not None:
            widget.setTitle(tr(source_menu_title))

    if isinstance(widget, QTabWidget):
        _apply_tab_texts(widget)

    if isinstance(widget, QComboBox):
        _apply_combo_items(widget)

    if isinstance(widget, QTreeWidget):
        _apply_tree_headers(widget)

    if isinstance(widget, QTableWidget):
        _apply_table_headers(widget)


def _apply_tab_texts(tab_widget: QTabWidget) -> None:
    try:
        source_texts = tab_widget.property(_SOURCE_TAB_TEXTS_PROPERTY)
        if not isinstance(source_texts, list) or len(source_texts) != tab_widget.count():
            source_texts = [
                repair_legacy_text(tab_widget.tabText(index))
                for index in range(tab_widget.count())
            ]
            tab_widget.setProperty(_SOURCE_TAB_TEXTS_PROPERTY, source_texts)

        for index, source_text in enumerate(source_texts):
            tab_widget.setTabText(index, tr(source_text))
    except Exception:
        return


def _apply_combo_items(combo: QComboBox) -> None:
    try:
        source_items = combo.property(_SOURCE_COMBO_ITEMS_PROPERTY)
        if not isinstance(source_items, list) or len(source_items) != combo.count():
            source_items = [
                repair_legacy_text(combo.itemText(index))
                for index in range(combo.count())
            ]
            combo.setProperty(_SOURCE_COMBO_ITEMS_PROPERTY, source_items)

        for index, source_text in enumerate(source_items):
            combo.setItemText(index, tr(source_text))
    except Exception:
        return


def _apply_table_headers(table: QTableWidget) -> None:
    try:
        source_headers = table.property(_SOURCE_TABLE_HEADERS_PROPERTY)
        if not isinstance(source_headers, list) or len(source_headers) != table.columnCount():
            source_headers = []
            for column in range(table.columnCount()):
                item = table.horizontalHeaderItem(column)
                source_headers.append(
                    repair_legacy_text(item.text()) if item is not None else ""
                )
            table.setProperty(_SOURCE_TABLE_HEADERS_PROPERTY, source_headers)

        for column, source_text in enumerate(source_headers):
            item = table.horizontalHeaderItem(column)
            if item is not None and source_text:
                item.setText(tr(source_text))
    except Exception:
        return


def _apply_tree_headers(tree: QTreeWidget) -> None:
    try:
        source_headers = tree.property(_SOURCE_TREE_HEADERS_PROPERTY)
        if not isinstance(source_headers, list) or len(source_headers) != tree.columnCount():
            source_headers = [
                repair_legacy_text(tree.headerItem().text(column))
                for column in range(tree.columnCount())
            ]
            tree.setProperty(_SOURCE_TREE_HEADERS_PROPERTY, source_headers)

        tree.setHeaderLabels([tr(text) for text in source_headers])
    except Exception:
        return


class _LanguageEventFilter(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Show, QEvent.LanguageChange):
            try:
                if isinstance(watched, (QWidget, QAction)):
                    apply_language(watched)
            except Exception:
                pass
        return super().eventFilter(watched, event)


def _translate_message_box_buttons(box: QMessageBox) -> None:
    button_texts = {
        QMessageBox.Ok: {"tr": "Tamam", "en": "OK"},
        QMessageBox.Cancel: {"tr": "İptal", "en": "Cancel"},
        QMessageBox.Yes: {"tr": "Evet", "en": "Yes"},
        QMessageBox.No: {"tr": "Hayır", "en": "No"},
        QMessageBox.Close: {"tr": "Kapat", "en": "Close"},
        QMessageBox.Save: {"tr": "Kaydet", "en": "Save"},
        QMessageBox.Open: {"tr": "Aç", "en": "Open"},
        QMessageBox.Retry: {"tr": "Yeniden Dene", "en": "Retry"},
        QMessageBox.Ignore: {"tr": "Yoksay", "en": "Ignore"},
        QMessageBox.Apply: {"tr": "Uygula", "en": "Apply"},
        QMessageBox.Reset: {"tr": "Sıfırla", "en": "Reset"},
        QMessageBox.Discard: {"tr": "Vazgeç", "en": "Discard"},
        QMessageBox.Abort: {"tr": "Durdur", "en": "Abort"},
    }

    for button_enum, labels in button_texts.items():
        button = box.button(button_enum)
        if button is not None:
            button.setText(labels[get_current_language()])


def _install_dialog_patches() -> None:
    global _patches_installed
    if _patches_installed:
        return

    _patch_message_boxes()
    _patch_input_dialogs()
    _patch_file_dialogs()
    _patches_installed = True


def _patch_message_boxes() -> None:
    if _ORIGINAL_QMESSAGEBOX:
        return

    for name in ("information", "warning", "critical", "question"):
        _ORIGINAL_QMESSAGEBOX[name] = getattr(QMessageBox, name)

    def _make_box(
        icon: QMessageBox.Icon,
        parent: Optional[QWidget],
        title: str,
        text: str,
        buttons: QMessageBox.StandardButtons,
        default_button: QMessageBox.StandardButton,
    ) -> QMessageBox:
        box = QMessageBox(parent)
        box.setIcon(icon)
        set_window_title(box, title)
        set_widget_text(box, text)
        box.setStandardButtons(buttons)
        if default_button != QMessageBox.NoButton:
            box.setDefaultButton(default_button)
        _translate_message_box_buttons(box)
        apply_language(box)
        return box

    def _parse_args(args, default_buttons):
        parent = args[0] if len(args) > 0 else None
        title = args[1] if len(args) > 1 else ""
        text = args[2] if len(args) > 2 else ""
        buttons = args[3] if len(args) > 3 else default_buttons
        default_button = args[4] if len(args) > 4 else QMessageBox.NoButton
        return parent, title, text, buttons, default_button

    def _info_wrapper(*args, **kwargs):
        parent, title, text, buttons, default_button = _parse_args(
            args, QMessageBox.Ok
        )
        buttons = kwargs.get("buttons", buttons)
        default_button = kwargs.get("defaultButton", default_button)
        box = _make_box(
            QMessageBox.Information, parent, title, text, buttons, default_button
        )
        return QMessageBox.StandardButton(box.exec())

    def _warning_wrapper(*args, **kwargs):
        parent, title, text, buttons, default_button = _parse_args(
            args, QMessageBox.Ok
        )
        buttons = kwargs.get("buttons", buttons)
        default_button = kwargs.get("defaultButton", default_button)
        box = _make_box(
            QMessageBox.Warning, parent, title, text, buttons, default_button
        )
        return QMessageBox.StandardButton(box.exec())

    def _critical_wrapper(*args, **kwargs):
        parent, title, text, buttons, default_button = _parse_args(
            args, QMessageBox.Ok
        )
        buttons = kwargs.get("buttons", buttons)
        default_button = kwargs.get("defaultButton", default_button)
        box = _make_box(
            QMessageBox.Critical, parent, title, text, buttons, default_button
        )
        return QMessageBox.StandardButton(box.exec())

    def _question_wrapper(*args, **kwargs):
        parent, title, text, buttons, default_button = _parse_args(
            args, QMessageBox.Yes | QMessageBox.No
        )
        buttons = kwargs.get("buttons", buttons)
        default_button = kwargs.get("defaultButton", default_button)
        box = _make_box(
            QMessageBox.Question, parent, title, text, buttons, default_button
        )
        return QMessageBox.StandardButton(box.exec())

    QMessageBox.information = staticmethod(_info_wrapper)
    QMessageBox.warning = staticmethod(_warning_wrapper)
    QMessageBox.critical = staticmethod(_critical_wrapper)
    QMessageBox.question = staticmethod(_question_wrapper)


def _patch_input_dialogs() -> None:
    if _ORIGINAL_QINPUTDIALOG:
        return

    _ORIGINAL_QINPUTDIALOG["getText"] = QInputDialog.getText
    _ORIGINAL_QINPUTDIALOG["getMultiLineText"] = QInputDialog.getMultiLineText

    def _get_text_wrapper(parent, title, label, *args, **kwargs):
        return _ORIGINAL_QINPUTDIALOG["getText"](
            parent,
            tr(title),
            tr(label),
            *args,
            **kwargs,
        )

    def _get_multiline_wrapper(parent, title, label, *args, **kwargs):
        return _ORIGINAL_QINPUTDIALOG["getMultiLineText"](
            parent,
            tr(title),
            tr(label),
            *args,
            **kwargs,
        )

    QInputDialog.getText = staticmethod(_get_text_wrapper)
    QInputDialog.getMultiLineText = staticmethod(_get_multiline_wrapper)


def _patch_file_dialogs() -> None:
    if _ORIGINAL_QFILEDIALOG:
        return

    for name in (
        "getExistingDirectory",
        "getOpenFileName",
        "getOpenFileNames",
        "getSaveFileName",
    ):
        _ORIGINAL_QFILEDIALOG[name] = getattr(QFileDialog, name)

    def _wrap_file_dialog(name: str):
        original = _ORIGINAL_QFILEDIALOG[name]

        def _wrapper(*args, **kwargs):
            mutable_args = list(args)
            if len(mutable_args) >= 2 and isinstance(mutable_args[1], str):
                mutable_args[1] = tr(mutable_args[1])
            if "caption" in kwargs and isinstance(kwargs["caption"], str):
                kwargs["caption"] = tr(kwargs["caption"])
            return original(*mutable_args, **kwargs)

        return _wrapper

    QFileDialog.getExistingDirectory = staticmethod(
        _wrap_file_dialog("getExistingDirectory")
    )
    QFileDialog.getOpenFileName = staticmethod(_wrap_file_dialog("getOpenFileName"))
    QFileDialog.getOpenFileNames = staticmethod(
        _wrap_file_dialog("getOpenFileNames")
    )
    QFileDialog.getSaveFileName = staticmethod(_wrap_file_dialog("getSaveFileName"))


__all__ = [
    "LANGUAGE_ENGLISH",
    "LANGUAGE_TURKISH",
    "apply_language",
    "get_current_language",
    "get_language_label",
    "init_i18n",
    "load_saved_language",
    "normalize_language",
    "repair_legacy_text",
    "set_current_language",
    "set_placeholder_text",
    "set_widget_text",
    "set_widget_tooltip",
    "set_window_title",
    "tr",
]
