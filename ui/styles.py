from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor, QFont


TOK_THEME_ORDER = ["light", "dark", "sand", "forest", "steel"]
TOK_THEME_VARIANTS = {
    "light": {
        "label": "Kurumsal Acik",
        "icon": "weather-clear",
        "palette": {
            "PRIMARY": "#5b9cf5",
            "PRIMARY_DARK": "#4a8ad6",
            "ACCENT": "#5dba9f",
            "TEXT": "#0d1117",
            "BG_LIGHT": "#f5f7fa",
            "SURFACE": "#ffffff",
            "MUTED": "#5a6575",
            "BORDER": "#d4dce6",
            "HOVER": "#6ba5f7",
        },
    },
    "dark": {
        "label": "Gece Mavisi",
        "icon": "weather-night",
        "palette": {
            "PRIMARY": "#5b9cf5",
            "PRIMARY_DARK": "#4a8ad6",
            "ACCENT": "#6fcdb8",
            "TEXT": "#f0f3f7",
            "BG_LIGHT": "#1a1f2e",
            "SURFACE": "#232936",
            "MUTED": "#a8b2bf",
            "BORDER": "#3a4555",
            "HOVER": "#6ba5f7",
        },
    },
    "sand": {
        "label": "Gundogumu",
        "icon": "weather-few-clouds",
        "palette": {
            "PRIMARY": "#c56a2d",
            "PRIMARY_DARK": "#a5521c",
            "ACCENT": "#3a8877",
            "TEXT": "#34261b",
            "BG_LIGHT": "#f8f1e8",
            "SURFACE": "#fffaf4",
            "MUTED": "#6d5a4a",
            "BORDER": "#e4d3c2",
            "HOVER": "#d98142",
        },
    },
    "forest": {
        "label": "Cam Yesili",
        "icon": "applications-graphics",
        "palette": {
            "PRIMARY": "#2f7d5b",
            "PRIMARY_DARK": "#246247",
            "ACCENT": "#c88a3d",
            "TEXT": "#12241c",
            "BG_LIGHT": "#eef5f1",
            "SURFACE": "#fbfdfb",
            "MUTED": "#54685d",
            "BORDER": "#d5e2db",
            "HOVER": "#3d9270",
        },
    },
    "steel": {
        "label": "Celik Gri",
        "icon": "preferences-desktop-theme",
        "palette": {
            "PRIMARY": "#4a6b8a",
            "PRIMARY_DARK": "#37536c",
            "ACCENT": "#7d8f9f",
            "TEXT": "#17212b",
            "BG_LIGHT": "#eef2f6",
            "SURFACE": "#fafcff",
            "MUTED": "#5e6c7c",
            "BORDER": "#d4dbe4",
            "HOVER": "#5a7da0",
        },
    },
}


def normalize_tok_variant(variant: str) -> str:
    candidate = str(variant or "light").strip().lower()
    return candidate if candidate in TOK_THEME_VARIANTS else "light"


def get_available_tok_variants():
    return [get_tok_variant_meta(variant) for variant in TOK_THEME_ORDER]


def get_tok_variant_meta(variant: str):
    key = normalize_tok_variant(variant)
    meta = dict(TOK_THEME_VARIANTS[key])
    meta["key"] = key
    return meta


def _resolve_variant_tokens(variant: str):
    key = normalize_tok_variant(variant)
    palette = TOK_THEME_VARIANTS[key]["palette"]

    primary = palette["PRIMARY"]
    primary_dark = palette["PRIMARY_DARK"]
    text = palette["TEXT"]
    bg_light = palette["BG_LIGHT"]
    surface = palette["SURFACE"]
    muted = palette["MUTED"]
    border = palette["BORDER"]
    hover = palette["HOVER"]
    is_dark = key == "dark"

    tokens = {
        "MAIN_BG": bg_light,
        "STATUS_BG": surface,
        "TAB_BG": surface,
        "TAB_SELECTED_BG": surface,
        "GROUPBOX_TEXT": text,
        "LIST_BG": surface,
        "LIST_BORDER": border,
        "SEL_START": primary,
        "SEL_END": primary_dark,
        "HEADER_START": surface,
        "HEADER_END": bg_light,
        "BUTTON_START": primary,
        "BUTTON_END": primary_dark,
        "HOVER": hover,
        "HOVER_START": hover,
        "HOVER_END": primary,
        "BUTTON_PRESSED": primary_dark,
        "PRIMARY_BUTTON_START": primary,
        "PRIMARY_BUTTON_END": primary_dark,
        "LINEEDIT_FOCUS": primary,
        "LABEL_COLOR": text,
        "LABEL_HEADER_COLOR": text,
        "SURFACE": surface,
        "BORDER": border,
        "MUTED": muted,
        "TEXT": text,
        "BG_LIGHT": bg_light,
        "PRIMARY": primary,
    }

    if is_dark:
        tokens.update(
            {
                "TOOLTIP_BG": surface,
                "TOOLTIP_TEXT": text,
                "LIST_ITEM_COLOR": text,
                "LIST_ITEM_SELECTED_INACTIVE_BG": "#3a4555",
                "LIST_ITEM_SELECTED_INACTIVE_TEXT": text,
                "MENU_SELECTED_BG": "#3a4555",
                "MENU_SELECTED_TEXT": text,
                "LINEEDIT_BORDER": border,
                "LINEEDIT_TEXT": text,
                "SUBHEADER_TEXT": muted,
                "HEADER_SECTION_TEXT": text,
                "MESSAGEBOX_TEXT": text,
            }
        )
    else:
        tokens.update(
            {
                "TOOLTIP_BG": "#2c3e50",
                "TOOLTIP_TEXT": "#ffffff",
                "LIST_ITEM_COLOR": "#212529",
                "LIST_ITEM_SELECTED_INACTIVE_BG": "#e9ecef",
                "LIST_ITEM_SELECTED_INACTIVE_TEXT": "#212529",
                "MENU_SELECTED_BG": bg_light,
                "MENU_SELECTED_TEXT": "#212529",
                "LINEEDIT_BORDER": border,
                "LINEEDIT_TEXT": "#212529",
                "SUBHEADER_TEXT": muted,
                "HEADER_SECTION_TEXT": muted,
                "MESSAGEBOX_TEXT": "#212529",
            }
        )

    return key, tokens


def apply_stylesheet(app: QApplication, *, theme: str = "tok", variant: str = "light"):
    """Apply a modern application stylesheet for the selected TOK variant."""
    try:
        font = QFont("Segoe UI", 10)
        app.setFont(font)

        _, tokens = _resolve_variant_tokens(variant)
        css = """
            * {
                font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }
            QMainWindow { background: {MAIN_BG}; }
            QToolBar { spacing: 8px; padding: 6px 10px; background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {SURFACE}, stop:1 {BG_LIGHT}); border-bottom: 1px solid {BORDER}; }
            QToolBar::separator { width: 1px; background: {BORDER}; margin: 4px 6px; }
            QStatusBar { background: {STATUS_BG}; border-top: 1px solid {BORDER}; padding: 4px 10px; }
            QStatusBar QLabel { color: {MUTED}; padding: 2px 8px; }
            QTabWidget::pane { border: 1px solid {BORDER}; background: {SURFACE}; border-radius: 4px; top: -1px; }
            QTabBar::tab { background: {TAB_BG}; color: {TEXT}; padding: 8px 16px; margin-right: 2px; border: 1px solid {BORDER}; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: {TAB_SELECTED_BG}; color: {TEXT}; font-weight: 700; }
            QTabBar::tab:hover:!selected { background: {HOVER}; color: {TEXT}; }
            QGroupBox { font-weight: 700; font-size: 10.5pt; color: {GROUPBOX_TEXT}; margin-top: 16px; padding-top: 12px; border: 1px solid {BORDER}; border-radius: 6px; background: {SURFACE}; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 12px; padding: 0 6px; background: {SURFACE}; }
            QListWidget, QTreeWidget { background: {LIST_BG}; border: 1px solid {LIST_BORDER}; border-radius: 4px; alternate-background-color: {BG_LIGHT}; outline: none; }
            QListWidget::item, QTreeWidget::item { padding: 6px 8px; border-radius: 3px; color: {LIST_ITEM_COLOR}; }
            QListWidget::item:selected:active, QTreeWidget::item:selected:active { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {SEL_START}, stop:1 {SEL_END}); color: #ffffff; }
            QListWidget::item:selected:!active, QTreeWidget::item:selected:!active { background: {LIST_ITEM_SELECTED_INACTIVE_BG}; color: {LIST_ITEM_SELECTED_INACTIVE_TEXT}; }
            QListWidget::item:hover:!selected, QTreeWidget::item:hover:!selected { background: {BG_LIGHT}; }
            QHeaderView::section { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {HEADER_START}, stop:1 {HEADER_END}); color: {HEADER_SECTION_TEXT}; padding: 6px 8px; border: none; border-right: 1px solid {BORDER}; border-bottom: 1px solid {BORDER}; font-weight: 500; }
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {BUTTON_START}, stop:1 {BUTTON_END}); color: #ffffff; border: 1px solid {BUTTON_END}; border-radius: 6px; padding: 8px 16px; font-weight: 700; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {HOVER_START}, stop:1 {HOVER_END}); border-color: {HOVER_END}; color: #ffffff; }
            QPushButton:pressed { background: {BUTTON_PRESSED}; }
            QPushButton[class="primary"] { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {PRIMARY_BUTTON_START}, stop:1 {PRIMARY_BUTTON_END}); color: #ffffff; border: none; }
            QPushButton[class="primary"]:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {PRIMARY_BUTTON_START}, stop:1 {PRIMARY_BUTTON_END}); }
            QLineEdit { background: {SURFACE}; border: 1px solid {LINEEDIT_BORDER}; border-radius: 4px; padding: 6px 10px; selection-background-color: {PRIMARY}; color: {LINEEDIT_TEXT}; }
            QLineEdit:focus { border-color: {LINEEDIT_FOCUS}; background: {SURFACE}; }
            QLineEdit:read-only { background: {BG_LIGHT}; color: {MUTED}; }
            QLabel { color: {LABEL_COLOR}; font-weight: 500; }
            QLabel[class="header"] { font-size: 12pt; font-weight: 700; color: {LABEL_HEADER_COLOR}; }
            QLabel[class="subheader"] { background: {SURFACE}; font-weight: 500; color: {SUBHEADER_TEXT}; }
            QFormLayout QLabel { font-weight: 600; }
            QMenuBar { background: {SURFACE}; border-bottom: 1px solid {BORDER}; padding: 2px; }
            QMenuBar::item { background: transparent; padding: 6px 12px; border-radius: 4px; color: {TEXT}; }
            QMenuBar::item:selected { background: {BG_LIGHT}; }
            QMenu { background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 4px; padding: 4px; }
            QMenu::item { padding: 6px 24px 6px 12px; border-radius: 3px; color: {TEXT}; }
            QMenu::item:selected { background: {MENU_SELECTED_BG}; color: {MENU_SELECTED_TEXT}; }
            QMessageBox { background: {SURFACE}; }
            QMessageBox QLabel { color: {MESSAGEBOX_TEXT}; }
            QToolTip { background: {TOOLTIP_BG}; color: {TOOLTIP_TEXT}; border: none; border-radius: 4px; padding: 6px 10px; opacity: 220; }
        """

        for key, value in tokens.items():
            css = css.replace(f"{{{key}}}", value)
        app.setStyleSheet(css)
    except Exception as e:
        print(f"Stylesheet uygulanamadi: {e}")


def toggle_contrast(app: QApplication, window):
    """Toggle application stylesheet to inspect native contrast behavior."""
    try:
        if not hasattr(window, "_previous_stylesheet"):
            window._previous_stylesheet = app.styleSheet() or ""
            app.setStyleSheet("")
        else:
            app.setStyleSheet(getattr(window, "_previous_stylesheet", ""))
            delattr(window, "_previous_stylesheet")

        if not hasattr(window, "_previous_palette"):
            window._previous_palette = app.palette()
            light_palette = QPalette()
            light_palette.setColor(QPalette.Window, QColor("#f5f6f7"))
            light_palette.setColor(QPalette.WindowText, QColor("#212529"))
            light_palette.setColor(QPalette.Base, QColor("#ffffff"))
            light_palette.setColor(QPalette.AlternateBase, QColor("#f8f9fa"))
            light_palette.setColor(QPalette.Highlight, QColor("#3498db"))
            light_palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
            app.setPalette(light_palette)
        else:
            app.setPalette(window._previous_palette)
            delattr(window, "_previous_palette")
    except Exception:
        pass


def set_tok_theme_variant(app: QApplication, window, variant: str) -> str:
    """Apply a specific TOK theme variant and store it on the window."""
    key = normalize_tok_variant(variant)
    try:
        apply_stylesheet(app, theme="tok", variant=key)
        setattr(window, "_tok_variant", key)
    except Exception:
        pass
    return key


def toggle_tok_theme(app: QApplication, window):
    """Cycle through available TOK theme variants."""
    try:
        current = normalize_tok_variant(getattr(window, "_tok_variant", "light"))
        index = TOK_THEME_ORDER.index(current)
        new_variant = TOK_THEME_ORDER[(index + 1) % len(TOK_THEME_ORDER)]
        return set_tok_theme_variant(app, window, new_variant)
    except Exception:
        return normalize_tok_variant(getattr(window, "_tok_variant", "light"))
