import os
import logging
from typing import Optional, List, Tuple, Dict

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QDialogButtonBox,
    QComboBox,
    QCheckBox,
    QWidget,
    QMessageBox,
    QGroupBox,
)

from models import Durum
from utils import dosyadan_tarih_sayi_cikar


class YeniRevizyonDialog(QDialog):
    def __init__(
        self,
        parent,
        rev_kodu,
        mevcut_yazilar=None,
        on_veri=None,
        yazi_turu=None,
        initial_dosya_yolu: str = None,
    ):
        super().__init__(parent)
        self.mevcut_yazilar = mevcut_yazilar or {}
        self.on_veri = on_veri or {}
        self.yazi_turu = yazi_turu
        self.yeni_rev_dosya_yolu = None
        self.yeni_yazi_dosya_yolu = None
        self.yeni_onay_dosya_yolu = None
        self.yeni_red_dosya_yolu = None
        self.dosya_yolu = None

        if "id" in self.on_veri:
            durum_str = (
                f" ({self.on_veri.get('durum', '')})"
                if self.on_veri.get("durum")
                else ""
            )
            tur_str = (
                " (Gelen)"
                if self.yazi_turu == "gelen"
                else " (Giden)"
                if self.yazi_turu == "giden"
                else ""
            )
            self.setWindowTitle(f"Rev-{rev_kodu} Düzenle{durum_str}{tur_str}")
        else:
            self.setWindowTitle(f"Yeni Revizyon Yükle (Rev-{rev_kodu})")

        self.initial_dosya_yolu = initial_dosya_yolu
        # store the provided rev code for use in setup_ui
        self.rev_kodu = rev_kodu
        self.setup_ui()

    def _normalize_mevcut_yazilar(self) -> List[Tuple[str, str, str]]:
        kayitlar: List[Tuple[str, str, str]] = []
        seen = set()
        if isinstance(self.mevcut_yazilar, dict):
            iterable = self.mevcut_yazilar.items()
        else:
            iterable = self.mevcut_yazilar or []

        for entry in iterable:
            if isinstance(entry, tuple) and len(entry) >= 2:
                yazi_no, tarih = entry[0], entry[1]
            else:
                yazi_no, tarih = entry, ""
            yazi_no = (yazi_no or "").strip()
            tarih = (tarih or "").strip()
            if not yazi_no:
                continue
            display = f"{yazi_no} | {tarih}" if tarih else yazi_no
            if (yazi_no, tarih) in seen:
                continue
            seen.add((yazi_no, tarih))
            kayitlar.append((display, yazi_no, tarih))
        return kayitlar

    def setup_ui(self):
        layout = QFormLayout(self)
        is_editing = "id" in self.on_veri
        show_gelen = True
        if is_editing and self.yazi_turu == "giden":
            show_gelen = False
        rev_dosya_layout = QHBoxLayout()
        self.rev_dosya_etiketi = QLabel(
            "Yeni revizyon dokümanı seçin (opsiyonel)..."
            if is_editing
            else "Revizyon dokümanını seçin..."
        )
        btn_rev_gozat = QPushButton("Gözat...")
        btn_rev_gozat.clicked.connect(self.rev_dosya_sec)
        rev_dosya_layout.addWidget(self.rev_dosya_etiketi)
        rev_dosya_layout.addWidget(btn_rev_gozat)
        layout.addRow("Revizyon Dosyası:", rev_dosya_layout)
        # Revizyon kodu entry (merge RevizyonSecDialog functionality)
        self.rev_kodu_entry = QLineEdit(self.rev_kodu)
        layout.addRow("Revizyon Kodu:", self.rev_kodu_entry)
        self.aciklama_entry = QLineEdit(self.on_veri.get("aciklama", ""))
        layout.addRow("Açıklama:", self.aciklama_entry)
        if is_editing:
            tse_layout = QVBoxLayout()
            tse_layout.setContentsMargins(0, 0, 0, 0)
            self.tse_checkbox = QCheckBox("TSE'ye Gönderildi")
            self.tse_checkbox.setChecked(bool(self.on_veri.get("tse_gonderildi", 0)))
            self.tse_form_widget = QWidget()
            tse_form_layout = QFormLayout(self.tse_form_widget)
            tse_form_layout.setContentsMargins(10, 0, 0, 0)
            self.tse_yazi_no_entry = QLineEdit(self.on_veri.get("tse_yazi_no", ""))
            self.tse_yazi_tarih_entry = QLineEdit(
                self.on_veri.get("tse_yazi_tarih", "")
            )
            tse_form_layout.addRow("TSE Yazı No:", self.tse_yazi_no_entry)
            tse_form_layout.addRow("TSE Yazı Tarihi:", self.tse_yazi_tarih_entry)
            tse_layout.addWidget(self.tse_checkbox)
            tse_layout.addWidget(self.tse_form_widget)
            layout.addRow(tse_layout)
            self.tse_checkbox.toggled.connect(self.tse_form_widget.setVisible)
            self.tse_form_widget.setVisible(self.tse_checkbox.isChecked())
        else:
            self.tse_checkbox = None
            self.tse_yazi_no_entry = None
            self.tse_yazi_tarih_entry = None
        self._mevcut_yazi_kayitlari = self._normalize_mevcut_yazilar()
        self._mevcut_yazi_map: Dict[str, Tuple[str, str]] = {
            display: (yazi_no, tarih)
            for display, yazi_no, tarih in self._mevcut_yazi_kayitlari
        }
        self.yazi_no_combo = QComboBox()
        self.yazi_no_combo.setEditable(True)
        self.yazi_no_combo.addItems([""] + [row[0] for row in self._mevcut_yazi_kayitlari])
        self.yazi_no_combo.setCurrentText(self.on_veri.get("gelen_yazi_no", ""))
        self.yazi_no_combo.currentIndexChanged.connect(self.yazi_secilince)
        self.tarih_entry = QLineEdit(self.on_veri.get("gelen_yazi_tarih", ""))
        yazi_dosya_layout = QHBoxLayout()
        self.yazi_dosya_etiketi = QLabel("Yeni gelen yazı seç (opsiyonel)...")
        btn_yazi_gozat = QPushButton("Gözat...")
        btn_yazi_gozat.clicked.connect(self.yazi_dosya_sec)
        yazi_dosya_layout.addWidget(self.yazi_dosya_etiketi)
        yazi_dosya_layout.addWidget(btn_yazi_gozat)
        self.lbl_gelen_no = QLabel("İlişkili Gelen Yazı No:")
        self.lbl_gelen_tarih = QLabel("Gelen Yazı Tarihi:")
        self.lbl_gelen_dosya = QLabel("Gelen Yazı Dosyası:")
        self.widget_gelen_dosya = QWidget()
        self.widget_gelen_dosya.setLayout(yazi_dosya_layout)
        layout.addRow(self.lbl_gelen_no, self.yazi_no_combo)
        layout.addRow(self.lbl_gelen_tarih, self.tarih_entry)
        layout.addRow(self.lbl_gelen_dosya, self.widget_gelen_dosya)
        self.onay_yazi_no_entry = QLineEdit(self.on_veri.get("onay_yazi_no", ""))
        self.onay_yazi_tarih_entry = QLineEdit(self.on_veri.get("onay_yazi_tarih", ""))
        self.onay_dosya_layout_widget = QWidget()
        onay_dosya_layout = QHBoxLayout(self.onay_dosya_layout_widget)
        onay_dosya_layout.setContentsMargins(0, 0, 0, 0)
        self.onay_dosya_etiketi = QLabel("Yeni onay yazısı seç (opsiyonel)...")
        btn_onay_gozat = QPushButton("Gözat...")
        btn_onay_gozat.clicked.connect(self.onay_dosya_sec)
        onay_dosya_layout.addWidget(self.onay_dosya_etiketi)
        onay_dosya_layout.addWidget(btn_onay_gozat)
        layout.addRow(QLabel("Onay Yazı No:"), self.onay_yazi_no_entry)
        layout.addRow(QLabel("Onay Yazı Tarihi:"), self.onay_yazi_tarih_entry)
        layout.addRow(QLabel("Onay Yazı Dosyası:"), self.onay_dosya_layout_widget)
        self.red_yazi_no_entry = QLineEdit(self.on_veri.get("red_yazi_no", ""))
        self.red_yazi_tarih_entry = QLineEdit(self.on_veri.get("red_yazi_tarih", ""))
        self.red_dosya_layout_widget = QWidget()
        red_dosya_layout = QHBoxLayout(self.red_dosya_layout_widget)
        red_dosya_layout.setContentsMargins(0, 0, 0, 0)
        self.red_dosya_etiketi = QLabel("Yeni red yazısı seç (opsiyonel)...")
        btn_red_gozat = QPushButton("Gözat...")
        btn_red_gozat.clicked.connect(self.red_dosya_sec)
        red_dosya_layout.addWidget(self.red_dosya_etiketi)
        red_dosya_layout.addWidget(btn_red_gozat)
        layout.addRow(QLabel("Red Yazı No:"), self.red_yazi_no_entry)
        layout.addRow(QLabel("Red Yazı Tarihi:"), self.red_yazi_tarih_entry)
        layout.addRow(QLabel("Red Yazı Dosyası:"), self.red_dosya_layout_widget)
        self.lbl_gelen_no.setVisible(show_gelen)
        self.yazi_no_combo.setVisible(show_gelen)
        self.lbl_gelen_tarih.setVisible(show_gelen)
        self.tarih_entry.setVisible(show_gelen)
        self.lbl_gelen_dosya.setVisible(show_gelen)
        self.widget_gelen_dosya.setVisible(show_gelen)
        show_onay = (
            is_editing
            and self.yazi_turu == "giden"
            and self.on_veri.get("durum")
            in [Durum.ONAYLI.value, Durum.ONAYLI_NOTLU.value]
        )
        show_red = (
            is_editing
            and self.yazi_turu == "giden"
            and self.on_veri.get("durum") == Durum.REDDEDILDI.value
        )
        self.onay_yazi_no_entry.setVisible(show_onay)
        self.onay_yazi_tarih_entry.setVisible(show_onay)
        self.onay_dosya_layout_widget.setVisible(show_onay)
        self.red_yazi_no_entry.setVisible(show_red)
        self.red_yazi_tarih_entry.setVisible(show_red)
        self.red_dosya_layout_widget.setVisible(show_red)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        # Button signal connections were previously made when creating each button; avoid re-connecting here
        self.yazi_no_combo.currentTextChanged.connect(self.yazi_secilince)
        # Add the ok/cancel buttons to the dialog layout so they're visible in GUI
        layout.addRow(buttons)
        try:
            ok_btn = buttons.button(QDialogButtonBox.Ok)
            if ok_btn:
                ok_btn.setDefault(True)
        except Exception:
            pass
        # If we have an initial file path passed, set it and avoid re-opening
        if self.initial_dosya_yolu:
            self.dosya_yolu = self.initial_dosya_yolu
            self.rev_dosya_etiketi.setText(os.path.basename(self.initial_dosya_yolu))

    def rev_dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self,
            "Revizyon Dokümanı Seç",
            "",
            "Tüm Dosyalar (*.pdf *.jpg *.jpeg *.png);;PDF Dosyaları (*.pdf);;Resim Dosyaları (*.jpg *.jpeg *.png)",
        )
        if yol:
            if "id" in self.on_veri:
                self.yeni_rev_dosya_yolu = yol
            else:
                self.dosya_yolu = yol
            self.rev_dosya_etiketi.setText(os.path.basename(yol))
            try:
                logger = logging.getLogger(__name__)
                logger.info(f"Revizyon dokümanı seçildi: {yol}")
            except Exception:
                pass

    def yazi_dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self,
            "Gelen Yazı Dokümanı Seç",
            "",
            "Tüm Dosyalar (*.pdf *.jpg *.jpeg *.png);;PDF Dosyaları (*.pdf);;Resim Dosyaları (*.jpg *.jpeg *.png)",
        )
        if yol:
            self.yeni_yazi_dosya_yolu = yol
            self.yazi_dosya_etiketi.setText(os.path.basename(yol))
            try:
                logger = logging.getLogger(__name__)
                logger.info(f"Yeni gelen yazı dosyası seçildi: {yol}")
            except Exception:
                pass
            if bilgiler := dosyadan_tarih_sayi_cikar(os.path.basename(yol)):
                self.yazi_no_combo.setCurrentText(bilgiler["sayi"])
                self.tarih_entry.setText(bilgiler["tarih"])

    def onay_dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self,
            "Onay Yazı Dokümanı Seç",
            "",
            "Tüm Dosyalar (*.pdf *.jpg *.jpeg *.png);;PDF Dosyaları (*.pdf);;Resim Dosyaları (*.jpg *.jpeg *.png)",
        )
        if yol:
            self.yeni_onay_dosya_yolu = yol
            self.onay_dosya_etiketi.setText(os.path.basename(yol))
            try:
                logger = logging.getLogger(__name__)
                logger.info(f"Yeni onay yazısı dosyası seçildi: {yol}")
            except Exception:
                pass
            if bilgiler := dosyadan_tarih_sayi_cikar(os.path.basename(yol)):
                self.onay_yazi_no_entry.setText(bilgiler["sayi"])
                self.onay_yazi_tarih_entry.setText(bilgiler["tarih"])

    def red_dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self,
            "Red Yazı Dokümanı Seç",
            "",
            "Tüm Dosyalar (*.pdf *.jpg *.jpeg *.png);;PDF Dosyaları (*.pdf);;Resim Dosyaları (*.jpg *.jpeg *.png)",
        )
        if yol:
            self.yeni_red_dosya_yolu = yol
            self.red_dosya_etiketi.setText(os.path.basename(yol))
            try:
                logger = logging.getLogger(__name__)
                logger.info(f"Yeni red yazısı dosyası seçildi: {yol}")
            except Exception:
                pass
            if bilgiler := dosyadan_tarih_sayi_cikar(os.path.basename(yol)):
                self.red_yazi_no_entry.setText(bilgiler["sayi"])
                self.red_yazi_tarih_entry.setText(bilgiler["tarih"])

    def yazi_secilince(self, text):
        selected = self._mevcut_yazi_map.get(text)
        if selected:
            yazi_no, tarih = selected
            if self.yazi_no_combo.currentText() != yazi_no:
                self.yazi_no_combo.setEditText(yazi_no)
            self.tarih_entry.setText(tarih)
            self.yeni_yazi_dosya_yolu = None
            self.yazi_dosya_etiketi.setText("Yeni gelen yazı seç (opsiyonel)...")
            try:
                logger = logging.getLogger(__name__)
                logger.info(f"Mevcut gelen yazı seçildi: {yazi_no} / {tarih}")
            except Exception:
                pass
            return
        same_number_dates = {
            tarih for _, yazi_no, tarih in self._mevcut_yazi_kayitlari if yazi_no == text
        }
        if len(same_number_dates) == 1:
            self.tarih_entry.setText(next(iter(same_number_dates)))

    def accept(self):
        if "id" not in self.on_veri and not self.dosya_yolu:
            return QMessageBox.warning(
                self, "Eksik Bilgi", "Yeni revizyon için doküman seçmek zorunludur."
            )
        # Revizyon kodu zorunlu
        if not self.rev_kodu_entry.text().strip():
            QMessageBox.warning(self, "Eksik Bilgi", "Revizyon Kodu boş bırakılamaz.")
            self.rev_kodu_entry.setFocus()
            return
        super().accept()
        try:
            logger = logging.getLogger(__name__)
            logger.info(f"OnayRedDialog accepted: {self.get_data()}")
        except Exception:
            pass
        try:
            logger = logging.getLogger(__name__)
            logger.info(f"YeniRevizyonDialog accepted: {self.get_data()}")
        except Exception:
            pass

    def get_data(self):
        tse_gonderildi = 0
        tse_yazi_no = None
        tse_yazi_tarih = None
        if self.tse_checkbox is not None:
            tse_gonderildi = 1 if self.tse_checkbox.isChecked() else 0
            if tse_gonderildi == 1:
                tse_yazi_no = self.tse_yazi_no_entry.text().strip() or None
                tse_yazi_tarih = self.tse_yazi_tarih_entry.text().strip() or None
        return {
            "revizyon_kodu": self.rev_kodu_entry.text().strip(),
            "aciklama": self.aciklama_entry.text().strip(),
            "dosya_yolu": self.dosya_yolu,
            "yeni_rev_dosya_yolu": self.yeni_rev_dosya_yolu,
            "gelen_yazi_no": self.yazi_no_combo.currentText().split("|", 1)[0].strip() or None,
            "gelen_yazi_tarih": self.tarih_entry.text().strip() or None,
            "yeni_yazi_dosya_yolu": self.yeni_yazi_dosya_yolu,
            "onay_yazi_no": self.onay_yazi_no_entry.text().strip() or None,
            "onay_yazi_tarih": self.onay_yazi_tarih_entry.text().strip() or None,
            "red_yazi_no": self.red_yazi_no_entry.text().strip() or None,
            "red_yazi_tarih": self.red_yazi_tarih_entry.text().strip() or None,
            "yeni_onay_dosya_yolu": self.yeni_onay_dosya_yolu,
            "yeni_red_dosya_yolu": self.yeni_red_dosya_yolu,
            "tse_gonderildi": tse_gonderildi,
            "tse_yazi_no": tse_yazi_no,
            "tse_yazi_tarih": tse_yazi_tarih,
        }


class OnayRedDialog(QDialog):
    def __init__(
        self, parent, islem_turu, mevcut_yazilar=None, title: Optional[str] = None
    ):
        super().__init__(parent)
        dialog_title = title if title else f"Revizyon {islem_turu}lama"
        self.setWindowTitle(dialog_title)
        self.mevcut_yazilar = mevcut_yazilar or {}
        self.dosya_yolu = None
        self._mevcut_yazi_kayitlari = self._normalize_mevcut_yazilar()
        self._mevcut_yazi_map: Dict[str, Tuple[str, str]] = {
            display: (yazi_no, tarih)
            for display, yazi_no, tarih in self._mevcut_yazi_kayitlari
        }
        layout = QFormLayout(self)
        self.yazi_no_combo = QComboBox()
        self.yazi_no_combo.setEditable(True)
        self.yazi_no_combo.addItems([""] + [row[0] for row in self._mevcut_yazi_kayitlari])
        self.tarih_entry = QLineEdit()
        layout.addRow(f"{islem_turu} Yazı No:", self.yazi_no_combo)
        layout.addRow(f"{islem_turu} Yazı Tarihi:", self.tarih_entry)
        dosya_layout = QHBoxLayout()
        self.dosya_etiketi = QLabel("Yeni yazı dokümanı seç (opsiyonel)...")
        btn_gozat = QPushButton("Gözat...")
        btn_gozat.clicked.connect(self.dosya_sec)
        dosya_layout.addWidget(self.dosya_etiketi)
        dosya_layout.addWidget(btn_gozat)
        layout.addRow("Yazı Dokümanı:", dosya_layout)
        self.yazi_no_combo.currentTextChanged.connect(self.yazi_secilince)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _normalize_mevcut_yazilar(self) -> List[Tuple[str, str, str]]:
        kayitlar: List[Tuple[str, str, str]] = []
        seen = set()
        if isinstance(self.mevcut_yazilar, dict):
            iterable = self.mevcut_yazilar.items()
        else:
            iterable = self.mevcut_yazilar or []
        for entry in iterable:
            if isinstance(entry, tuple) and len(entry) >= 2:
                yazi_no, tarih = entry[0], entry[1]
            else:
                yazi_no, tarih = entry, ""
            yazi_no = (yazi_no or "").strip()
            tarih = (tarih or "").strip()
            if not yazi_no:
                continue
            display = f"{yazi_no} | {tarih}" if tarih else yazi_no
            if (yazi_no, tarih) in seen:
                continue
            seen.add((yazi_no, tarih))
            kayitlar.append((display, yazi_no, tarih))
        return kayitlar

    def dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self,
            "Yazı Dokümanı Seç",
            "",
            "Tüm Dosyalar (*.pdf *.jpg *.jpeg *.png);;PDF Dosyaları (*.pdf);;Resim Dosyaları (*.jpg *.jpeg *.png)",
        )
        if yol:
            self.dosya_yolu = yol
            self.dosya_etiketi.setText(os.path.basename(yol))
            if bilgiler := dosyadan_tarih_sayi_cikar(os.path.basename(yol)):
                self.yazi_no_combo.setCurrentText(bilgiler["sayi"])
                self.tarih_entry.setText(bilgiler["tarih"])

    def yazi_secilince(self, text):
        selected = self._mevcut_yazi_map.get(text)
        if selected:
            yazi_no, tarih = selected
            if self.yazi_no_combo.currentText() != yazi_no:
                self.yazi_no_combo.setEditText(yazi_no)
            self.tarih_entry.setText(tarih)
            self.dosya_yolu = None
            self.dosya_etiketi.setText("Yeni yazı dokümanı seç (opsiyonel)...")
            return
        same_number_dates = {
            tarih for _, yazi_no, tarih in self._mevcut_yazi_kayitlari if yazi_no == text
        }
        if len(same_number_dates) == 1:
            self.tarih_entry.setText(next(iter(same_number_dates)))

    def get_data(self):
        return {
            "yazi_no": self.yazi_no_combo.currentText().split("|", 1)[0].strip(),
            "tarih": self.tarih_entry.text().strip(),
            "dosya_yolu": self.dosya_yolu,
        }

    def accept(self):
        if (
            not self.yazi_no_combo.currentText().strip()
            or not self.tarih_entry.text().strip()
        ):
            QMessageBox.warning(
                self, "Eksik Bilgi", "Yazı No ve Tarih alanları zorunludur."
            )
            return
        super().accept()


class RevizyonSecDialog(QDialog):
    def __init__(
        self,
        parent,
        proje_kodu: str,
        mevcut_revizyonlar: list,
        onerilen_rev: str = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"{proje_kodu} - Yeni Revizyon")
        self.mevcut_revizyonlar = mevcut_revizyonlar
        layout = QFormLayout(self)
        if mevcut_revizyonlar:
            mevcut_label = QLabel(
                f"Mevcut revizyonlar: {', '.join(mevcut_revizyonlar)}"
            )
            layout.addRow(mevcut_label)
        self.rev_combo = QComboBox()
        self.rev_combo.setEditable(True)
        if onerilen_rev:
            self.rev_combo.addItem(f"✨ {onerilen_rev} (Önerilen)")
            self.rev_combo.setCurrentIndex(0)
        self.rev_combo.addItem("Manuel gir...")
        layout.addRow("Revizyon Kodu:", self.rev_combo)
        self.aciklama_entry = QLineEdit()
        layout.addRow("Açıklama (opsiyonel):", self.aciklama_entry)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_revizyon_bilgisi(self) -> dict:
        secim = self.rev_combo.currentText()
        if secim.startswith("✨"):
            secim = secim.split()[1]
        return {"revizyon_kodu": secim, "aciklama": self.aciklama_entry.text().strip()}

    def accept(self):
        secim = self.rev_combo.currentText()
        if secim.startswith("✨"):
            secim = secim.split()[1]
        if not secim or secim == "Manuel gir...":
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir revizyon kodu girin.")
            return
        if secim in self.mevcut_revizyonlar:
            yanit = QMessageBox.question(
                self,
                "Revizyon Zaten Mevcut",
                f"Revizyon '{secim}' bu projede zaten mevcut.\n\nAynı revizyon koduna yeni bir belge (örn. giden yazı) eklemek istiyorsanız 'Evet'e basın.\nFarklı bir revizyon kodu seçmek için 'Hayır'a basın.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if yanit == QMessageBox.No:
                return
        super().accept()


class DurumDegistirDialog(QDialog):
    def __init__(self, parent, mevcut_durum: str, mevcut_kod: str):
        super().__init__(parent)
        self.setWindowTitle("Revizyon Durumunu Düzelt")
        layout = QFormLayout(self)
        self.durum_combo = QComboBox()
        for durum in Durum:
            self.durum_combo.addItem(durum.value)
        self.durum_combo.setCurrentText(mevcut_durum)
        self.kod_entry = QLineEdit(mevcut_kod)
        self.kod_entry.setToolTip("Gerekirse revizyon kodunu da değiştirebilirsiniz.")
        layout.addRow("<b>Yeni Durum:</b>", self.durum_combo)
        layout.addRow("<b>Yeni Revizyon Kodu:</b>", self.kod_entry)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            "yeni_durum": self.durum_combo.currentText(),
            "yeni_kod": self.kod_entry.text().strip(),
        }

    def accept(self):
        if not self.kod_entry.text().strip():
            QMessageBox.warning(self, "Eksik Bilgi", "Revizyon Kodu boş bırakılamaz.")
            return
        super().accept()


class YaziTuruSecDialog(QDialog):
    def __init__(self, parent, dosya_adi: str):
        super().__init__(parent)
        self.setWindowTitle(f"Yazı Türü Seç - {dosya_adi}")
        self.setMinimumWidth(550)
        layout = QVBoxLayout(self)
        bilgi_label = QLabel(
            f"<b>Dosya:</b> {dosya_adi}<br><br>Bu dosya hangi tür bir yazı ile ilişkili?"
        )
        bilgi_label.setWordWrap(True)
        layout.addWidget(bilgi_label)
        tur_group = QGroupBox("Yazı Türü")
        tur_layout = QVBoxLayout(tur_group)
        from PySide6.QtWidgets import QRadioButton

        self.gelen_radio = QRadioButton("📥 Gelen Yazı")
        self.giden_radio = QRadioButton("📤 Giden Yazı (Onay)")
        self.yok_radio = QRadioButton("📄 Yazı Yok (Manuel)")
        self.gelen_radio.setChecked(True)
        tur_layout.addWidget(self.gelen_radio)
        tur_layout.addWidget(self.giden_radio)
        tur_layout.addWidget(self.yok_radio)
        layout.addWidget(tur_group)
        self.gelen_group = QGroupBox("Gelen Yazı Bilgileri")
        gelen_layout = QFormLayout(self.gelen_group)
        self.gelen_yazi_no_entry = QLineEdit()
        self.gelen_yazi_tarih_entry = QLineEdit()
        gelen_layout.addRow("Yazı No:", self.gelen_yazi_no_entry)
        gelen_layout.addRow("Yazı Tarihi:", self.gelen_yazi_tarih_entry)
        # Add file browse for Gelen Yazı
        gelen_dosya_layout = QHBoxLayout()
        self.gelen_dosya_etiket = QLabel("Gelen yazı dokümanı seç (opsiyonel)...")
        btn_gelen_gozat = QPushButton("Gözat...")
        btn_gelen_gozat.clicked.connect(self.gelen_dosya_sec)
        gelen_dosya_layout.addWidget(self.gelen_dosya_etiket)
        gelen_dosya_layout.addWidget(btn_gelen_gozat)
        gelen_layout.addRow("Gelen Yazı Dosyası:", gelen_dosya_layout)
        layout.addWidget(self.gelen_group)
        self.giden_group = QGroupBox("Giden Yazı Bilgileri")
        giden_layout = QFormLayout(self.giden_group)
        self.durum_combo = QComboBox()
        self.durum_combo.addItems(["Onaylı", "Notlu Onaylı", "Reddedildi"])
        giden_layout.addRow("Onay Durumu:", self.durum_combo)
        self.giden_yazi_no_entry = QLineEdit()
        giden_layout.addRow("Yazı No:", self.giden_yazi_no_entry)
        self.giden_yazi_tarih_entry = QLineEdit()
        giden_layout.addRow("Yazı Tarihi:", self.giden_yazi_tarih_entry)
        self.aciklama_entry = QLineEdit()
        giden_layout.addRow("Açıklama:", self.aciklama_entry)
        # Add file browse for Giden Yazı
        giden_dosya_layout = QHBoxLayout()
        self.giden_dosya_etiket = QLabel("Giden yazı dokümanı seç (opsiyonel)...")
        btn_giden_gozat = QPushButton("Gözat...")
        btn_giden_gozat.clicked.connect(self.giden_dosya_sec)
        giden_dosya_layout.addWidget(self.giden_dosya_etiket)
        giden_dosya_layout.addWidget(btn_giden_gozat)
        giden_layout.addRow("Giden Yazı Dosyası:", giden_dosya_layout)
        layout.addWidget(self.giden_group)
        self.giden_group.setVisible(False)
        self.gelen_radio.toggled.connect(self._yazi_turu_degisti)
        self.giden_radio.toggled.connect(self._yazi_turu_degisti)
        self.yok_radio.toggled.connect(self._yazi_turu_degisti)
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _yazi_turu_degisti(self):
        if self.gelen_radio.isChecked():
            self.gelen_group.setVisible(True)
            self.giden_group.setVisible(False)
        elif self.giden_radio.isChecked():
            self.gelen_group.setVisible(False)
            self.giden_group.setVisible(True)
        else:
            self.gelen_group.setVisible(False)
            self.giden_group.setVisible(False)

    def get_yazi_bilgisi(self) -> dict:
        if self.gelen_radio.isChecked():
            return {
                "yazi_turu": "gelen",
                "gelen_yazi_no": self.gelen_yazi_no_entry.text().strip(),
                "gelen_yazi_tarih": self.gelen_yazi_tarih_entry.text().strip(),
                "durum": None,
                "aciklama": "",
            }
        elif self.giden_radio.isChecked():
            durum_text = self.durum_combo.currentText()
            if durum_text == "Onaylı":
                durum = "Onayli"
            elif durum_text == "Notlu Onaylı":
                durum = "Notlu Onayli"
            else:
                durum = "Reddedildi"
            return {
                "yazi_turu": "giden",
                "giden_yazi_no": self.giden_yazi_no_entry.text().strip(),
                "giden_yazi_tarih": self.giden_yazi_tarih_entry.text().strip(),
                "durum": durum,
                "aciklama": self.aciklama_entry.text().strip(),
            }
        else:
            return {
                "yazi_turu": "yok",
                "durum": None,
                "aciklama": "Manuel proje oluşturuldu",
            }

    def accept(self):
        if self.gelen_radio.isChecked():
            if not self.gelen_yazi_no_entry.text().strip():
                QMessageBox.warning(
                    self, "Eksik Bilgi", "Gelen yazı numarası boş bırakılamaz."
                )
                self.gelen_yazi_no_entry.setFocus()
                return
            if not self.gelen_yazi_tarih_entry.text().strip():
                QMessageBox.warning(
                    self, "Eksik Bilgi", "Gelen yazı tarihi boş bırakılamaz."
                )
                self.gelen_yazi_tarih_entry.setFocus()
                return
        elif self.giden_radio.isChecked():
            if not self.giden_yazi_no_entry.text().strip():
                QMessageBox.warning(
                    self, "Eksik Bilgi", "Giden yazı numarası boş bırakılamaz."
                )
                self.giden_yazi_no_entry.setFocus()
                return
            if not self.giden_yazi_tarih_entry.text().strip():
                QMessageBox.warning(
                    self, "Eksik Bilgi", "Giden yazı tarihi boş bırakılamaz."
                )
                self.giden_yazi_tarih_entry.setFocus()
                return
        super().accept()

    def gelen_dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self,
            "Gelen Yazı Dokümanı Seç",
            "",
            "Tüm Dosyalar (*.pdf *.jpg *.jpeg *.png);;PDF Dosyaları (*.pdf);;Resim Dosyaları (*.jpg *.jpeg *.png)",
        )
        if not yol:
            return
        self.gelen_dosya_etiket.setText(os.path.basename(yol))
        try:
            logger = logging.getLogger(__name__)
            logger.info(f"YaziTuruSec - gelen dosya seçildi: {yol}")
        except Exception:
            pass
        # Try to parse from filename first
        if bilgiler := dosyadan_tarih_sayi_cikar(os.path.basename(yol)):
            self.gelen_yazi_no_entry.setText(bilgiler["sayi"])
            self.gelen_yazi_tarih_entry.setText(bilgiler["tarih"])
            return
        # If file is a PDF, try to extract textual content and find the pattern
        if yol.lower().endswith(".pdf"):
            try:
                import fitz

                doc = fitz.open(yol)
                # read the first couple pages to increase chance of finding info
                text = ""
                for i in range(min(3, doc.page_count)):
                    page = doc.load_page(i)
                    text += page.get_text()
                doc.close()
                # use the same regex pattern as utils
                import re

                # Some PDFs may have encoding / glyph differences (e.g., dotted characters for 'ı').
                # Match date + 'tarih ve' + a following number regardless of the trailing "sayılı" wording.
                match = re.search(r"(\d{2}\.\d{2}\.\d{4})\s*tarih\s*ve\s*([0-9]{1,6})\b", text, re.IGNORECASE)
                if match:
                    self.gelen_yazi_tarih_entry.setText(match.group(1))
                    self.gelen_yazi_no_entry.setText(match.group(2))
            except Exception:
                # ignore failures
                pass

    def giden_dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self,
            "Giden Yazı Dokümanı Seç",
            "",
            "Tüm Dosyalar (*.pdf *.jpg *.jpeg *.png);;PDF Dosyaları (*.pdf);;Resim Dosyaları (*.jpg *.jpeg *.png)",
        )
        if not yol:
            return
        self.giden_dosya_etiket.setText(os.path.basename(yol))
        if bilgiler := dosyadan_tarih_sayi_cikar(os.path.basename(yol)):
            self.giden_yazi_no_entry.setText(bilgiler["sayi"])
            self.giden_yazi_tarih_entry.setText(bilgiler["tarih"])
            return
        if yol.lower().endswith(".pdf"):
            try:
                import fitz

                doc = fitz.open(yol)
                text = ""
                for i in range(min(3, doc.page_count)):
                    page = doc.load_page(i)
                    text += page.get_text()
                doc.close()
                import re

                match = re.search(r"(\d{2}\.\d{2}\.\d{4})\s*tarih\s*ve\s*([0-9]{1,6})\b", text, re.IGNORECASE)
                if match:
                    self.giden_yazi_tarih_entry.setText(match.group(1))
                    self.giden_yazi_no_entry.setText(match.group(2))
            except Exception:
                pass
