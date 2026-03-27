from PySide6.QtWidgets import (
    QToolBar,
    QLabel,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QLineEdit,
    QGroupBox,
    QFormLayout,
    QPushButton,
    QSplitter,
    QAbstractItemView,
    QSizePolicy,
)
from PySide6.QtCore import Qt
import os
import sys
from PySide6.QtGui import QFont, QIcon, QKeySequence

from app_paths import get_resource_path
from widgets import ZoomableScrollArea, WatermarkOverlay
from config import ENABLE_WATERMARK, WATERMARK_IMAGE_PATH, WATERMARK_OPACITY


def setup_ui(self):
    # Keep identical behavior with previous implementation but move the code here
    self.setGeometry(100, 100, 1600, 900)
    self.ana_widget = QWidget()
    self.setCentralWidget(self.ana_widget)
    from PySide6.QtWidgets import QHBoxLayout

    self.ana_layout = QHBoxLayout(self.ana_widget)
    # (actual layout creation is done in main_window to avoid double imports)
    # Call the original helpers from this module
    _setup_toolbar(self)
    self.ana_bolunmus_pencere = QSplitter(Qt.Horizontal)
    self.ana_layout = self.ana_layout or self.ana_widget.layout() or None
    if not self.ana_layout:
        # fallback to horizontal layout to keep old behavior
        from PySide6.QtWidgets import QHBoxLayout

        self.ana_layout = QHBoxLayout(self.ana_widget)
    self.ana_layout.addWidget(self.ana_bolunmus_pencere)
    self.ana_bolunmus_pencere.addWidget(_setup_projeler_panel(self))
    self.ana_bolunmus_pencere.addWidget(self._setup_revizyonlar_panel())
    self.sag_dikey_bolucu = QSplitter(Qt.Vertical)
    self.sag_dikey_bolucu.addWidget(self._setup_detaylar_panel())
    self.sag_dikey_bolucu.addWidget(self._setup_onizleme_panel())
    self.sag_dikey_bolucu.setSizes([300, 600])
    self.ana_bolunmus_pencere.addWidget(self.sag_dikey_bolucu)
    self.ana_bolunmus_pencere.setSizes([400, 800, 400])
    # Watermark overlay
    try:
        if ENABLE_WATERMARK:
            self._watermark = WatermarkOverlay(
                parent=self.ana_widget,
                image_path=WATERMARK_IMAGE_PATH,
                opacity=WATERMARK_OPACITY,
            )
            self._watermark.setGeometry(self.ana_widget.rect())
            self._watermark.raise_()
    except Exception:
        pass
    # Restore UI state if available
    try:
        self._restore_ui_state()
    except Exception:
        pass

    # Final UI adjustments (splitter sizes, minimum sizes, header modes etc.)
    try:
        _finalize_ui(self)
    except Exception:
        pass


def _setup_toolbar(self):
    toolbar = QToolBar("Ana Araç Çubuğu")
    toolbar.setObjectName("ana_arac_cubugu")
    toolbar.setMovable(False)
    self.addToolBar(toolbar)

    self.mem_timer.start()


def _setup_projeler_panel(self):
    # Create the panel wrapper with tabs
    from ui.panels.project_panel import ProjectPanel

    # Initialize ProjectPanel
    if not hasattr(self, "project_panel"):
        self.project_panel = ProjectPanel()
        self.project_panel.project_selected.connect(self.on_project_selected_from_panel)
        self.project_panel.project_moved.connect(self.on_proje_tasindi)
        self.project_panel.advanced_filter_clicked.connect(self.show_advanced_filters)
        self.project_panel.clear_filter_clicked.connect(self.clear_filters)

        # Compatibility aliases
        self.proje_listesi_widget = self.project_panel.proje_listesi_widget
        self.proje_agaci_widget = self.project_panel.proje_agaci_widget
        self.arama_kutusu = self.project_panel.arama_kutusu
        self.filter_indicator = self.project_panel.filter_indicator

    # Create tab widget wrapper
    panel = QWidget()
    from PySide6.QtWidgets import QVBoxLayout

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)

    # Add search bar from ProjectPanel
    layout.addWidget(self.arama_kutusu.parent())  # Add the whole search layout

    # Create tab widget
    self.sekme_widget = QTabWidget()
    layout.addWidget(self.sekme_widget)

    # Add list view tab
    sekme_liste = QWidget()
    liste_layout = QVBoxLayout(sekme_liste)
    liste_layout.setContentsMargins(0, 0, 0, 0)
    liste_layout.addWidget(self.proje_listesi_widget)
    self.sekme_widget.addTab(sekme_liste, "Tüm Projeler")

    # Add tree view tab
    sekme_agac = QWidget()
    agac_layout = QVBoxLayout(sekme_agac)
    agac_layout.setContentsMargins(0, 0, 0, 0)
    agac_layout.addWidget(self.proje_agaci_widget)
    self.sekme_widget.addTab(sekme_agac, "Kategori Görünümü")

    # Add report tab
    self.sekme_widget.addTab(_setup_rapor_paneli(self), "Gösterge Paneli")

    return panel


def _setup_rapor_paneli(self):
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(15)

    self.istatistik_etiketleri = {}

    font = QFont()
    font.setPointSize(11)

    # Genel İstatistikler Grubu
    genel_grup = QGroupBox("📊 Genel İstatistikler")
    genel_grup.setStyleSheet("QGroupBox { font-weight: bold; }")
    genel_layout = QFormLayout(genel_grup)
    genel_layout.setContentsMargins(15, 15, 15, 15)
    genel_layout.setSpacing(8)

    labels_genel = [
        ("Toplam Görüntülenen Proje:", "0", None),
        ("Beklemede (Onaysız):", "0", "color: #0066cc; font-weight: bold;"),
    ]
    for label_text, default_val, style in labels_genel:
        lbl = QLabel(default_val)
        lbl.setFont(font)
        if style:
            lbl.setStyleSheet(style)
        genel_layout.addRow(label_text, lbl)
        self.istatistik_etiketleri[label_text] = lbl
    layout.addWidget(genel_grup)

    # Onay Durumu İstatistikleri
    durum_grup = QGroupBox("✅ Onay Durumu")
    durum_grup.setStyleSheet("QGroupBox { font-weight: bold; }")
    durum_layout = QFormLayout(durum_grup)
    durum_layout.setContentsMargins(15, 15, 15, 15)
    durum_layout.setSpacing(8)

    labels_durum = [
        ("Onaylı:", "0", "color: green; font-weight: bold;"),
        ("Notlu Onaylı:", "0", "color: orange; font-weight: bold;"),
        ("Reddedilen:", "0", "color: red; font-weight: bold;"),
    ]
    for label_text, default_val, style in labels_durum:
        lbl = QLabel(default_val)
        lbl.setFont(font)
        if style:
            lbl.setStyleSheet(style)
        durum_layout.addRow(label_text, lbl)
        self.istatistik_etiketleri[label_text] = lbl
    layout.addWidget(durum_grup)

    # TSE Durumu İstatistikleri
    tse_grup = QGroupBox("📤 TSE Durumu")
    tse_grup.setStyleSheet("QGroupBox { font-weight: bold; }")
    tse_layout = QFormLayout(tse_grup)
    tse_layout.setContentsMargins(15, 15, 15, 15)
    tse_layout.setSpacing(8)

    labels_tse = [
        ("TSE'ye Gönderilen:", "0", "color: #0066cc; font-weight: bold;"),
        ("Henüz Gönderilmeyen:", "0", "color: #666; font-weight: bold;"),
    ]
    for label_text, default_val, style in labels_tse:
        lbl = QLabel(default_val)
        lbl.setFont(font)
        if style:
            lbl.setStyleSheet(style)
        tse_layout.addRow(label_text, lbl)
        self.istatistik_etiketleri[label_text] = lbl
    layout.addWidget(tse_grup)

    # Proje Türü Dağılımı
    tur_grup = QGroupBox("📋 Proje Türü Dağılımı")
    tur_grup.setStyleSheet("QGroupBox { font-weight: bold; }")
    tur_layout = QVBoxLayout(tur_grup)
    tur_layout.setContentsMargins(15, 15, 15, 15)

    from PySide6.QtWidgets import QTableWidget

    self.rapor_tur_table = QTableWidget()
    self.rapor_tur_table.setColumnCount(5)
    self.rapor_tur_table.setHorizontalHeaderLabels(
        ["Proje Türü", "Toplam", "Onaylı", "Notlu Onaylı", "Reddedilen"]
    )
    self.rapor_tur_table.setEditTriggers(QTableWidget.NoEditTriggers)
    self.rapor_tur_table.setSelectionMode(QTableWidget.NoSelection)
    self.rapor_tur_table.setMaximumHeight(200)
    try:
        from PySide6.QtWidgets import QHeaderView

        header = self.rapor_tur_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
    except Exception:
        pass
    self.rapor_tur_table.setStyleSheet(
        "background-color: #f9f9f9; border: 1px solid #ddd;"
    )
    tur_layout.addWidget(self.rapor_tur_table)
    layout.addWidget(tur_grup)

    # Minimal stretch at the end
    layout.addStretch()

    # Wrap panel in scroll area
    from PySide6.QtWidgets import QScrollArea

    scroll = QScrollArea()
    scroll.setWidget(panel)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    return scroll


def _setup_revizyonlar_panel(self):
    panel = QWidget()
    layout = QVBoxLayout(panel)
    label = QLabel("<b>📝 Revizyonlar</b>")
    label.setStyleSheet("font-size: 12pt; color: #212529;")
    layout.addWidget(label)
    quick_actions_layout = QHBoxLayout()
    quick_actions_layout.setSpacing(8)
    self.revizyon_takip_btn = QPushButton("Takip Notu")
    self.revizyon_takip_btn.setToolTip("Seçili revizyona takip notu ekle/güncelle")
    self.revizyon_takip_kaldir_btn = QPushButton("Takibi Kaldır")
    self.revizyon_takip_kaldir_btn.setToolTip("Seçili revizyonu takip listesinden çıkar")
    for btn in (self.revizyon_takip_btn, self.revizyon_takip_kaldir_btn):
        btn.setFixedHeight(30)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff;
                color: #2f3542;
                border: 1px solid #d9dee7;
                border-radius: 8px;
                padding: 4px 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #fff5ee;
                border-color: #f0b284;
            }
            QPushButton:pressed {
                background-color: #ffe8d9;
            }
            QPushButton:disabled {
                background-color: #f4f6f9;
                color: #9aa3b2;
                border-color: #e6e9ef;
            }
            """
        )
    self.revizyon_takip_btn.clicked.connect(self.revizyon_takip_notu_ekle_duzenle)
    self.revizyon_takip_kaldir_btn.clicked.connect(self.revizyon_takip_kaldir)
    quick_actions_layout.addWidget(self.revizyon_takip_btn)
    quick_actions_layout.addWidget(self.revizyon_takip_kaldir_btn)
    quick_actions_layout.addStretch(1)
    layout.addLayout(quick_actions_layout)
    self.revizyon_agaci = QTreeWidget()
    self.revizyon_agaci.setHeaderLabels(
        [
            "Revizyon",
            "Durum",
            "Açıklama",
            "Yazı Türü",
            "Yazı No",
            "Yazı Tarihi",
            "Doküman",
            "Yazı Dok.",
            "Uyarı",
            "Takip",
        ]
    )
    self.revizyon_agaci.setSortingEnabled(False)  # Disable sorting to respect data order
    self.revizyon_agaci.setSelectionMode(QAbstractItemView.SingleSelection)
    self.revizyon_agaci.setAlternatingRowColors(True)
    self.revizyon_agaci.setUniformRowHeights(True)
    layout.addWidget(self.revizyon_agaci)
    return panel


def _finalize_ui(self):
    # finalize layout adjustments
    from PySide6.QtWidgets import QHeaderView

    # Splitter default sizes (left, center, right)
    try:
        self.ana_bolunmus_pencere.setSizes([320, 780, 500])
        # Ensure panels don't collapse
        self.ana_bolunmus_pencere.setCollapsible(0, False)
        self.ana_bolunmus_pencere.setCollapsible(1, False)
        self.ana_bolunmus_pencere.setCollapsible(2, False)
        # Set stretch factors for stable behavior
        self.ana_bolunmus_pencere.setStretchFactor(0, 1)
        self.ana_bolunmus_pencere.setStretchFactor(1, 2)
        self.ana_bolunmus_pencere.setStretchFactor(2, 2)
        # Make handle more visible and interactive
        try:
            self.ana_bolunmus_pencere.setHandleWidth(10)
        except Exception:
            pass
        try:
            self.ana_bolunmus_pencere.setChildrenCollapsible(False)
        except Exception:
            pass
    except Exception as e:
        import logging

        logging.warning(f"Splitter size set failed: {e}")

    # Minimum widths
    try:
        import logging

        logging.debug("Setting min widths and sizes in finalize UI")
        if getattr(self, "proje_listesi_widget", None):
            self.proje_listesi_widget.setMinimumWidth(220)
            self.proje_listesi_widget.setSizePolicy(
                QSizePolicy.Preferred, QSizePolicy.Expanding
            )
            # verified minimum width applied
        if getattr(self, "revizyon_agaci", None):
            self.revizyon_agaci.setMinimumWidth(280)
            self.revizyon_agaci.setSizePolicy(
                QSizePolicy.Preferred, QSizePolicy.Expanding
            )
            # verified minimum width applied
        if getattr(self, "onizleme_scroll_alani", None):
            self.onizleme_scroll_alani.setMinimumSize(420, 300)
            self.onizleme_scroll_alani.setSizePolicy(
                QSizePolicy.Preferred, QSizePolicy.Expanding
            )
            # verified min size applied
    except Exception as e:
        import logging

        logging.warning(f"Finalize UI size settings failed: {e}")

    # Tree header modes for nicer behavior
    try:
        if getattr(self, "revizyon_agaci", None):
            header = self.revizyon_agaci.header()
            header.setSectionResizeMode(QHeaderView.ResizeToContents)
            header.setStretchLastSection(True)
    except Exception as e:
        import logging

        logging.warning(f"Header resize mode set failed: {e}")

    # Default size policies to avoid stretching in odd ways
    try:
        if getattr(self, "proje_agaci_widget", None):
            self.proje_agaci_widget.setMinimumWidth(200)
    except Exception as e:
        import logging

        logging.warning(f"proje_agaci_widget.setMinimumWidth failed: {e}")





def _setup_onizleme_panel(self):
    panel = QWidget()
    layout = QVBoxLayout(panel)
    label = QLabel("<b>🔍 Doküman Ön İzleme</b>")
    label.setStyleSheet("font-size: 12pt; color: #212529;")
    layout.addWidget(label)
    self.onizleme_scroll_alani = ZoomableScrollArea(self)
    self.onizleme_etiketi = QLabel("Bir revizyon seçerek dokümanı ön izleyin.")
    self.onizleme_etiketi.setAlignment(Qt.AlignCenter)
    self.onizleme_scroll_alani.setWidget(self.onizleme_etiketi)
    layout.addWidget(self.onizleme_scroll_alani)
    self.goruntule_btn = QPushButton("Dokümanı Görüntüle")
    self.goruntule_btn.setEnabled(False)
    layout.addWidget(self.goruntule_btn)
    return panel


def _add_menu_action(self, menu, icon, text, callback, shortcut=""):
    from PySide6.QtGui import QIcon, QAction, QKeySequence

    action = QAction(QIcon.fromTheme(icon), text, self)
    if shortcut:
        action.setShortcut(QKeySequence(shortcut))
    action.triggered.connect(callback)
    menu.addAction(action)
    return action


def _setup_menubar(self):
    menubar = self.menuBar()
    # Because original code uses many helper methods and actions, keep it compact
    # The wrapper will call the original helpers for detailed actions
    dosya_menu = menubar.addMenu("&Dosya")
    self._add_menu_action(
        dosya_menu,
        "document-new",
        "Yeni Veritabanı Oluştur...",
        self.yeni_veritabani_olustur,
        "Ctrl+Shift+N",
    )
    self._add_menu_action(
        dosya_menu, "document-open", "Veritabanı Aç...", self.veritabani_ac, "Ctrl+O"
    )
    # Son kullanılan dosyalar
    self.son_dosyalar_menu = dosya_menu.addMenu(
        QIcon.fromTheme("document-open-recent"), "Son Kullanılan Dosyalar"
    )
    try:
        self._son_kullanilan_dosyalari_guncelle()
    except Exception:
        pass
    dosya_menu.addSeparator()
    self.excel_export_action = self._add_menu_action(
        dosya_menu, "x-office-spreadsheet", "Excel'e Aktar", self.excele_aktar, "Ctrl+E"
    )
    self.revizyon_takip_export_action = self._add_menu_action(
        dosya_menu,
        "x-office-spreadsheet",
        "Takip Listesini Excel'e Aktar...",
        self.takip_listesini_excele_aktar,
    )
    self._add_menu_action(
        dosya_menu, "folder-new", "Projeleri Klasöre Çıkar...", self.projeleri_klasore_cikar
    )
    dosya_menu.addSeparator()
    # Yedekleme menüsü
    yedek_menu = dosya_menu.addMenu(QIcon.fromTheme("document-save"), "Yedekleme")
    self._add_menu_action(
        yedek_menu, "document-save-as", "Manuel Yedek Al", self.manuel_yedek_al
    )
    self._add_menu_action(
        yedek_menu,
        "document-revert",
        "Yedekten Geri Yükle...",
        self.yedekten_geri_yukle_dialog,
    )
    self._add_menu_action(
        yedek_menu, "folder-open", "Yedekleri Listele...", self.yedekleri_goster
    )
    dosya_menu.addSeparator()
    # Güncelleme eylemleri — Dosya menüsü altında
    try:
        from PySide6.QtGui import QAction
        update_action = QAction("🔄 Güncellemeleri Kontrol Et...", self)
        update_action.setIcon(QIcon.fromTheme("system-software-update"))
        try:
            update_action.triggered.connect(self.check_for_updates)
        except Exception:
            pass
        self.update_action = update_action
        dosya_menu.addAction(update_action)

        auto_action = QAction("Başlangıçta güncellemeleri kontrol et", self)
        auto_action.setCheckable(True)
        try:
            auto_action.triggered.connect(
                lambda checked: getattr(self, '_toggle_auto_update_check', lambda *_: None)(checked)
            )
        except Exception:
            pass
        self.auto_check_update_action = auto_action
        dosya_menu.addAction(auto_action)
    except Exception:
        pass
    dosya_menu.addSeparator()
    self._add_menu_action(dosya_menu, "application-exit", "Çıkış", self.close, "Ctrl+Q")
    # Görünüm menüsü - Tema toggle eklendi
    # Proje menüsü
    proje_menu = menubar.addMenu("&Proje")
    self._add_menu_action(
        proje_menu, "document-new", "Yeni Proje", self.yeni_proje_penceresi, "Ctrl+N"
    )
    self._add_menu_action(
        proje_menu,
        "document-open",
        "Dosyadan Proje Oluştur...",
        self.dosyadan_proje_olustur,
    )
    self._add_menu_action(
        proje_menu,
        "mail-forward",
        "Gelen Yazıdan Proje Oluştur...",
        self.gelen_yazidan_coklu_proje_olustur,
    )
    self._add_menu_action(
        proje_menu,
        "mail-send",
        "Giden Yazıdan Proje Oluştur...",
        self.giden_yazidan_coklu_proje_olustur,
    )
    proje_menu.addSeparator()
    self.proje_duzenle_action = self._add_menu_action(
        proje_menu,
        "document-edit",
        "Seçili Projeyi Düzenle...",
        self.proje_duzenleme_penceresi,
    )
    self.proje_sil_action = self._add_menu_action(
        proje_menu, "edit-delete", "Seçili Projeyi Sil", self.arayuzden_projeyi_sil
    )
    proje_menu.addSeparator()
    self.proje_toplu_gelen_action = self._add_menu_action(
        proje_menu,
        "mail-receive",
        "Seçili Projelere Toplu Gelen Yazı Ekle...",
        lambda: self._toplu_yazi_islem_baslat("Gelen"),
    )
    self.proje_toplu_onay_action = self._add_menu_action(
        proje_menu,
        "mail-signed-verified",
        "Seçili Projelere Toplu Onay Yazısı Ekle...",
        lambda: self._toplu_yazi_islem_baslat("Onay"),
    )
    self.proje_toplu_notlu_action = self._add_menu_action(
        proje_menu,
        "emblem-favorite",
        "Seçili Projelere Toplu Notlu Onay Yazısı Ekle...",
        lambda: self._toplu_yazi_islem_baslat("Notlu Onay"),
    )
    self.proje_toplu_red_action = self._add_menu_action(
        proje_menu,
        "mail-mark-junk",
        "Seçili Projelere Toplu Red Yazısı Ekle...",
        lambda: self._toplu_yazi_islem_baslat("Red"),
    )

    # Revizyon menüsü
    revizyon_menu = menubar.addMenu("&Revizyon")
    self._add_menu_action(
        revizyon_menu,
        "list-add",
        "Yeni Revizyon Yükle...",
        self.yeni_revizyon_yukle,
        "Ctrl+Shift+R",
    )
    self.revizyon_duzenle_action = self._add_menu_action(
        revizyon_menu,
        "document-edit",
        "Seçili Revizyonu Düzenle...",
        self.arayuzden_revizyonu_duzenle,
        "Ctrl+D",
    )
    self.revizyon_sil_action = self._add_menu_action(
        revizyon_menu,
        "edit-delete",
        "Seçili Revizyonu Sil...",
        self.arayuzden_revizyonu_sil,
        "Delete",
    )
    revizyon_menu.addSeparator()
    self._add_menu_action(
        revizyon_menu,
        "dialog-ok-apply",
        "Revizyonu Onayla...",
        lambda: self._revizyon_islem_baslat("Onay"),
    )
    self._add_menu_action(
        revizyon_menu,
        "emblem-favorite",
        "Revizyonu Notlu Onayla...",
        lambda: self._revizyon_islem_baslat("Notlu Onay"),
    )
    self._add_menu_action(
        revizyon_menu,
        "dialog-cancel",
        "Revizyonu Reddet...",
        lambda: self._revizyon_islem_baslat("Red"),
    )
    self._add_menu_action(
        revizyon_menu,
        "system-run",
        "Revizyon Durumunu Düzelt...",
        self.revizyon_durumunu_degistir,
    )
    revizyon_menu.addSeparator()
    self.revizyon_takip_notu_action = self._add_menu_action(
        revizyon_menu,
        "edit-rename",
        "Takip Notu Ekle/Güncelle...",
        self.revizyon_takip_notu_ekle_duzenle,
    )
    self.revizyon_takip_kaldir_action = self._add_menu_action(
        revizyon_menu,
        "edit-clear",
        "Takip İşaretini Kaldır",
        self.revizyon_takip_kaldir,
    )
    from PySide6.QtGui import QAction
    self.sadece_takipteki_revizyonlar_action = QAction(
        "Sadece Takipteki Revizyonları Göster", self
    )
    self.sadece_takipteki_revizyonlar_action.setCheckable(True)
    self.sadece_takipteki_revizyonlar_action.toggled.connect(
        self.revizyon_takip_filtresini_degistir
    )
    revizyon_menu.addAction(self.sadece_takipteki_revizyonlar_action)
    revizyon_menu.addSeparator()
    indir_menu = revizyon_menu.addMenu(QIcon.fromTheme("download"), "İndir")
    self.rev_indir_action = self._add_menu_action(
        indir_menu, "go-down", "Revizyon Dokümanı", self.dokumani_indir
    )
    self.gelen_yazi_indir_action = self._add_menu_action(
        indir_menu, "mail-attachment", "Gelen Yazı Dokümanı", self.gelen_yaziyi_indir
    )
    self.onay_red_yazi_indir_action = self._add_menu_action(
        indir_menu,
        "mail-signed",
        "Onay/Red Yazı Dokümanı",
        self.onay_red_yazisini_indir,
    )
    # Filtre menüsü
    filtre_menu = menubar.addMenu("&Filtre")
    self._add_menu_action(
        filtre_menu,
        "view-filter",
        "Gelişmiş Filtreleme...",
        self.show_advanced_filters,
        "Ctrl+Shift+F",
    )
    self._add_menu_action(
        filtre_menu, "edit-clear", "Filtreleri Temizle", self.clear_filters
    )

    # Görünüm menüsü - Tema toggle eklendi
    gorunum_menu = menubar.addMenu("&Görünüm")
    yenile_action = self._add_menu_action(
        gorunum_menu, "view-refresh", "Yenile", self.yenile
    )
    try:
        yenile_action.setShortcuts([QKeySequence("F5"), QKeySequence("Ctrl+R")])
    except Exception:
        pass
    self._add_menu_action(
        gorunum_menu, "", "Arama Kutusuna Odaklan", self.focus_search, "Ctrl+F"
    )
    try:
        # Use a QAction for toggling contrast
        from PySide6.QtGui import QAction

        toggle_action = QAction("Düşük Kontrast", self)
        toggle_action.setCheckable(True)

        def _toggle(checked):
            try:
                self.toggle_contrast()  # method must be provided on AnaPencere
            except Exception:
                pass

        toggle_action.triggered.connect(_toggle)
        gorunum_menu.addAction(toggle_action)
        # TOK theme toggle (light <-> dark)
        # Tok theme toggle - show current state text and icon
        initial_tok_variant = getattr(self, "_tok_variant", "light")
        tok_label = "Tok: Koyu" if initial_tok_variant == "dark" else "Tok: Açık"
        tok_icon = QIcon.fromTheme("weather-night") if initial_tok_variant == "dark" else QIcon.fromTheme("weather-clear")
        tok_action = QAction(tok_label, self)
        tok_action.setIcon(tok_icon)
        tok_action.setCheckable(True)

        def _tok_toggled(checked):
            try:
                self.toggle_tok_theme()
                # Update action text and icon to reflect new state
                try:
                    label = "Tok: Koyu" if checked else "Tok: Açık"
                    ico = QIcon.fromTheme("weather-night") if checked else QIcon.fromTheme("weather-clear")
                    tok_action.setText(label)
                    tok_action.setIcon(ico)
                except Exception:
                    pass
            except Exception:
                pass

        tok_action.triggered.connect(_tok_toggled)
        self.tok_action = tok_action
        # reflect current variant if set on window
        try:
            is_dark = getattr(self, "_tok_variant", "light") == "dark"
            self.tok_action.setChecked(is_dark)
        except Exception:
            pass
        gorunum_menu.addAction(tok_action)
        # Add a reset layout action
        reset_action = QAction("Düzeni Sıfırla", self)
        reset_action.triggered.connect(
            lambda: getattr(self, "_reset_layout", lambda: None)()
        )
        gorunum_menu.addAction(reset_action)
        # Güncelleme eylemleri Dosya menüsüne taşındı
    except Exception:
        pass
    # Rapor menüsü
    rapor_menu = menubar.addMenu("&Rapor")
    self._add_menu_action(
        rapor_menu,
        "x-office-document",
        "Proje Durum Raporu Oluştur...",
        self.rapor_olustur,
        "Ctrl+Shift+P",
    )

    # Yardım menüsü
    yardim_menu = menubar.addMenu("&Yardım")
    self._add_menu_action(
        yardim_menu,
        "help-contents",
        "Kullanım Kılavuzu",
        self.show_user_guide_tab,
        "F1",
    )
    self._add_menu_action(
        yardim_menu, "help-about", "Sürüm Bilgisi", self.show_version_info
    )

    return menubar


def show_user_guide_tab(self):
    # Keep same behavior - try to read KULLANIM_KILAVUZU.md and show textual content
    try:
        guide_path = get_resource_path("KULLANIM_KILAVUZU.md")
        if os.path.exists(guide_path):
            with open(guide_path, "r", encoding="utf-8") as f:
                guide_text = f.read()
        else:
            guide_text = "Kılavuz bulunamadı"
    except Exception:
        guide_text = "Kılavuz okunamadı"
    # Simple dialog
    from PySide6.QtWidgets import QMessageBox

    QMessageBox.information(self, "Kullanım Kılavuzu", guide_text)


__all__ = [
    "setup_ui",
    "_setup_toolbar",
    "_setup_projeler_panel",
    "_setup_revizyonlar_panel",
    "_setup_onizleme_panel",
    "_setup_rapor_paneli",
    "_add_menu_action",
    "_setup_menubar",
    "show_user_guide_tab",
]
