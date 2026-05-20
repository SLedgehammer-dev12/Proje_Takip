# PySide6 UI Pattern Skill

Bu skill, projede kullanılan PySide6 desenlerini tanımlar.

## Widget Pattern
```python
class CustomPanel(QWidget):
    my_signal = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        btn = QPushButton("İşlem")
        btn.clicked.connect(self._on_clicked)
        layout.addWidget(btn)

    def _on_clicked(self):
        self.my_signal.emit(data)
```

## i18n Pattern
```python
from i18n import tr, set_widget_text
# For dynamic text:
label.setText(tr("Metin"))
# For widget text that changes:
set_widget_text(button, "Buton")
```

## Signal-Slot Disconnect Pattern
```python
self._connections = [
    (signal, slot),
    ...
]
for sig, slot in self._connections:
    try:
        sig.disconnect(slot)
    except Exception:
        pass
```

## Theme Pattern
```python
from ui.styles import normalize_tok_variant, TOK_THEME_VARIANTS
current_variant = getattr(self.window(), "_tok_variant", "light")
theme_key = normalize_tok_variant(current_variant)
palette = TOK_THEME_VARIANTS[theme_key]["palette"]
text_color = palette.get("TEXT", "#0d1117")
```

## Lazy Import Pattern
```python
# In __init__ or method:
from heavy_module import HeavyClass  # Lazy, not at module top
```
