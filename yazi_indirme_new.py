"""
Yazı Dökümanları İndirme Aracı (ProjeTakipDB uyumlu) - cleaned implementation
=============================================================================

This module contains the updated implementation using ProjeTakipDB and provides
a GUI to select DB and download documents.
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QProgressBar,
    QGroupBox,
    QFormLayout,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

from database import ProjeTakipDB
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class IndirmeWorker(QThread):
    ilerleme = Signal(int, int)
    tamamlandi = Signal(int, int)
    hata = Signal(str)

    def __init__(self, db_path: str, yazi_listesi: List[Dict], hedef_klasor: str):
        super().__init__()
        self.db_path = db_path
        self.yazi_listesi = yazi_listesi
        self.hedef_klasor = hedef_klasor
        self.basarili = 0
        self.hatali = 0

    def run(self):
        try:
            db = ProjeTakipDB(self.db_path)
        except Exception as e:
            self.hata.emit(str(e))
            return

        try:
            toplam = len(self.yazi_listesi)
            for i, yazi in enumerate(self.yazi_listesi, 1):
                self.ilerleme.emit(i, toplam)
                try:
                    db.cursor.execute("SELECT dosya_adi, dosya_verisi FROM yazi_dokumanlari WHERE id = ?", (yazi["id"],))
                    row = db.cursor.fetchone()
                    if not row:
                        self.hatali += 1
                        continue
                    dosya_adi, dosya_verisi = row[0], row[1]
                    tur_klasoru = Path(self.hedef_klasor) / (yazi.get("yazi_turu") or "_")
                    tur_klasoru.mkdir(parents=True, exist_ok=True)
                    guvenli = self._guvenli_dosya_adi_yap(dosya_adi)
                    hedef = tur_klasoru / guvenli
                    sayac = 1
                    while hedef.exists():
                        ad, uzanti = os.path.splitext(guvenli)
                        hedef = tur_klasoru / f"{ad}_{sayac}{uzanti}"
                        sayac += 1
                    with open(hedef, "wb") as f:
                        f.write(dosya_verisi)
                    self.basarili += 1
                except Exception:
                    self.hatali += 1

            self.tamamlandi.emit(self.basarili, self.hatali)
        finally:
            try:
                db.close()
            except Exception:
                try:
                    db.cleanup_connections()
                except Exception:
                    pass

    def _guvenli_dosya_adi_yap(self, dosya_adi: str) -> str:
        yasak = '<>:"/\\|?*'
        for c in yasak:
            dosya_adi = dosya_adi.replace(c, "_")
        return dosya_adi


class YaziIndirmeArayuz(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db: Optional[ProjeTakipDB] = None
        self.db_path: Optional[str] = None
        self.yazi_listesi: List[Dict] = []
        self.secili_yazilar: List[Dict] = []
        self.hedef_klasor: Optional[str] = None
        self.indirme_worker = None
        self.settings_path = Path.home() / ".proj_takip_yazi_indirme.json"
        self.init_ui()
        self._load_settings()

    def init_ui(self):
        self.setWindowTitle("Yazı Dokümanları İndirme Aracı")
        self.resize(900, 600)
        ana = QWidget()
        self.setCentralWidget(ana)
        vbox = QVBoxLayout(ana)

        title = QLabel("📄 Yazı Dokümanları İndirme Aracı")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)

        filtre_group = QGroupBox("🔍 Filtreler")
        form = QFormLayout()
        hbox = QHBoxLayout()
        self.db_label = QLabel("Veritabanı: (seçilmedi)")
        self.db_btn = QPushButton("🗄️ Veritabanı Seç")
        self.db_btn.clicked.connect(self.veritabani_sec)
        hbox.addWidget(self.db_label)
        hbox.addWidget(self.db_btn)
        form.addRow("Veritabanı:", hbox)

        self.tur_combo = QComboBox()
        self.tur_combo.currentTextChanged.connect(self.yazilari_yukle)
        form.addRow("Yazı Türü:", self.tur_combo)
        filtre_group.setLayout(form)
        vbox.addWidget(filtre_group)

        self.tablo = QTableWidget()
        self.tablo.setColumnCount(6)
        self.tablo.setHorizontalHeaderLabels(["ID", "Yazı No", "Yazı Tarihi", "Dosya Adı", "Tür", "Boyut (KB)"])
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        vbox.addWidget(self.tablo)
        # connect selection changes to toggle download button
        self.tablo.selectionModel().selectionChanged.connect(self._selection_changed)

        btns = QHBoxLayout()
        self.tum_sec_btn = QPushButton("✓ Tümünü Seç")
        self.tum_sec_btn.clicked.connect(self.tum_satirlari_sec)
        btns.addWidget(self.tum_sec_btn)
        self.sec_kaldir_btn = QPushButton("✗ Seçimi Kaldır")
        self.sec_kaldir_btn.clicked.connect(self.secimi_kaldir)
        btns.addWidget(self.sec_kaldir_btn)
        btns.addStretch()
        self.klasor_btn = QPushButton("📁 Hedef Klasör Seç")
        self.klasor_btn.clicked.connect(self.klasor_sec)
        btns.addWidget(self.klasor_btn)
        self.indir_btn = QPushButton("⬇️ Seçilenleri İndir")
        self.indir_btn.clicked.connect(self.yazilari_indir)
        self.indir_btn.setEnabled(False)
        btns.addWidget(self.indir_btn)
        self.tumunu_indir_btn = QPushButton("⬇️ Tümünü İndir")
        self.tumunu_indir_btn.clicked.connect(self.tumunu_indir)
        self.tumunu_indir_btn.setEnabled(False)
        btns.addWidget(self.tumunu_indir_btn)
        vbox.addLayout(btns)

        self.status = self.statusBar()
        self.status_label = QLabel("Veritabanı seçilmedi")
        self.status.addWidget(self.status_label)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        vbox.addWidget(self.progress)

        # try default db
        default = os.path.join(os.getcwd(), "projeler.db")
        if os.path.exists(default):
            self.db_path = default
            self.db_label.setText(f"Veritabanı: {default}")
            self.veritabani_baglan(default)

    def veritabani_sec(self):
        dosya, _ = QFileDialog.getOpenFileName(self, "Veritabanı Dosyasını Seçin", os.getcwd(), "SQLite DB Files (*.db *.sqlite);;All Files (*)")
        if dosya:
            self.db_path = dosya
            self.db_label.setText(f"Veritabanı: {dosya}")
            self.veritabani_baglan(dosya)

    def veritabani_baglan(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        if not self.db_path or not os.path.exists(self.db_path):
            self.status_label.setText("❌ Veritabanı bulunamadı")
            return
        old_db = self.db
        try:
            new_db = ProjeTakipDB(self.db_path)
            self.db = new_db
            if old_db:
                try:
                    old_db.close()
                except Exception:
                    try:
                        old_db.cleanup_connections()
                    except Exception:
                        pass
            # persist last db selection
            self._save_settings()
        except Exception as e:
            self.db = old_db
            QMessageBox.critical(self, "Veritabanı Hatası", f"Veritabanı açılamadı: {e}")
            return
        self.db_label.setText(f"Veritabanı: {self.db_path}")
        self.status_label.setText("✓ Veritabanı bağlı")
        # load types
        try:
            self.tur_combo.clear()
            self.tur_combo.addItem("Tümü")
            self.db.cursor.execute("SELECT DISTINCT yazi_turu FROM yazi_dokumanlari WHERE yazi_turu IS NOT NULL ORDER BY yazi_turu")
            rows = self.db.cursor.fetchall()
            types = [r[0] for r in rows if r and r[0]]
            if types:
                self.tur_combo.addItems(types)
                self.yazilari_yukle()
            # after loading rows, we can enable download buttons if a target folder exists
            if getattr(self, 'hedef_klasor', None):
                has_rows = bool(self.yazi_listesi)
                self.indir_btn.setEnabled(has_rows)
                self.tumunu_indir_btn.setEnabled(has_rows)
        except Exception as e:
            logger.error(f"Yazı türleri yüklenemedi: {e}")

    def yazilari_yukle(self):
        if not self.db:
            return
        tur = self.tur_combo.currentText()
        try:
            if tur and tur != "Tümü":
                self.db.cursor.execute(
                    """
                    SELECT id, yazi_no, COALESCE(yazi_tarih, ''), dosya_adi, yazi_turu,
                           LENGTH(dosya_verisi) as boyut
                    FROM yazi_dokumanlari
                    WHERE yazi_turu = ?
                    ORDER BY yazi_no, COALESCE(yazi_tarih, '') DESC, id DESC
                    """,
                    (tur,),
                )
            else:
                self.db.cursor.execute(
                    """
                    SELECT id, yazi_no, COALESCE(yazi_tarih, ''), dosya_adi, yazi_turu,
                           LENGTH(dosya_verisi) as boyut
                    FROM yazi_dokumanlari
                    ORDER BY yazi_turu, yazi_no, COALESCE(yazi_tarih, '') DESC, id DESC
                    """
                )
            rows = self.db.cursor.fetchall()
            self.yazi_listesi = [
                {
                    "id": r[0],
                    "yazi_no": r[1],
                    "yazi_tarih": r[2],
                    "dosya_adi": r[3],
                    "yazi_turu": r[4],
                    "boyut": r[5],
                }
                for r in rows
            ]
            self.tablo.setRowCount(len(self.yazi_listesi))
            for i, y in enumerate(self.yazi_listesi):
                self.tablo.setItem(i, 0, QTableWidgetItem(str(y["id"])))
                self.tablo.setItem(i, 1, QTableWidgetItem(y["yazi_no"]))
                self.tablo.setItem(i, 2, QTableWidgetItem(y["yazi_tarih"] or "-"))
                self.tablo.setItem(i, 3, QTableWidgetItem(y["dosya_adi"]))
                self.tablo.setItem(i, 4, QTableWidgetItem(y["yazi_turu"]))
                self.tablo.setItem(i, 5, QTableWidgetItem(f"{(y['boyut'] or 0)/1024:.2f}"))
            self.status_label.setText(f"✓ {len(self.yazi_listesi)} yazı dokümanı listelendi")
            # toggle download buttons depending on whether we have selection and target folder
            has_rows = len(self.yazi_listesi) > 0
            if getattr(self, 'hedef_klasor', None):
                self.indir_btn.setEnabled(has_rows)
                self.tumunu_indir_btn.setEnabled(has_rows)
            # also update selection-based button state
            self._selection_changed()
        except Exception as e:
            logger.error(f"Yazılar yüklenemedi: {e}")

    def tum_satirlari_sec(self):
        self.tablo.selectAll()

    def secimi_kaldir(self):
        self.tablo.clearSelection()

    def klasor_sec(self):
        klasor = QFileDialog.getExistingDirectory(self, "Dokümanların İndirileceği Klasörü Seçin", os.getcwd(), QFileDialog.ShowDirsOnly)
        if klasor:
            self.hedef_klasor = klasor
            self.indir_btn.setEnabled(True)
            self.tumunu_indir_btn.setEnabled(bool(self.yazi_listesi))
            self.status_label.setText(f"📁 Hedef klasör: {klasor}")
            self._save_settings()
            # update button state in case there's a selection
            self._selection_changed()

    def yazilari_indir(self):
        if not self.hedef_klasor:
            QMessageBox.warning(self, "Uyarı", "Önce hedef klasörü seçmelisiniz!")
            return
        rows = self.tablo.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen indirmek istediğiniz yazıları seçin!")
            return
        self.secili_yazilar = [self.yazi_listesi[r.row()] for r in rows if 0 <= r.row() < len(self.yazi_listesi)]
        if not self.secili_yazilar:
            return
        cevap = QMessageBox.question(self, "İndirme Onayı", f"{len(self.secili_yazilar)} adet yazı indirilecek.\nDevam edilsin mi?", QMessageBox.Yes | QMessageBox.No)
        if cevap != QMessageBox.Yes:
            return
        self.indirme_baslat()

    def tumunu_indir(self):
        if not self.hedef_klasor:
            QMessageBox.warning(self, "Uyarı", "Önce hedef klasörü seçmelisiniz!")
            return
        if not self.yazi_listesi:
            QMessageBox.warning(self, "Uyarı", "İndirilecek yazı yok!")
            return
        self.secili_yazilar = list(self.yazi_listesi)
        cevap = QMessageBox.question(self, "İndirme Onayı", f"Tüm ({len(self.secili_yazilar)}) yazı indirilecek. Devam edilsin mi?", QMessageBox.Yes | QMessageBox.No)
        if cevap != QMessageBox.Yes:
            return
        self.indirme_baslat()

    def _selection_changed(self, *args, **kwargs):
        try:
            selected = self.tablo.selectionModel().selectedRows()
            has_selection = len(selected) > 0
            # only enable the button if folder is selected and there is a selection
            if getattr(self, 'hedef_klasor', None) and has_selection:
                self.indir_btn.setEnabled(True)
            else:
                # if no selection, don't enable unless tumunu_indir is used
                self.indir_btn.setEnabled(False)
        except Exception:
            pass

    def indirme_baslat(self):
        if not self.db_path:
            QMessageBox.critical(self, "Hata", "Önce veritabanı seçin")
            return
        self.indir_btn.setEnabled(False)
        self.klasor_btn.setEnabled(False)
        self.tur_combo.setEnabled(False)
        self.tumunu_indir_btn.setEnabled(False)
        self.progress.setVisible(True)
        # start background worker
        try:
            self.progress.setRange(0, len(self.secili_yazilar) or 1)
            self.progress.setValue(0)
            self.indirme_worker = IndirmeWorker(self.db_path, self.secili_yazilar, self.hedef_klasor)
            self.indirme_worker.ilerleme.connect(self.ilerleme_guncelle)
            self.indirme_worker.tamamlandi.connect(self.indirme_tamamlandi)
            self.indirme_worker.hata.connect(self.indirme_hatasi)
            self.indirme_worker.start()
            self.status_label.setText(f"⬇️ {len(self.secili_yazilar)} yazı indiriliyor...")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İndirme başlatılamadı: {e}")
            self.indir_btn.setEnabled(True)
            self.klasor_btn.setEnabled(True)
            self.tur_combo.setEnabled(True)
            self.progress.setVisible(False)

    def ilerleme_guncelle(self, i: int, toplam: int):
        try:
            self.progress.setRange(0, toplam or 1)
            self.progress.setValue(i)
            self.status_label.setText(f"⬇️ İndiriliyor: {i}/{toplam}")
        except Exception:
            pass

    def indirme_tamamlandi(self, basarili: int, hatali: int):
        QMessageBox.information(self, "İndirme Tamamlandı", f"İşlem tamamlandı. Başarılı: {basarili}, Hatalı: {hatali}")
        self.status_label.setText(f"✓ İndirildi: {basarili}, Hata: {hatali}")
        self.indir_btn.setEnabled(True)
        self.klasor_btn.setEnabled(True)
        self.tur_combo.setEnabled(True)
        self.progress.setVisible(False)
        # cleanup worker
        try:
            self.indirme_worker.quit()
            self.indirme_worker.wait(5000)
        except Exception:
            pass
        self.indirme_worker = None
        # Save last successful folder
        try:
            self._save_settings()
        except Exception:
            pass
        self.tumunu_indir_btn.setEnabled(True)

    def indirme_hatasi(self, hata: str):
        QMessageBox.critical(self, "İndirme Hatası", hata)
        self.status_label.setText(f"❌ Hata: {hata}")
        self.indir_btn.setEnabled(True)
        self.klasor_btn.setEnabled(True)
        self.tur_combo.setEnabled(True)
        self.progress.setVisible(False)
        if self.indirme_worker:
            try:
                self.indirme_worker.quit()
                self.indirme_worker.wait(3000)
            except Exception:
                pass
        self.indirme_worker = None
        self.tumunu_indir_btn.setEnabled(True)

    def closeEvent(self, event):
        if self.indirme_worker and self.indirme_worker.isRunning():
            try:
                self.indirme_worker.quit()
                self.indirme_worker.wait(3000)
            except Exception:
                pass
        if self.db:
            try:
                self.db.close()
            except Exception:
                try:
                    self.db.cleanup_connections()
                except Exception:
                    pass
        event.accept()

    # --------------------------- Settings ---------------------------
    def _load_settings(self):
        try:
            if self.settings_path.exists():
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    last_db = d.get('last_db')
                    last_folder = d.get('last_folder')
                    if last_db and os.path.exists(last_db):
                        self.db_path = last_db
                        self.db_label.setText(f"Veritabanı: {last_db}")
                        self.veritabani_baglan(last_db)
                    if last_folder and os.path.exists(last_folder):
                        self.hedef_klasor = last_folder
                        self.status_label.setText(f"📁 Hedef klasör: {last_folder}")
                        # set download buttons according to the loaded rows
                        has_rows = bool(self.yazi_listesi)
                        self.indir_btn.setEnabled(has_rows)
                        self.tumunu_indir_btn.setEnabled(has_rows)
        except Exception as e:
            logger.info(f"Ayarlar okunamadı: {e}")

    def _save_settings(self):
        try:
            d = {'last_db': self.db_path, 'last_folder': self.hedef_klasor}
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.info(f"Ayarlar kaydedilemedi: {e}")


def main():
    app = QApplication(sys.argv)
    win = YaziIndirmeArayuz()
    win.show()
    sys.exit(app.exec())
