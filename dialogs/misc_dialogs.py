from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QScrollArea,
    QWidget,
    QFormLayout,
    QDialogButtonBox,
    QCheckBox,
    QLineEdit,
    QVBoxLayout,
)


class CokluProjeDialog(QDialog):
    def __init__(self, parent, projeler_dict):
        super().__init__(parent)
        self.setWindowTitle("Gelen Yazıya Proje İlişkilendir")
        self.projeler_dict = projeler_dict
        self.checkbox_list = []

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Lütfen gelen yazı ile ilişkilendirilecek projeleri seçin:")
        )
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        for kod, info in projeler_dict.items():
            isim = info.get('isim', '')
            uyar = info.get('uyari')
            label = f"{kod} - {isim}"
            cb = QCheckBox(label)
            if uyar:
                # Append a visual warning marker and set tooltip for full detail
                cb.setText(f"{label}  ⚠️")
                cb.setToolTip(uyar)
            cb.setChecked(True)
            self.checkbox_list.append((kod, cb))
            scroll_layout.addWidget(cb)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_secilen_projeler(self):
        return [kod for kod, cb in self.checkbox_list if cb.isChecked()]


class CokluAciklamaDialog(QDialog):
    def __init__(self, parent, proje_isimleri):
        super().__init__(parent)
        self.setWindowTitle("Revizyon Açıklamalarını Girin")
        self.setMinimumWidth(500)
        self.aciklama_entryleri = {}
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Lütfen her projenin ilk revizyonu (Rev-A) için bir açıklama girin:")
        )
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        form_layout = QFormLayout(scroll_widget)
        for isim in proje_isimleri:
            entry = QLineEdit()
            self.aciklama_entryleri[isim] = entry
            form_layout.addRow(f"{isim}:", entry)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_aciklamalar(self):
        return {
            isim: entry.text().strip()
            for isim, entry in self.aciklama_entryleri.items()
        }
