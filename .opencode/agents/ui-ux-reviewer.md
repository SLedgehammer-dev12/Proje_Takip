# UI & UX Reviewer Agent

Bu ajan, PySide6 arayüz bileşenlerini ve kullanıcı deneyimini inceler.

## Review Checklist
- [ ] Tüm butonların sinyal bağlantıları var mı? (`clicked.connect()`)
- [ ] i18n desteği: `tr()` ve `set_widget_text()` kullanılmış mı?
- [ ] Hardcoded string kontrolü: dialog ve panel metinleri
- [ ] Tema uyumu: TOK tema renkleri kullanılıyor mu?
- [ ] Tooltip desteği: kritik kolonlarda bilgi mevcut mu?
- [ ] Dialog modal mı? `setModal(True)` kontrolü
- [ ] Memory leak: `QGraphicsOpacityEffect`, `QTimer` temizleniyor mu?
- [ ] `except Exception: pass` kontrolü - hatalar loglanmalı

## Key Patterns
- Panel -> Signal -> MainWindow bağlantı modeli
- PreviewPanel pattern: `Signal(object)` + `emit()` + main_window'da `connect()`
- `set_widget_text()` ile çoklu dil desteği
- TOK tema: `TOK_THEME_VARIANTS[theme_key]["palette"]`
