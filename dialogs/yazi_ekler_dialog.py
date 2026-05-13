"""
YaziEklerDialog — Yazı Ekleri Zekası
======================================
Bir resmî yazı yüklendiğinde, yazının içindeki "Ek:" / "Ekler:" ve "İlgi:"
bölümleri otomatik olarak taranır. Bu dialog:

1. Tespit edilen ekleri kullanıcıya listeler.
2. Veritabanında mevcut projelerle benzerlik (Fuzzy) araştırması yapar.
3. Her ek satırı için:
   - Mevcut bir projeyle eşleştir (ve hangi revizyona bağlanacağını sor).
   - Yeni proje oluştur (kullanıcı dosya gösterir).
   - Atla / görmezden gel.
4. İlgi bölümünü ayrı bilgi olarak gösterir (mevcut yazıyla cross-reference).
5. Eksik ek sayısı uyarısı verir.
"""

import os
import re
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Yardımcı: Proje adı benzerliği (basit token overlap)
# ---------------------------------------------------------------------------

def _similarity_score(a: str, b: str) -> float:
    """0.0-1.0 arası basit token benzerlik skoru."""
    tokens_a = set(re.findall(r"[a-zA-ZğüşıöçĞÜŞİÖÇ0-9]+", a.lower()))
    tokens_b = set(re.findall(r"[a-zA-ZğüşıöçĞÜŞİÖÇ0-9]+", b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))


def _parse_ek_lines(ekler_raw: str) -> List[str]:
    """
    Backward-compat: convert pipe-joined raw string to list.
    Used when ekler_listesi is not available.
    """
    if not ekler_raw:
        return []
    parts = [p.strip() for p in ekler_raw.split("|")]
    cleaned = []
    for part in parts:
        part = re.sub(r"^[\d]+[).\-]\s*", "", part).strip()
        if part and len(part) >= 3:
            cleaned.append(part)
    return cleaned


def _ekler_listesi_to_rows(ekler_listesi: list, ekler_raw: str) -> list:
    """
    Normalise the structured ekler_listesi (from parse_letter_text) into a
    simple list of dicts used by the dialog rows.
    Falls back to splitting ekler_raw string if ekler_listesi is empty.
    """
    if ekler_listesi:
        return ekler_listesi  # already structured
    # Fallback: build minimal dicts from raw string
    return [
        {"sira": i + 1, "ham_metin": t, "kod": "", "ad": t, "revizyon": ""}
        for i, t in enumerate(_parse_ek_lines(ekler_raw))
    ]

# ---------------------------------------------------------------------------
# Ana Dialog
# ---------------------------------------------------------------------------

class YaziEklerDialog(QDialog):
    """
    Yazı Ekleri Yönetim Diyalogu.

    Parametreler
    ------------
    parent : QWidget
        Ana pencere (main_window.py).
    db :
        ProjeTakipDB örneği.
    yazi_no : str
        Yazının numarası.
    yazi_tarih : str
        Yazının tarihi.
    ekler_raw : str
        parse_letter_text tarafından döndürülen ham ekler metni.
    ilgi_raw : str
        İlgi bölümü ham metni.
    intelligence_service :
        DocumentIntelligenceService örneği (OCR için).
    """

    # Sütun indeksleri
    COL_EK = 0
    COL_DB_ESLESME = 1
    COL_ISLEM = 2
    COL_DOSYA = 3
    COL_REVIZYON = 4
    COL_DAHIL = 5

    def __init__(
        self,
        parent,
        db,
        yazi_no: str,
        yazi_tarih: str,
        ekler_raw: str,
        ilgi_raw: str = "",
        intelligence_service=None,
        ekler_listesi: Optional[list] = None,
        islem_turu: str = "gelen",
    ):
        super().__init__(parent)
        self.db = db
        self.yazi_no = yazi_no
        self.yazi_tarih = yazi_tarih
        self.ekler_raw = ekler_raw
        self.ilgi_raw = ilgi_raw
        self.intelligence_service = intelligence_service
        self.islem_turu = islem_turu
        # Prefer structured list; fall back to parsing raw string
        self._ek_rows: List[dict] = _ekler_listesi_to_rows(
            ekler_listesi or [], ekler_raw
        )
        # Keep compat alias
        self._ek_satirlari: List[str] = [e.get("ham_metin", "") for e in self._ek_rows]
        self._dosya_map: Dict[int, str] = {}        # row -> dosya yolu
        self._proje_match_map: Dict[int, dict] = {} # row -> {"id", "kod", "isim"}

        self.setWindowTitle("📎 Yazı Eki Yönetimi")
        self.setMinimumSize(1050, 560)
        self.setSizeGripEnabled(True)

        # ── Ana layout ──────────────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Başlık bandı
        root.addWidget(self._build_header())

        # İlgi bölümü (varsa)
        if ilgi_raw and ilgi_raw.strip():
            root.addWidget(self._build_ilgi_panel())

        # Ana tablo
        root.addWidget(self._build_table_group())

        # Alt buton çubuğu
        root.addLayout(self._build_footer())

        # Tabloyu doldur
        self._populate_table()

    # ── UI İnşası ───────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        w = QFrame()
        w.setFrameShape(QFrame.StyledPanel)
        w.setStyleSheet("background:#f0f4ff; border-radius:6px; padding:8px;")
        h = QHBoxLayout(w)
        h.setContentsMargins(12, 8, 12, 8)

        icon_label = QLabel("📬")
        icon_label.setFont(QFont("Segoe UI", 20))

        info = QVBoxLayout()
        title = QLabel(f"<b>Yazı Ekleri Analizi</b> &nbsp; — &nbsp; "
                       f"Sayı: <b>{self.yazi_no}</b> &nbsp; | &nbsp; Tarih: <b>{self.yazi_tarih}</b>")
        title.setFont(QFont("Segoe UI", 11))
        sub = QLabel(
            f"Yazı içinde <b>{len(self._ek_rows)}</b> adet ek tespit edildi. "
            "Her ek için mevcut bir projeyle eşleştirin veya yeni proje oluşturun."
        )
        sub.setStyleSheet("color:#555;")
        sub.setWordWrap(True)
        info.addWidget(title)
        info.addWidget(sub)

        h.addWidget(icon_label)
        h.addLayout(info, 1)
        return w

    def _build_ilgi_panel(self) -> QGroupBox:
        grp = QGroupBox("🔗 İlgi (Referans Yazı)")
        grp.setStyleSheet("QGroupBox { font-weight:bold; color:#2563eb; }")
        ly = QVBoxLayout(grp)
        lbl = QLabel(self.ilgi_raw)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color:#374151; font-size:12px; padding:4px;")
        ly.addWidget(lbl)
        return grp

    def _build_table_group(self) -> QGroupBox:
        grp = QGroupBox("📋 Ekler Listesi ve Eşleştirme")
        ly = QVBoxLayout(grp)

        self.table = QTableWidget()
        headers = [
            "Ek Açıklaması",
            "DB Eşleşmesi",
            "İşlem",
            "Dosya / Proje",
            "Revizyon",
            "Dahil Et",
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(42)

        ly.addWidget(self.table)
        return grp

    def _build_footer(self) -> QHBoxLayout:
        h = QHBoxLayout()

        # Sol: Yeni Ek, Tümünü Dahil Et / Kaldır
        btn_ekle = QPushButton("➕ Manuel Ek Ekle")
        btn_ekle.setStyleSheet("font-weight:bold; color:#16a34a;")
        btn_ekle.clicked.connect(self._manuel_ek_ekle)
        h.addWidget(btn_ekle)

        sel_all = QPushButton("☑ Tümünü Dahil Et")
        sel_all.clicked.connect(lambda: self._set_all_dahil(True))
        sel_none = QPushButton("☐ Tümünü Kaldır")
        sel_none.clicked.connect(lambda: self._set_all_dahil(False))
        h.addWidget(sel_all)
        h.addWidget(sel_none)
        h.addStretch()

        # Sağ: OK / İptal
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("✅ Uygula")
        btn_box.button(QDialogButtonBox.Cancel).setText("Kapat")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        h.addWidget(btn_box)
        return h

    # ── Tablo Doldurma ve Manuel Ek ──────────────────────────────────────────

    def _manuel_ek_ekle(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Sütun 0: Ek açıklaması
        item = QTableWidgetItem("Manuel Ek")
        self.table.setItem(row, self.COL_EK, item)
        
        # Sütun 1: DB Eşleşmesi
        match_item = QTableWidgetItem("— (Bulunamadı)")
        match_item.setForeground(QColor("#9ca3af"))
        self.table.setItem(row, self.COL_DB_ESLESME, match_item)
        
        # Sütun 2: İşlem combo
        islem_combo = QComboBox()
        islem_combo.addItems([
            "Eşleştir (Mevcut)",
            "Yeni Proje Oluştur",
            "Atla",
        ])
        islem_combo.setCurrentIndex(1)  # Yeni Proje Oluştur varsayılan
        islem_combo.currentIndexChanged.connect(
            lambda idx, r=row: self._on_islem_changed(r, idx)
        )
        self.table.setCellWidget(row, self.COL_ISLEM, islem_combo)
        
        # Sütun 3: Dosya
        dosya_widget = self._build_dosya_widget(row, None)
        self.table.setCellWidget(row, self.COL_DOSYA, dosya_widget)
        
        # Sütun 4: Revizyon önerisi
        rev_label = QLabel("A (Yeni)")
        rev_label.setAlignment(Qt.AlignCenter)
        rev_label.setStyleSheet("color:#d97706;")
        self.table.setCellWidget(row, self.COL_REVIZYON, rev_label)
        
        # Sütun 5: Dahil Et
        cb = QCheckBox()
        cb.setChecked(True)
        cb_widget = QWidget()
        cb_ly = QHBoxLayout(cb_widget)
        cb_ly.addWidget(cb)
        cb_ly.setAlignment(Qt.AlignCenter)
        cb_ly.setContentsMargins(0, 0, 0, 0)
        self.table.setCellWidget(row, self.COL_DAHIL, cb_widget)

    def _populate_table(self):
        """Her ek satırı için bir tablo satırı oluştur ve DB araması yap."""
        self.table.setRowCount(len(self._ek_rows))

        try:
            tum_projeler = list(self.db.projeleri_listele())
        except Exception:
            tum_projeler = []

        for row, ek in enumerate(self._ek_rows):
            # Ek gösterim metni: ad varsa önce ad, sonra kod
            display = ek.get("ad") or ek.get("ham_metin", "")
            if ek.get("kod"):
                display = f"{ek['kod']}  {display}".strip()

            # Sütun 0: Ek açıklaması
            item = QTableWidgetItem(display)
            tooltip = (
                f"Kod: {ek.get('kod', '—')}\n"
                f"Ad: {ek.get('ad', '—')}\n"
                f"Revizyon: {ek.get('revizyon', '—')}\n"
                f"Ham: {ek.get('ham_metin', '—')}"
            )
            item.setToolTip(tooltip)
            self.table.setItem(row, self.COL_EK, item)

            # DB benzerlik araması (kod öncelikli)
            best_match = self._find_best_match(ek, tum_projeler)
            self._proje_match_map[row] = best_match

            # Sütun 1: DB Eşleşmesi
            if best_match:
                match_text = f"{best_match['kod']} — {best_match['isim'][:40]}"
                match_item = QTableWidgetItem(match_text)
                match_item.setForeground(QColor("#16a34a"))
                
                # ✅ GAP 1 FIX: Benzer eşleşmeleri tooltip'te göster
                benzer_eslesmeleri = self._find_best_matches(ek, tum_projeler, threshold=0.50, top_n=3)
                tooltip_text = f"Kod: {best_match['kod']}\n"
                tooltip_text += f"İsim: {best_match['isim']}\n"
                tooltip_text += f"Benzerlik: %{int(best_match['score'] * 100)}\n"
                
                if len(benzer_eslesmeleri) > 1:
                    tooltip_text += "\n📌 Diğer Benzer Projeler:\n"
                    for i, m in enumerate(benzer_eslesmeleri[1:], 1):
                        tooltip_text += f"  {i}. {m['kod']} — {m['isim'][:30]} (%{int(m['score'] * 100)})\n"
                
                match_item.setToolTip(tooltip_text.strip())
            else:
                match_item = QTableWidgetItem("— (Bulunamadı)")
                match_item.setForeground(QColor("#9ca3af"))
            self.table.setItem(row, self.COL_DB_ESLESME, match_item)

            # Sütun 2: İşlem combo
            islem_combo = QComboBox()
            islem_combo.addItems([
                "Eşleştir (Mevcut)",
                "Yeni Proje Oluştur",
                "Atla",
            ])
            if not best_match:
                islem_combo.setCurrentIndex(1)  # Yeni Proje Oluştur
            islem_combo.currentIndexChanged.connect(
                lambda idx, r=row: self._on_islem_changed(r, idx)
            )
            self.table.setCellWidget(row, self.COL_ISLEM, islem_combo)

            # Sütun 3: Dosya / Proje bilgisi
            dosya_widget = self._build_dosya_widget(row, best_match)
            self.table.setCellWidget(row, self.COL_DOSYA, dosya_widget)

            # Sütun 4: Revizyon önerisi
            rev_label = QLabel()
            rev_label.setAlignment(Qt.AlignCenter)
            # Use revision from ek if available, otherwise query DB
            if ek.get("revizyon") and not best_match:
                rev_label.setText(ek["revizyon"])
                rev_label.setStyleSheet("color:#d97706; font-weight:bold;")
            else:
                self._update_rev_label(row, rev_label, best_match, hint_rev=ek.get("revizyon", ""))
            self.table.setCellWidget(row, self.COL_REVIZYON, rev_label)

            # Sütun 5: Dahil Et checkbox
            cb = QCheckBox()
            cb.setChecked(True)
            cb_widget = QWidget()
            cb_ly = QHBoxLayout(cb_widget)
            cb_ly.addWidget(cb)
            cb_ly.setAlignment(Qt.AlignCenter)
            cb_ly.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, self.COL_DAHIL, cb_widget)


    def _build_dosya_widget(self, row: int, best_match: Optional[dict]) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(4, 0, 4, 0)
        h.setSpacing(4)

        label = QLabel("—")
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        label.setObjectName(f"dosya_label_{row}")

        # Eşleştirme modunda proje kodu göstermeye gerek yok, DB Sütununda var.
        # Sadece dosya yolunu göster.
        dosya_yolu = self._dosya_map.get(row)
        if dosya_yolu:
            label.setText(os.path.basename(dosya_yolu))
            
        btn_sec = QPushButton("📎")
        btn_sec.setFixedSize(QSize(28, 28))
        btn_sec.setToolTip("Ek Dosyasını (PDF vb.) Seç / Değiştir")
        btn_sec.clicked.connect(lambda _, r=row: self._dosya_sec_only(r))

        btn_ara = QPushButton("🔍")
        btn_ara.setFixedSize(QSize(28, 28))
        btn_ara.setToolTip("Eşleştirilecek Projeyi Seç / Değiştir")
        btn_ara.clicked.connect(lambda _, r=row: self._eslesme_sec_dialog(r))

        h.addWidget(label, 1)
        h.addWidget(btn_sec)
        h.addWidget(btn_ara)
        return w

    # ── Event Handlers ──────────────────────────────────────────────────────

    def _on_islem_changed(self, row: int, idx: int):
        """İşlem combo değiştiğinde revizyon label ve dosya gösterimini güncelle."""
        rev_widget = self.table.cellWidget(row, self.COL_REVIZYON)
        match = self._proje_match_map.get(row)

        if idx == 0:  # Eşleştir (Mevcut)
            self._update_rev_label(row, rev_widget, match)
        elif idx == 1:  # Yeni Proje Oluştur
            if isinstance(rev_widget, QLabel):
                rev_widget.setText("A (Yeni)")
                rev_widget.setStyleSheet("color:#d97706;")
        else:  # Atla
            if isinstance(rev_widget, QLabel):
                rev_widget.setText("—")
                rev_widget.setStyleSheet("color:#9ca3af;")

    def _dosya_sec_only(self, row: int):
        """Kullanıcı ek dosyasını bilgisayardan seçmek için tıkladı."""
        dosya_yolu, _ = QFileDialog.getOpenFileName(
            self,
            "Ek Dosyasını Seç",
            "",
            "Desteklenen Dosyalar (*.pdf *.dwg *.doc *.docx *.xls *.xlsx *.jpg *.png);;Tüm Dosyalar (*.*)",
        )
        if not dosya_yolu:
            return

        self._dosya_map[row] = dosya_yolu
        self._update_dosya_label(row, os.path.basename(dosya_yolu))

        # Dosyadan proje bilgisi çıkar (OCR veya dosya adı)
        dosya_bilgi = {}
        if self.intelligence_service:
            try:
                dosya_bilgi = self.intelligence_service.analyze_project_document(dosya_yolu)
            except Exception:
                pass

        dosya_kod = (dosya_bilgi.get("kod") or "").strip().upper()

        islem_combo = self.table.cellWidget(row, self.COL_ISLEM)
        idx = islem_combo.currentIndex() if islem_combo else 0

        if idx == 0:
            # Eşleştir modu — dosya kodu mevcut eşleşmeyle uyuşuyor mu kontrol et
            match = self._proje_match_map.get(row)
            if match and dosya_kod and match.get("kod"):
                match_kod = match["kod"].upper()
                if dosya_kod != match_kod and not dosya_kod.startswith(match_kod) and not match_kod.startswith(dosya_kod):
                    QMessageBox.warning(
                        self,
                        "⚠️ Dosya Uyuşmazlığı",
                        f"Seçtiğiniz dosyadaki proje kodu ile eşleşen proje kodu farklı:\n\n"
                        f"  Dosyadaki kod:  {dosya_kod}\n"
                        f"  Eşleşen proje: {match_kod}\n\n"
                        f"Yanlış dosya seçmiş olabilirsiniz. Lütfen kontrol edin.",
                    )
        else:
            # Yeni Proje veya henüz karar verilmemiş — dosyadan bilgi çıkar ve DB'de ara
            if dosya_kod or dosya_bilgi.get("isim"):
                # ✅ GAP 2 FIX: Benzer projeleri bul
                try:
                    tum_projeler = list(self.db.projeleri_listele())
                except Exception:
                    tum_projeler = []
                
                benzer_projeler = self._find_best_matches(
                    {"kod": dosya_kod, "ad": dosya_bilgi.get("isim", ""), "ham_metin": dosya_bilgi.get("isim", "")},
                    tum_projeler,
                    threshold=0.40,
                    top_n=5
                )
                
                if len(benzer_projeler) > 0:
                    # Benzer proje varsa ProjeSecDialog'u aç
                    from .proje_sec_dialog import ProjeSecDialog
                    
                    msg_text = f"Dosyada tespit edilen kod/isim: {dosya_kod or dosya_bilgi.get('isim', 'Bilinmiyor')}\n\n"
                    
                    if len(benzer_projeler) == 1:
                        # Tek eşleşme → otomatik kullan
                        msg_text += f"Bu ek için {len(benzer_projeler)} benzer proje bulundu:\n"
                        msg_text += f"\n  {benzer_projeler[0]['kod']} — {benzer_projeler[0]['isim'][:50]}\n"
                        msg_text += "\nBu projeyi kullanmak ister misiniz?"
                        
                        cevap = QMessageBox.question(
                            self,
                            "Benzer Proje Bulundu",
                            msg_text,
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes,
                        )
                        if cevap == QMessageBox.Yes:
                            match = benzer_projeler[0]
                            self._proje_match_map[row] = match
                            if islem_combo:
                                islem_combo.setCurrentIndex(0)  # Eşleştir
                            # Eşleşme sütununu güncelle
                            match_item = self.table.item(row, self.COL_DB_ESLESME)
                            if match_item:
                                match_item.setText(f"{match['kod']} — {match['isim'][:40]}")
                                match_item.setForeground(QColor("#16a34a"))
                            # Revizyon önerisini güncelle
                            rev_widget = self.table.cellWidget(row, self.COL_REVIZYON)
                            self._update_rev_label(row, rev_widget, match)
                            return  # ✅ İşlem tamamlandı
                        # Hayır derirse devam et (yeni proje oluşturacak)
                    else:
                        # Birden fazla eşleşme → liste sunarak seçtir
                        msg_text += f"Bu ek için {len(benzer_projeler)} benzer proje bulundu.\n"
                        msg_text += "Lütfen listeden uygun olanı seçin veya yeni proje oluşturmak için İptal'e tıklayın."
                        
                        msg_box = QMessageBox(self)
                        msg_box.setWindowTitle("📋 Benzer Projeler Bulundu")
                        msg_box.setText(msg_text)
                        btn_list = msg_box.addButton("📋 Listeden Seç", QMessageBox.AcceptRole)
                        msg_box.addButton("Yeni Proje Oluştur", QMessageBox.RejectRole)
                        msg_box.exec()
                        
                        if msg_box.clickedButton() == btn_list:
                            # ProjeSecDialog'u aç
                            dialog = ProjeSecDialog(
                                self, 
                                self.db, 
                                title=f"Benzer Projeler - Kodya / İsme Göre Seç ({len(benzer_projeler)} bulundu)",
                                projeler_listesi=benzer_projeler
                            )
                            if dialog.exec():
                                selected = dialog.selected_project()
                                if selected:
                                    self._proje_match_map[row] = selected
                                    if islem_combo:
                                        islem_combo.setCurrentIndex(0)  # Eşleştir
                                    # Eşleşme sütununu güncelle
                                    match_item = self.table.item(row, self.COL_DB_ESLESME)
                                    if match_item:
                                        match_item.setText(f"{selected['kod']} — {selected['isim'][:40]}")
                                        match_item.setForeground(QColor("#16a34a"))
                                    # Revizyon önerisini güncelle
                                    rev_widget = self.table.cellWidget(row, self.COL_REVIZYON)
                                    self._update_rev_label(row, rev_widget, selected)
                                    self._update_dosya_label(row, f"🔗 {selected['kod']}")
                                    return  # ✅ İşlem tamamlandı
                        # Hayır derirse yeni proje oluşturacak
                
                # Eşleşme bulunamadı veya yeni proje oluşturmak istedi → devam et
                self._proje_match_map[row] = {
                    "id": None,
                    "kod": dosya_bilgi.get("kod", ""),
                    "isim": dosya_bilgi.get("isim", ""),
                    "score": 1.0,
                    "yeni": True,
                }

            # Revizyon önerisini güncelle
            rev_widget = self.table.cellWidget(row, self.COL_REVIZYON)
            match = self._proje_match_map.get(row)
            self._update_rev_label(row, rev_widget, match, hint_rev=dosya_bilgi.get("revizyon", ""))

    def _eslesme_sec_dialog(self, row: int):
        """Mevcut projelerden birini seçmek için canlı arama diyalogu aç."""
        from .proje_sec_dialog import ProjeSecDialog
        dialog = ProjeSecDialog(self, self.db, title="Eşleştirilecek Projeyi Seç")
        if not dialog.exec():
            return
        secilen = dialog.selected_project()
        if not secilen:
            return

        proje_kodu = secilen["kod"]
        proje_isim = secilen["isim"]
        pid = secilen["id"]

        self._proje_match_map[row] = {
            "id": pid,
            "kod": proje_kodu,
            "isim": proje_isim,
            "score": 1.0,
            "yeni": False,
        }
        self._update_dosya_label(row, f"🔗 {proje_kodu}")
        rev_widget = self.table.cellWidget(row, self.COL_REVIZYON)
        self._update_rev_label(row, rev_widget, self._proje_match_map[row])
        # Eşleşme sütununu güncelle
        match_item = self.table.item(row, self.COL_DB_ESLESME)
        if match_item:
            match_item.setText(f"{proje_kodu} — {proje_isim[:40]}")
            match_item.setForeground(QColor("#16a34a"))
        # İşlem combo'yu Eşleştir olarak ayarla
        islem_combo = self.table.cellWidget(row, self.COL_ISLEM)
        if islem_combo:
            islem_combo.setCurrentIndex(0)

    def _update_dosya_label(self, row: int, text: str):
        w = self.table.cellWidget(row, self.COL_DOSYA)
        if w:
            lbl = w.findChild(QLabel, f"dosya_label_{row}")
            if lbl:
                lbl.setText(text)

    def _update_rev_label(self, row: int, rev_widget, match: Optional[dict], hint_rev: str = ""):
        if not isinstance(rev_widget, QLabel):
            return
        if match and match.get("id"):
            try:
                onerilen = ""
                if self.islem_turu == "giden":
                    row_db = self.db.cursor.execute(
                        "SELECT revizyon_kodu FROM revizyonlar WHERE proje_id=? ORDER BY id DESC LIMIT 1",
                        (match["id"],)
                    ).fetchone()
                    if row_db and row_db[0]:
                        onerilen = row_db[0]
                    else:
                        onerilen = "A"
                else:
                    onerilen = self.db.sonraki_revizyon_kodu_onerisi(match["id"], "gelen")
                    
                rev_widget.setText(onerilen)
                rev_widget.setStyleSheet("color:#16a34a; font-weight:bold;")
            except Exception:
                rev_widget.setText(hint_rev or "?")
                rev_widget.setStyleSheet("color:#9ca3af;")
        elif hint_rev:
            rev_widget.setText(hint_rev)
            rev_widget.setStyleSheet("color:#d97706; font-weight:bold;")
        else:
            rev_widget.setText("A (Yeni)")
            rev_widget.setStyleSheet("color:#d97706;")

    def _set_all_dahil(self, checked: bool):
        for row in range(self.table.rowCount()):
            cb_w = self.table.cellWidget(row, self.COL_DAHIL)
            if cb_w:
                cb = cb_w.findChild(QCheckBox)
                if cb:
                    cb.setChecked(checked)

    # ── DB Benzerlik Araması ─────────────────────────────────────────────────

    def _find_best_match(self, ek: dict, tum_projeler: list) -> Optional[dict]:
        """
        Find the closest project in DB.
        Priority: exact doc-code match > code-prefix match > fuzzy isim/kod match.
        """
        if not tum_projeler:
            return None

        ek_kod = (ek.get("kod") or "").strip().upper()
        ek_ad = (ek.get("ad") or ek.get("ham_metin") or "").strip()

        best_score = 0.0
        best_proje = None

        for p in tum_projeler:
            proje_kod = getattr(p, "proje_kodu", "") or ""
            proje_isim = getattr(p, "proje_ismi", "") or ""

            # Exact code match → top priority
            if ek_kod and proje_kod.upper() == ek_kod:
                return {
                    "id": getattr(p, "id", None),
                    "kod": proje_kod,
                    "isim": proje_isim,
                    "score": 1.0,
                    "yeni": False,
                }

            # Code-prefix/contains match (e.g. ek_kod contains proje_kod or vice versa)
            if ek_kod and proje_kod:
                upper_proje = proje_kod.upper()
                if ek_kod.startswith(upper_proje) or upper_proje.startswith(ek_kod):
                    prefix_score = min(len(ek_kod), len(upper_proje)) / max(len(ek_kod), len(upper_proje))
                    if prefix_score > best_score:
                        best_score = prefix_score
                        best_proje = p
                    continue

            # Fuzzy score using both ad and kod
            kod_score = _similarity_score(ek_kod, proje_kod) if ek_kod else 0.0
            isim_score = _similarity_score(ek_ad, proje_isim)
            ham_score = _similarity_score(ek.get("ham_metin", ""), proje_isim)
            score = max(kod_score, isim_score, ham_score)

            if score > best_score:
                best_score = score
                best_proje = p

        if best_score >= 0.30 and best_proje is not None:
            return {
                "id": getattr(best_proje, "id", None),
                "kod": getattr(best_proje, "proje_kodu", ""),
                "isim": getattr(best_proje, "proje_ismi", ""),
                "score": best_score,
                "yeni": False,
            }
        return None

    def _find_best_matches(self, ek: dict, tum_projeler: list, threshold: float = 0.30, top_n: int = 5) -> List[dict]:
        """
        Find all matching projects in DB (sorted by score).
        Returns top-N matches above threshold.
        """
        if not tum_projeler:
            return []

        ek_kod = (ek.get("kod") or "").strip().upper()
        ek_ad = (ek.get("ad") or ek.get("ham_metin") or "").strip()
        
        matches = []
        exact_match_found = False

        for p in tum_projeler:
            proje_kod = getattr(p, "proje_kodu", "") or ""
            proje_isim = getattr(p, "proje_ismi", "") or ""
            score = 0.0

            # Exact code match → top priority
            if ek_kod and proje_kod.upper() == ek_kod:
                score = 1.0
                exact_match_found = True
            # Code-prefix/contains match
            elif ek_kod and proje_kod:
                upper_proje = proje_kod.upper()
                if ek_kod.startswith(upper_proje) or upper_proje.startswith(ek_kod):
                    score = min(len(ek_kod), len(upper_proje)) / max(len(ek_kod), len(upper_proje))
            # Fuzzy score
            else:
                kod_score = _similarity_score(ek_kod, proje_kod) if ek_kod else 0.0
                isim_score = _similarity_score(ek_ad, proje_isim)
                ham_score = _similarity_score(ek.get("ham_metin", ""), proje_isim)
                score = max(kod_score, isim_score, ham_score)

            if score >= threshold:
                matches.append({
                    "id": getattr(p, "id", None),
                    "kod": proje_kod,
                    "isim": proje_isim,
                    "score": score,
                    "yeni": False,
                })

        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:top_n]

    # ── Sonuç ────────────────────────────────────────────────────────────────

    def get_results(self) -> List[dict]:
        """
        Dialog kapatıldıktan sonra çağrılır.
        Her dahil edilen ek için bir dict döndürür:
        {
            "ek_metin": str,
            "islem": "eslesme" | "yeni" | "atla",
            "proje_id": int | None,
            "proje_kodu": str,
            "proje_isim": str,
            "dosya_yolu": str | None,
            "revizyon": str,
            "yeni_mi": bool,
        }
        """
        results = []
        for row in range(self.table.rowCount()):
            # Dahil checkbox
            cb_w = self.table.cellWidget(row, self.COL_DAHIL)
            if cb_w:
                cb = cb_w.findChild(QCheckBox)
                if cb and not cb.isChecked():
                    continue

            ek_item = self.table.item(row, self.COL_EK)
            ek_metin = ek_item.text() if ek_item else ""

            islem_combo = self.table.cellWidget(row, self.COL_ISLEM)
            idx = islem_combo.currentIndex() if islem_combo else 2
            if idx == 2:  # Atla
                continue

            islem = "eslesme" if idx == 0 else "yeni"
            match = self._proje_match_map.get(row, {})
            dosya_yolu = self._dosya_map.get(row)

            rev_widget = self.table.cellWidget(row, self.COL_REVIZYON)
            revizyon = rev_widget.text() if isinstance(rev_widget, QLabel) else "A"

            results.append({
                "ek_metin": ek_metin,
                "islem": islem,
                "proje_id": match.get("id"),
                "proje_kodu": match.get("kod", ""),
                "proje_isim": match.get("isim", ""),
                "dosya_yolu": dosya_yolu,
                "revizyon": revizyon,
                "yeni_mi": match.get("yeni", False) or islem == "yeni",
            })
        return results

    def accept(self):
        """OK tıklandığında en az bir 'Dahil' satır olduğunu kontrol et."""
        results = self.get_results()
        if not results:
            cevap = QMessageBox.question(
                self,
                "Ek Seçilmedi",
                "Hiçbir ek dahil edilmedi. Yine de kapamak istiyor musunuz?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if cevap == QMessageBox.No:
                return
        super().accept()
