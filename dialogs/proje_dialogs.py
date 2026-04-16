from typing import Optional, Dict, List, Tuple

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QDialog,
    QFormLayout,
    QComboBox,
    QDialogButtonBox,
    QCheckBox,
    QScrollArea,
    QGroupBox,
    QDateEdit,
    QTableWidget,
    QHeaderView,
    QCompleter,
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from project_types import PROJECT_TYPE_OPTIONS, PROJECT_TYPE_OPTIONS_WITH_EMPTY


class ProjeDialog(QDialog):
    def __init__(
        self,
        parent,
        kategori_listesi: List[Tuple[int, str]],
        on_veri: Optional[Dict] = None,
    ):
        super().__init__(parent)
        self.on_veri = on_veri or {}
        self.setWindowTitle(
            "Proje Düzenle" if "id" in self.on_veri else "Yeni Proje Oluştur"
        )

        layout = QFormLayout(self)
        self.kod_entry = QLineEdit(self.on_veri.get("kod", ""))
        self.isim_entry = QLineEdit(self.on_veri.get("isim", ""))

        self.tur_combo = QComboBox()
        self.tur_combo.setEditable(True)
        self.tur_combo.addItems(PROJECT_TYPE_OPTIONS_WITH_EMPTY)
        if self.on_veri.get("tur"):
            index = self.tur_combo.findText(self.on_veri["tur"])
            (
                self.tur_combo.setCurrentIndex(index)
                if index >= 0
                else self.tur_combo.setEditText(self.on_veri["tur"])
            )

        self.kategori_combo = QComboBox()
        self.kategori_combo.setPlaceholderText("Kategori Seçin...")
        self.kategori_combo.addItem("Kategorisiz", None)
        for kat_id, kat_yol in kategori_listesi:
            self.kategori_combo.addItem(kat_yol, kat_id)

        mevcut_kategori_id = self.on_veri.get("kategori_id")
        if mevcut_kategori_id:
            index = self.kategori_combo.findData(mevcut_kategori_id)
            if index > -1:
                self.kategori_combo.setCurrentIndex(index)
            else:
                self.kategori_combo.setCurrentIndex(0)
        elif "id" not in self.on_veri and "kategori_id" in self.on_veri:
            index = self.kategori_combo.findData(self.on_veri["kategori_id"])
            if index > -1:
                self.kategori_combo.setCurrentIndex(index)
            else:
                self.kategori_combo.setCurrentIndex(0)
        else:
            self.kategori_combo.setCurrentIndex(0)

        layout.addRow("Proje Kodu:", self.kod_entry)
        layout.addRow("Proje İsmi:", self.isim_entry)
        layout.addRow("Proje Türü:", self.tur_combo)
        layout.addRow("Kategori:", self.kategori_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        if not self.kod_entry.text().strip():
            return QMessageBox.warning(
                self, "Eksik Bilgi", "Proje kodu boş bırakılamaz."
            )
        if not self.isim_entry.text().strip():
            return QMessageBox.warning(
                self, "Eksik Bilgi", "Proje ismi boş bırakılamaz."
            )
        super().accept()

    def get_data(self):
        return {
            "kod": self.kod_entry.text().strip(),
            "isim": self.isim_entry.text().strip(),
            "tur": self.tur_combo.currentText().strip() or None,
            "kategori_id": self.kategori_combo.currentData(),
        }


class ProjeTuruDuzenlemeDialog(QDialog):
    def __init__(self, parent, projeler):
        super().__init__(parent)
        self.projeler = projeler
        self.tur_girdileri = {}
        self.setWindowTitle("Yeni Projeleri Yapılandır")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)
        ortak_grup_layout = QFormLayout()
        self.ortak_hiyerarsi_entry = QLineEdit()
        self.ortak_hiyerarsi_entry.setPlaceholderText(
            "Tüm projelere uygulanacak ortak yol (örn: Mekanik/Pompalar)"
        )
        ortak_grup_layout.addRow(
            "<b>Ortak Kategori Yolu (Opsiyonel):</b>", self.ortak_hiyerarsi_entry
        )

        self.turleri_kategori_yap_cb = QCheckBox(
            "Seçilen Proje Türlerini Kategori Olarak da Kullan"
        )
        self.turleri_kategori_yap_cb.setChecked(True)
        ortak_grup_layout.addRow("", self.turleri_kategori_yap_cb)
        layout.addLayout(ortak_grup_layout)
        layout.addWidget(QLabel("<b>Proje Bazlı Tür Ataması:</b>"))
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        form_layout = QFormLayout(scroll_widget)
        on_tanimli_turler = PROJECT_TYPE_OPTIONS_WITH_EMPTY
        for proje_id, proje_kodu, proje_ismi in self.projeler:
            tur_combo = QComboBox()
            tur_combo.setEditable(True)
            tur_combo.addItems(on_tanimli_turler)
            self.tur_girdileri[proje_id] = tur_combo
            form_layout.addRow(f"{proje_kodu} - {proje_ismi}", tur_combo)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return {
            "proje_turleri": {
                proje_id: combo_box.currentText().strip() or None
                for proje_id, combo_box in self.tur_girdileri.items()
            },
            "ortak_hiyerarsi": self.ortak_hiyerarsi_entry.text().strip() or None,
            "turleri_kategori_yap": self.turleri_kategori_yap_cb.isChecked(),
        }


class ManuelProjeGirisiDialog(QDialog):
    def __init__(self, parent, dosya_adi: str):
        super().__init__(parent)
        self.dosya_adi = dosya_adi
        self.setWindowTitle(f"Proje Bilgisi Gir - {dosya_adi}")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        bilgi_label = QLabel(
            f"<b>Dosya:</b> {dosya_adi}<br><br>Bu dosya otomatik format kontrolünden geçemedi.<br>Lütfen proje kodunu ve ismini manuel olarak girin:"
        )
        bilgi_label.setWordWrap(True)
        layout.addWidget(bilgi_label)
        form_layout = QFormLayout()
        self.kod_entry = QLineEdit()
        self.kod_entry.setPlaceholderText("Örn: 1-MUH-2024")
        form_layout.addRow("<b>Proje Kodu:</b>", self.kod_entry)
        self.isim_entry = QLineEdit()
        self.isim_entry.setPlaceholderText("Proje adını girin")
        form_layout.addRow("<b>Proje İsmi:</b>", self.isim_entry)
        layout.addLayout(form_layout)
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.kod_entry.setFocus()

    def get_bilgi(self) -> dict:
        return {
            "kod": self.kod_entry.text().strip(),
            "isim": self.isim_entry.text().strip(),
        }

    def accept(self):
        bilgi = self.get_bilgi()
        if not bilgi["kod"]:
            QMessageBox.warning(self, "Eksik Bilgi", "Proje kodu boş bırakılamaz.")
            self.kod_entry.setFocus()
            return
        if not bilgi["isim"]:
            QMessageBox.warning(self, "Eksik Bilgi", "Proje ismi boş bırakılamaz.")
            self.isim_entry.setFocus()
            return
        super().accept()


class ProjeYuklemeDialog(QDialog):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.parent_window = parent
        self.setWindowTitle("Proje/Revizyon Yükleme")
        self.setMinimumSize(800, 600)
        main_layout = QVBoxLayout(self)
        from PySide6.QtWidgets import QTabWidget

        self.tab_widget = QTabWidget()
        self.tab_tek_proje = self._create_tek_proje_tab()
        self.tab_coklu_proje = self._create_coklu_proje_tab()
        self.tab_revizyon = self._create_revizyon_tab()
        self.tab_toplu_islem = self._create_toplu_islem_tab()
        self.tab_widget.addTab(self.tab_tek_proje, "Tek Proje Ekle")
        self.tab_widget.addTab(self.tab_coklu_proje, "Çoklu Proje Ekle")
        self.tab_widget.addTab(self.tab_revizyon, "Revizyon Ekle")
        self.tab_widget.addTab(self.tab_toplu_islem, "Toplu İşlemler")
        main_layout.addWidget(self.tab_widget)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.kapat_btn = QPushButton("Kapat")
        self.kapat_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.kapat_btn)
        main_layout.addLayout(button_layout)

    def _create_tek_proje_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form_layout = QFormLayout()
        self.tek_kod_entry = QLineEdit()
        self.tek_isim_entry = QLineEdit()
        self.tek_tur_combo = QComboBox()
        self.tek_tur_combo.setEditable(True)
        self.tek_tur_combo.addItems(PROJECT_TYPE_OPTIONS_WITH_EMPTY)
        self.tek_kategori_combo = QComboBox()
        self.tek_kategori_combo.addItem("Kategorisiz", None)
        kategoriler = self.db.get_kategoriler()
        for kat_id, kat_isim, kat_parent_id in kategoriler:
            kat_yol = self.db.get_kategori_yolu(kat_id)
            self.tek_kategori_combo.addItem(kat_yol, kat_id)
        self.tek_gelen_yazi_no = QLineEdit()
        self.tek_gelen_yazi_tarih = QDateEdit()
        self.tek_gelen_yazi_tarih.setCalendarPopup(True)
        self.tek_gelen_yazi_tarih.setDate(QDate.currentDate())
        form_layout.addRow("Proje Kodu:", self.tek_kod_entry)
        form_layout.addRow("Proje İsmi:", self.tek_isim_entry)
        form_layout.addRow("Proje Türü:", self.tek_tur_combo)
        form_layout.addRow("Kategori:", self.tek_kategori_combo)
        form_layout.addRow("Gelen Yazı No:", self.tek_gelen_yazi_no)
        form_layout.addRow("Gelen Yazı Tarihi:", self.tek_gelen_yazi_tarih)
        layout.addLayout(form_layout)
        layout.addStretch()
        kaydet_btn = QPushButton("Projeyi Kaydet")
        kaydet_btn.clicked.connect(self._tek_proje_kaydet)
        layout.addWidget(kaydet_btn)
        return widget


class DosyadanCokluProjeDialog(QDialog):
    """Dialog for bulk management of projects detected from selected files.

    Shows a table with one row per selected file, allows editing project code/name/tur/kategori
    and choosing whether to add it (as new project with first revision) or add a revision to
    an existing project.
    """

    def __init__(self, parent, db, files_info: list):
        super().__init__(parent)
        self.db = db
        self.files_info = files_info
        self.setWindowTitle("Dosyadan Toplu Proje Yükleme")
        self.setMinimumSize(1000, 500)

        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QComboBox, QCheckBox, QPushButton, QLabel

        layout = QVBoxLayout(self)
        instr = QLabel(
            "Lütfen tabloyu kontrol edin ve düzenleyin. 'Ekle' seçili satırlar işlenecektir."
        )
        instr.setWordWrap(True)
        title_layout = QHBoxLayout()
        title_layout.addWidget(instr)
        # Select all / deselect all
        select_all_btn = QPushButton("Tümünü Seç")
        select_all_btn.clicked.connect(lambda: self._set_all_ekle(True))
        deselect_all_btn = QPushButton("Tümünü Kaldır")
        deselect_all_btn.clicked.connect(lambda: self._set_all_ekle(False))
        # Bulk set project type for selected rows
        bulk_type_btn = QPushButton("Seçilenlere Tür Ata")
        bulk_type_btn.clicked.connect(self._bulk_set_type)
        title_layout.addStretch()
        title_layout.addWidget(bulk_type_btn)
        title_layout.addWidget(select_all_btn)
        title_layout.addWidget(deselect_all_btn)
        layout.addLayout(title_layout)

        self.table = QTableWidget()
        headers = [
            "Dosya",
            "Proje Kodu",
            "Proje İsmi",
            "Proje Türü",
            "Kategori",
            "Gelen Yazı No",
            "Gelen Yazı Tarihi",
            "Mevcut",
            "Yeni Revizyon Kodu",
            "Ekle",
            "Uyarı",
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        # allow interactive resize; user can double-click header to autosize
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        # Allow selecting multiple rows using Shift/Ctrl
        try:
            self.table.setSelectionBehavior(QTableWidget.SelectRows)
            self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        except Exception:
            pass
        self._load_categories()
        # Fetch current project codes for completion
        try:
            projeler = self.db.projeleri_listele()
            self.proje_kodlari = [p.proje_kodu for p in projeler]
        except Exception:
            self.proje_kodlari = []

        # populate table and then connect change handler
        self._suppress_events = True
        self._populate_table()
        self._suppress_events = False
        self.table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.table)
        # Buttons and column controls
        btn_layout = QHBoxLayout()
        # add auto-fit & stretch toggle
        autofit_btn = QPushButton("Sütunları İçeriğe Göre Sığdır")
        autofit_btn.clicked.connect(lambda: self.table.resizeColumnsToContents())
        stretch_toggle = QPushButton("Stretch/Interactive")
        def _toggle():
            hdr = self.table.horizontalHeader()
            mode = hdr.sectionResizeMode(0)
            if mode == QHeaderView.Interactive:
                # turn to stretch
                hdr.setSectionResizeMode(QHeaderView.Stretch)
                self.table.horizontalHeader().setStretchLastSection(True)
            else:
                hdr.setSectionResizeMode(QHeaderView.Interactive)
                self.table.horizontalHeader().setStretchLastSection(False)
        stretch_toggle.clicked.connect(_toggle)
        btn_layout.addWidget(autofit_btn)
        btn_layout.addWidget(stretch_toggle)
        self.save_btn = QPushButton("Tümünü Kaydet")
        self.save_btn.clicked.connect(self._save_clicked)
        self.cancel_btn = QPushButton("İptal")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def _load_categories(self):
        try:
            self.kategoriler = [(None, "Kategorisiz")]
            for kat_id, kat_isim, parent in self.db.get_kategoriler():
                self.kategoriler.append((kat_id, self.db.get_kategori_yolu(kat_id)))
        except Exception:
            self.kategoriler = [(None, "Kategorisiz")]

    def _resolve_category_for_row(self, row: int) -> Tuple[Optional[int], Optional[str]]:
        combo = self.table.cellWidget(row, 4)
        if not isinstance(combo, QComboBox):
            return None, None

        text = combo.currentText().strip()
        if not text or text.casefold() == "kategorisiz":
            return None, None

        for index in range(combo.count()):
            if combo.itemText(index).strip().casefold() == text.casefold():
                value = combo.itemData(index)
                return (value if value not in (None, "", 0, "0") else None), None

        return None, f"Kategori bulunamadı: {text}"

    def _populate_table(self):
        from PySide6.QtWidgets import QTableWidgetItem, QComboBox, QCheckBox, QLineEdit, QLabel

        self.table.setRowCount(len(self.files_info))
        for row, info in enumerate(self.files_info):
            # Dosya
            item_dosya = QTableWidgetItem(info.get("dosya_adi", ""))
            item_dosya.setFlags(item_dosya.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, item_dosya)

            # Proje Kodu
            kod_line = QLineEdit(info.get("kod", ""))
            # completer
            try:
                kod_comp = QCompleter(self.proje_kodlari)
                kod_comp.setCaseSensitivity(Qt.CaseInsensitive)
                kod_line.setCompleter(kod_comp)
            except Exception:
                pass
            kod_line.textChanged.connect(lambda txt, r=row: self._update_row_for_code(r, txt))
            self.table.setCellWidget(row, 1, kod_line)

            # Proje İsmi
            isim_line = QLineEdit(info.get("isim", ""))
            self.table.setCellWidget(row, 2, isim_line)

            # Proje Türü
            tur_line = QLineEdit(info.get("tur", ""))
            try:
                tur_comp = QCompleter(PROJECT_TYPE_OPTIONS)
                tur_comp.setCaseSensitivity(Qt.CaseInsensitive)
                tur_line.setCompleter(tur_comp)
            except Exception:
                pass
            tur_line.textChanged.connect(lambda txt, r=row: self._update_row_for_code(r, self._get_kod_for_row(r)))
            self.table.setCellWidget(row, 3, tur_line)

            # Kategori combo
            kat_combo = QComboBox()
            kat_combo.setEditable(True)
            try:
                kat_comp = QCompleter([k[1] for k in self.kategoriler])
                kat_comp.setCaseSensitivity(Qt.CaseInsensitive)
                kat_combo.setCompleter(kat_comp)
            except Exception:
                pass
            for kat_id, kat_yol in self.kategoriler:
                kat_combo.addItem(kat_yol, kat_id)
            if info.get("kategori_id"):
                index = kat_combo.findData(info["kategori_id"])
                if index >= 0:
                    kat_combo.setCurrentIndex(index)
            self.table.setCellWidget(row, 4, kat_combo)

            # Gelen Yazı No
            gy_no_item = QTableWidgetItem(info.get("gelen_yazi_no", ""))
            self.table.setItem(row, 5, gy_no_item)

            # Gelen Yazı Tarihi
            gy_t_item = QTableWidgetItem(info.get("gelen_yazi_tarih", ""))
            self.table.setItem(row, 6, gy_t_item)

            # Mevcut (label)
            mevcut = "Evet" if info.get("mevcut") else "Hayır"
            mevcut_item = QTableWidgetItem(mevcut)
            mevcut_item.setFlags(mevcut_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 7, mevcut_item)

            # Yeni Revizyon Kodu
            rev_item = QTableWidgetItem(info.get("yeni_revizyon_kodu", ""))
            self.table.setItem(row, 8, rev_item)

            # Ekle checkbox
            ekle_cb = QCheckBox()
            ekle_cb.setChecked(True)
            self.table.setCellWidget(row, 9, ekle_cb)

            # Uyarı
            uyar_item = QTableWidgetItem("")
            uyar_item.setFlags(uyar_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 10, uyar_item)

            # For existing projects, auto-fill category/tur/next revision
            if info.get("mevcut") and info.get("kod"):
                pid = None
                try:
                    pid = self.db.proje_var_mi(info.get("kod"))
                except Exception:
                    pid = None
                if pid:
                    try:
                        row_data = self.db.cursor.execute(
                            "SELECT proje_turu, kategori_id FROM projeler WHERE id = ?",
                            (pid,),
                        ).fetchone()
                        if row_data:
                            proje_turu, proj_kategori_id = row_data
                            # Set project type into tur line
                            if proje_turu:
                                try:
                                    tur_widget = self.table.cellWidget(row, 3)
                                    if isinstance(tur_widget, QLineEdit):
                                        tur_widget.setText(proje_turu)
                                except Exception:
                                    pass
                            # Set category
                            if proj_kategori_id:
                                try:
                                    combo = self.table.cellWidget(row, 4)
                                    if combo:
                                        for i in range(combo.count()):
                                            if combo.itemData(i) == proj_kategori_id:
                                                combo.setCurrentIndex(i)
                                                break
                                except Exception:
                                    pass
                        # Next revision suggestion
                        try:
                            tur_widget = self.table.cellWidget(row, 3)
                            # Derive yazi_turu from the presence of an incoming yazı number
                            try:
                                gy_item = self.table.item(row, 5)
                                gy_no = gy_item.text().strip() if gy_item else ""
                            except Exception:
                                gy_no = ""
                            row_yazi_turu = "gelen" if gy_no else "yok"
                            next_rev = self.db.sonraki_revizyon_kodu_onerisi(pid, row_yazi_turu)
                            if self.table.item(row, 8):
                                self.table.item(row, 8).setText(next_rev)
                        except Exception:
                            pass
                    except Exception:
                        pass

    def get_results(self):
        """Return a list of dicts for each row representing the final user choices"""
        results = []
        for r in range(self.table.rowCount()):
            dosya = self.table.item(r, 0).text() if self.table.item(r, 0) else ""
            # Read from cell widgets with fallback to items
            kod = ""
            isim = ""
            tur = None
            kod_widget = self.table.cellWidget(r, 1)
            if isinstance(kod_widget, QLineEdit):
                kod = kod_widget.text().strip()
            else:
                kod = self.table.item(r, 1).text().strip() if self.table.item(r, 1) else ""
            isim_widget = self.table.cellWidget(r, 2)
            if isinstance(isim_widget, QLineEdit):
                isim = isim_widget.text().strip()
            else:
                isim = self.table.item(r, 2).text().strip() if self.table.item(r, 2) else ""
            tur_widget = self.table.cellWidget(r, 3)
            if isinstance(tur_widget, QLineEdit):
                tur = tur_widget.text().strip()
            else:
                tur = self.table.item(r, 3).text().strip() if self.table.item(r, 3) else None
            kategori_id, _ = self._resolve_category_for_row(r)
            gelen_no = self.table.item(r, 5).text().strip() if self.table.item(r, 5) else ""
            gelen_t = self.table.item(r, 6).text().strip() if self.table.item(r, 6) else ""
            mevcut = (self.table.item(r, 7).text() == "Evet") if self.table.item(r, 7) else False
            yeni_rev_kodu = self.table.item(r, 8).text().strip() if self.table.item(r, 8) else ""
            ekle_cb = self.table.cellWidget(r, 9)
            ekle = ekle_cb.isChecked() if ekle_cb else True
            uyar = self.table.item(r, 10).text().strip() if self.table.item(r, 10) else ""

            results.append(
                {
                    "dosya_adi": dosya,
                    "kod": kod,
                    "isim": isim,
                    "tur": tur,
                    "kategori_id": kategori_id,
                    "gelen_yazi_no": gelen_no,
                    "gelen_yazi_tarih": gelen_t,
                    "mevcut": mevcut,
                    "yeni_revizyon_kodu": yeni_rev_kodu,
                    "ekle": ekle,
                    "uyari": uyar,
                }
            )
        return results

    def _get_kod_for_row(self, row: int) -> str:
        widget = self.table.cellWidget(row, 1)
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        item = self.table.item(row, 1)
        return item.text().strip() if item else ""

    def _get_isim_for_row(self, row: int) -> str:
        widget = self.table.cellWidget(row, 2)
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        item = self.table.item(row, 2)
        return item.text().strip() if item else ""

    def _set_all_ekle(self, value: bool):
        """Set Ekle checkbox for all rows."""
        for r in range(self.table.rowCount()):
            cb = self.table.cellWidget(r, 9)
            if isinstance(cb, QCheckBox):
                cb.setChecked(value)

    def _bulk_set_type(self):
        """Prompt for a project type and apply to selected rows (or all if none selected)."""
        try:
            sel_model = self.table.selectionModel()
            rows = [idx.row() for idx in sel_model.selectedRows()] if sel_model else []
        except Exception:
            rows = []
        if not rows:
            rows = list(range(self.table.rowCount()))
        # Suggest current text of first row as default
        default_text = ""
        try:
            widget = self.table.cellWidget(rows[0], 3) if rows else None
            if isinstance(widget, QLineEdit):
                default_text = widget.text()
            elif self.table.item(rows[0], 3):
                default_text = self.table.item(rows[0], 3).text()
        except Exception:
            default_text = ""
        yeni_tur, ok = QInputDialog.getText(self, "Proje Türü Ata", "Tür:", text=default_text)
        if not ok:
            return
        yeni_tur = yeni_tur.strip()
        if not yeni_tur:
            return
        try:
            self._suppress_events = True
            for r in rows:
                widget = self.table.cellWidget(r, 3)
                if isinstance(widget, QLineEdit):
                    widget.setText(yeni_tur)
                elif self.table.item(r, 3):
                    self.table.item(r, 3).setText(yeni_tur)
                # trigger any dependent updates (e.g., existing project data) after change
                self._update_row_for_code(r, self._get_kod_for_row(r))
        finally:
            self._suppress_events = False

    def _validate_rows(self) -> list:
        """Validate rows and set Uyarı text / row highlight. Return list of error tuples (row, msg)."""
        errors = []
        seen_codes = {}
        for r in range(self.table.rowCount()):
            # Clear previous warnings
            if self.table.item(r, 10):
                self.table.item(r, 10).setText("")
            # Reset background for both widgets and items
            for c in range(self.table.columnCount()):
                widget = self.table.cellWidget(r, c)
                if widget:
                    widget.setStyleSheet("")
                it = self.table.item(r, c)
                if it:
                    it.setBackground(QColor(255, 255, 255))

        for r in range(self.table.rowCount()):
            ekle_widget = self.table.cellWidget(r, 9)
            ekle = ekle_widget.isChecked() if isinstance(ekle_widget, QCheckBox) else True
            if not ekle:
                continue
            kod = self._get_kod_for_row(r)
            isim = self._get_isim_for_row(r)
            _, kategori_hata = self._resolve_category_for_row(r)
            msgs = []
            if not kod:
                msgs.append("Proje Kodu boş")
            if not isim:
                msgs.append("Proje İsmi boş")
            if kategori_hata:
                msgs.append(kategori_hata)
            # duplicate code check in grid
            if kod:
                seen = seen_codes.get(kod)
                if seen is not None:
                    msgs.append(f"Aynı kod {seen+1}. satırda zaten kullanılmış")
                else:
                    seen_codes[kod] = r
            if msgs:
                err_msg = "; ".join(msgs)
                errors.append((r, err_msg))
                # set Uyarı cell
                if self.table.item(r, 10):
                    self.table.item(r, 10).setText(err_msg)
                # highlight row (light red) for widgets and items
                for c in range(self.table.columnCount()):
                    widget = self.table.cellWidget(r, c)
                    if widget:
                        widget.setStyleSheet("background-color: #ffe6e6")
                    it = self.table.item(r, c)
                    if it:
                        it.setBackground(QColor(255, 230, 230))
        return errors

    def _save_clicked(self):
        errors = self._validate_rows()
        if errors:
            QMessageBox.warning(self, "Doğrulama Hatası", f"{len(errors)} satırda hata var. Lütfen uyarıları düzeltin.")
            return
        # All good - accept
        super().accept()

    def _update_row_for_code(self, row: int, kod: str):
        """Update a table row based on the provided project code: Mevcut, tur, kategori, next rev."""
        try:
            self._suppress_events = True
            if not kod:
                # clear Mevcut and rev
                if self.table.item(row, 7):
                    self.table.item(row, 7).setText("Hayır")
                if self.table.item(row, 8):
                    self.table.item(row, 8).setText("")
                return

            pid = self.db.proje_var_mi(kod)
            mevcut_item = self.table.item(row, 7)
            if pid:
                if mevcut_item:
                    mevcut_item.setText("Evet")
                row_data = self.db.cursor.execute(
                    "SELECT proje_turu, kategori_id FROM projeler WHERE id = ?",
                    (pid,),
                ).fetchone()
                if row_data:
                    proje_turu, proj_kategori_id = row_data
                    if proje_turu:
                        tur_widget = self.table.cellWidget(row, 3)
                        if isinstance(tur_widget, QLineEdit):
                            tur_widget.setText(proje_turu)
                        elif self.table.item(row, 3):
                            self.table.item(row, 3).setText(proje_turu)
                    if proj_kategori_id:
                        try:
                            combo: QComboBox = self.table.cellWidget(row, 4)
                            if combo:
                                for i in range(combo.count()):
                                    if combo.itemData(i) == proj_kategori_id:
                                        combo.setCurrentIndex(i)
                                        break
                        except Exception:
                            pass
                # Propose next rev code based on row 'tur' value
                try:
                    tur_widget = self.table.cellWidget(row, 3)
                    # Don't use project type for yazi_turu; use incoming yazı number presence to infer it
                    if isinstance(tur_widget, QLineEdit):
                        # still allow project type to be shown in this column; but for yazi logic infer differently
                        pass
                    try:
                        gy_item = self.table.item(row, 5)
                        gy_no = gy_item.text().strip() if gy_item else ""
                    except Exception:
                        gy_no = ""
                    row_yazi_turu = "gelen" if gy_no else "yok"
                    next_rev = self.db.sonraki_revizyon_kodu_onerisi(pid, row_yazi_turu)
                    if self.table.item(row, 8):
                        self.table.item(row, 8).setText(next_rev)
                except Exception:
                    pass
            else:
                if mevcut_item:
                    mevcut_item.setText("Hayır")
                if self.table.item(row, 8):
                    self.table.item(row, 8).setText("")
        finally:
            self._suppress_events = False

    def _on_cell_changed(self, row: int, col: int):
        """Handle cell changes that affect row state (e.g., project code edited)."""
        if getattr(self, "_suppress_events", False):
            return

        # React to project code changes and project type (tur) changes
        if col == 1 or col == 3:
            kod = self._get_kod_for_row(row)
            self._update_row_for_code(row, kod)


    def _create_coklu_proje_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        aciklama = QLabel(
            "Aşağıdaki tabloya birden fazla proje ekleyebilirsiniz. Satır eklemek için 'Satır Ekle' butonunu kullanın."
        )
        aciklama.setWordWrap(True)
        layout.addWidget(aciklama)
        self.coklu_table = QTableWidget()
        self.coklu_table.setColumnCount(6)
        self.coklu_table.setHorizontalHeaderLabels(
            [
                "Proje Kodu",
                "Proje İsmi",
                "Proje Türü",
                "Kategori",
                "Gelen Yazı No",
                "Gelen Yazı Tarihi",
            ]
        )
        self.coklu_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Allow selecting multiple rows with Shift/Ctrl in the helper multiple add table
        try:
            self.coklu_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.coklu_table.setSelectionMode(QTableWidget.ExtendedSelection)
        except Exception:
            pass
        self.coklu_table.setRowCount(5)
        layout.addWidget(self.coklu_table)
        btn_layout = QHBoxLayout()
        satir_ekle_btn = QPushButton("Satır Ekle")
        satir_ekle_btn.clicked.connect(self._coklu_satir_ekle)
        satir_sil_btn = QPushButton("Seçili Satırı Sil")
        satir_sil_btn.clicked.connect(self._coklu_satir_sil)
        temizle_btn = QPushButton("Tabloyu Temizle")
        temizle_btn.clicked.connect(self._coklu_temizle)
        kaydet_btn = QPushButton("Tüm Projeleri Kaydet")
        kaydet_btn.clicked.connect(self._coklu_proje_kaydet)
        kaydet_btn.setStyleSheet("font-weight: bold;")
        btn_layout.addWidget(satir_ekle_btn)
        btn_layout.addWidget(satir_sil_btn)
        btn_layout.addWidget(temizle_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(kaydet_btn)
        layout.addLayout(btn_layout)
        return widget

    def _create_revizyon_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        proje_layout = QHBoxLayout()
        proje_layout.addWidget(QLabel("Proje Seç:"))
        self.rev_proje_combo = QComboBox()
        self.rev_proje_combo.setMinimumWidth(400)
        self._rev_projeleri_yukle()
        proje_layout.addWidget(self.rev_proje_combo)
        proje_layout.addStretch()
        layout.addLayout(proje_layout)
        form_layout = QFormLayout()
        self.rev_kod_entry = QLineEdit()
        self.rev_aciklama_entry = QLineEdit()
        self.rev_yazi_turu_combo = QComboBox()
        self.rev_yazi_turu_combo.addItems(
            ["Gelen Yazı", "Giden Yazı (Onay)", "Giden Yazı (Red)"]
        )
        self.rev_yazi_no = QLineEdit()
        self.rev_yazi_tarih = QDateEdit()
        self.rev_yazi_tarih.setCalendarPopup(True)
        self.rev_yazi_tarih.setDate(QDate.currentDate())
        dokuman_layout = QHBoxLayout()
        self.rev_dokuman_yol = QLineEdit()
        self.rev_dokuman_yol.setReadOnly(True)
        dokuman_sec_btn = QPushButton("Doküman Seç")
        dokuman_sec_btn.clicked.connect(self._rev_dokuman_sec)
        dokuman_layout.addWidget(self.rev_dokuman_yol)
        dokuman_layout.addWidget(dokuman_sec_btn)
        form_layout.addRow("Revizyon Kodu:", self.rev_kod_entry)
        form_layout.addRow("Açıklama:", self.rev_aciklama_entry)
        form_layout.addRow("Yazı Türü:", self.rev_yazi_turu_combo)
        form_layout.addRow("Yazı No:", self.rev_yazi_no)
        form_layout.addRow("Yazı Tarihi:", self.rev_yazi_tarih)
        form_layout.addRow("Doküman:", dokuman_layout)
        layout.addLayout(form_layout)
        layout.addStretch()
        kaydet_btn = QPushButton("Revizyonu Kaydet")
        kaydet_btn.clicked.connect(self._revizyon_kaydet)
        layout.addWidget(kaydet_btn)
        return widget

    def _create_toplu_islem_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        aciklama = QLabel(
            "Bu sekmeden gelen veya giden yazı dosyalarından toplu olarak proje oluşturabilir veya mevcut projelere revizyon ekleyebilirsiniz."
        )
        aciklama.setWordWrap(True)
        layout.addWidget(aciklama)
        tip_layout = QHBoxLayout()
        tip_layout.addWidget(QLabel("İşlem Tipi:"))
        self.toplu_tip_combo = QComboBox()
        self.toplu_tip_combo.addItems(["Gelen Yazı", "Giden Yazı (Onay/Red)"])
        tip_layout.addWidget(self.toplu_tip_combo)
        tip_layout.addStretch()
        layout.addLayout(tip_layout)
        dosya_group = QGroupBox("Dosya Seçimi")
        dosya_layout = QVBoxLayout(dosya_group)
        self.toplu_dosya_listesi = QLabel("Henüz dosya seçilmedi")
        self.toplu_dosya_listesi.setWordWrap(True)
        dosya_layout.addWidget(self.toplu_dosya_listesi)
        dosya_sec_btn = QPushButton("Dosyaları Seç")
        dosya_sec_btn.clicked.connect(self._toplu_dosya_sec)
        dosya_layout.addWidget(dosya_sec_btn)
        layout.addWidget(dosya_group)
        layout.addStretch()
        isle_btn = QPushButton("Toplu İşlemi Başlat")
        isle_btn.clicked.connect(self._toplu_islem_baslat)
        isle_btn.setStyleSheet("font-weight: bold;")
        layout.addWidget(isle_btn)
        return widget

    # Methods for actions are the same as original file; they call self.db, so keep as-is
