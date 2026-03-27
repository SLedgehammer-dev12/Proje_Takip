from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel
from models import Durum, ProjeModel, RevizyonModel


class DetailPanel(QWidget):
    """
    Panel for displaying detailed project information.

    Shows project code, name, type, hierarchy, latest incoming/outgoing letters,
    latest revision, approval status, and TSE status.
    """

    def __init__(self, parent=None):
        """Initialize the DetailPanel."""
        super().__init__(parent)
        self.detay_etiketleri = {}
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Proje Detayları")
        form_layout = QFormLayout()

        labels = [
            "Proje Kodu:",
            "Proje İsmi:",
            "Proje Türü:",
            "Hiyerarşi Yolu:",
            "En Son Gelen Yazı No:",
            "En Son Gelen Yazı Tarihi:",
            "En Son Giden Yazı No:",
            "En Son Giden Yazı Tarihi:",
            "En Son Revizyon Kodu:",
            "Onay Durumu:",
            "TSE Durumu:",
            "Liste Durumu:",
            "Listedeki Tür:",
        ]

        for label_text in labels:
            label = QLabel("-")
            form_layout.addRow(label_text, label)
            self.detay_etiketleri[label_text] = label

        group.setLayout(form_layout)
        layout.addWidget(group)
        layout.addStretch()

    def show_project_details(
        self, proje: ProjeModel, son_rev: RevizyonModel = None, hiyerarsi: str = "",
        excel_validation_info: dict = None
    ):
        if not proje:
            self.clear()
            return

        self.detay_etiketleri["Proje Kodu:"].setText(proje.proje_kodu)
        self.detay_etiketleri["Proje İsmi:"].setText(proje.proje_ismi)
        self.detay_etiketleri["Proje Türü:"].setText(proje.proje_turu or "-")
        self.detay_etiketleri["Hiyerarşi Yolu:"].setText(hiyerarsi)

        self.detay_etiketleri["En Son Gelen Yazı No:"].setText(
            proje.gelen_yazi_no or "-"
        )
        self.detay_etiketleri["En Son Gelen Yazı Tarihi:"].setText(
            proje.gelen_yazi_tarih or "-"
        )

        # Giden yazı bilgileri (onay veya red yazısından)
        if son_rev:
            giden_yazi_no = "-"
            giden_yazi_tarih = "-"

            if son_rev.durum in [Durum.ONAYLI.value, Durum.ONAYLI_NOTLU.value]:
                giden_yazi_no = son_rev.onay_yazi_no or "-"
                giden_yazi_tarih = son_rev.onay_yazi_tarih or "-"
            elif son_rev.durum == "Reddedildi":
                giden_yazi_no = son_rev.red_yazi_no or "-"
                giden_yazi_tarih = son_rev.red_yazi_tarih or "-"

            self.detay_etiketleri["En Son Giden Yazı No:"].setText(giden_yazi_no)
            self.detay_etiketleri["En Son Giden Yazı Tarihi:"].setText(giden_yazi_tarih)

            self.detay_etiketleri["En Son Revizyon Kodu:"].setText(
                son_rev.revizyon_kodu
            )
            self.detay_etiketleri["Onay Durumu:"].setText(son_rev.durum)
            tse_durum = "Gönderildi" if son_rev.tse_gonderildi else "Gönderilmedi"
            self.detay_etiketleri["TSE Durumu:"].setText(tse_durum)
        else:
            self.detay_etiketleri["En Son Giden Yazı No:"].setText("-")
            self.detay_etiketleri["En Son Giden Yazı Tarihi:"].setText("-")
            self.detay_etiketleri["En Son Revizyon Kodu:"].setText("-")
            self.detay_etiketleri["Onay Durumu:"].setText(proje.durum or "-")
            self.detay_etiketleri["TSE Durumu:"].setText("-")
        
        # Excel validation info
        if excel_validation_info:
            is_in_list = excel_validation_info.get('is_in_list', False)
            excel_type = excel_validation_info.get('project_type', '-')
            
            if is_in_list:
                liste_durumu = "✓ Bu proje listede var"
                # Apply green color for found projects
                self.detay_etiketleri["Liste Durumu:"].setStyleSheet("color: #2e7d32; font-weight: bold;")
            else:
                liste_durumu = "✗ Bu proje listede yok"
                # Apply gray color for not found projects
                self.detay_etiketleri["Liste Durumu:"].setStyleSheet("color: #757575;")
            
            self.detay_etiketleri["Liste Durumu:"].setText(liste_durumu)
            self.detay_etiketleri["Listedeki Tür:"].setText(excel_type)
        else:
            # No validation info available
            self.detay_etiketleri["Liste Durumu:"].setText("-")
            self.detay_etiketleri["Liste Durumu:"].setStyleSheet("")
            self.detay_etiketleri["Listedeki Tür:"].setText("-")

    def clear(self):
        for label in self.detay_etiketleri.values():
            label.setText("-")
