from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor, QFont


def apply_stylesheet(app: QApplication, *, theme: str = "tok", variant: str = "light"):
    """Apply modern, professional stylesheet to the application.

    Parameters:
    - app: QApplication instance
    - theme: the theme name (only 'tok' supported currently)
    - variant: 'light' or 'dark'
    """
    try:
        # Set application font - Segoe UI: Windows'ta en güzel ve okunaklı font
        font = QFont("Segoe UI", 10)
        app.setFont(font)

        # TOK color tokens - Yumuşak ve dengeli renkler
        if variant == "dark":
            PRIMARY = "#5b9cf5"            # Yumuşak mavi
            PRIMARY_DARK = "#4a8ad6"       # Daha koyu yumuşak mavi
            ACCENT = "#6fcdb8"             # Yumuşak turkuaz
            TEXT = "#f0f3f7"               # Parlak metin (koyu arka planlarda)
            BG_LIGHT = "#1a1f2e"           # Yumuşak koyu arka plan
            SURFACE = "#232936"            # Koyu yüzey rengi
            MUTED = "#a8b2bf"              # Açık gri (ikincil metinler)
            BORDER = "#3a4555"             # Daha belirgin kenarlık
            HOVER = "#6ba5f7"              # Yumuşak hover mavi
        else:
            PRIMARY = "#5b9cf5"            # Yumuşak pastel mavi (çok parlak değil)
            PRIMARY_DARK = "#4a8ad6"       # Yumuşak koyu mavi
            ACCENT = "#5dba9f"             # Yumuşak yeşil-turkuaz
            TEXT = "#0d1117"               # Çok koyu metin (beyaz panellerde çok net)
            BG_LIGHT = "#f5f7fa"           # Çok hafif mavi-gri arka plan
            SURFACE = "#ffffff"            # Beyaz yüzey
            MUTED = "#5a6575"              # Koyu gri (daha okunaklı)
            BORDER = "#d4dce6"             # Yumuşak kenarlık
            HOVER = "#6ba5f7"              # Yumuşak hover mavi

        # Local variables for styling tokens
        main_bg = BG_LIGHT
        status_bg = SURFACE
        tab_bg = SURFACE
        tab_selected_bg = SURFACE
        groupbox_text = TEXT
        list_bg = SURFACE
        list_border = BORDER
        sel_start, sel_end = PRIMARY, PRIMARY_DARK
        header_start, header_end = SURFACE, BG_LIGHT
        button_start, button_end = PRIMARY, PRIMARY_DARK
        hover_start, hover_end = HOVER, PRIMARY
        button_pressed = PRIMARY_DARK
        primary_button_start, primary_button_end = PRIMARY, PRIMARY_DARK
        lineedit_focus = PRIMARY
        label_color = TEXT
        label_header_color = TEXT
        
        # Dark mode için dinamik renklendirme
        if variant == "dark":
            tooltip_bg = SURFACE
            tooltip_text = TEXT
            list_item_color = TEXT
            list_item_selected_inactive_bg = "#3a4555"
            list_item_selected_inactive_text = TEXT
            menu_selected_bg = "#3a4555"
            menu_selected_text = TEXT
            lineedit_border = BORDER
            lineedit_text = TEXT
            subheader_text = MUTED
            header_section_text = TEXT
            messagebox_text = TEXT
        else:
            tooltip_bg = "#2c3e50"
            tooltip_text = "#ffffff"
            list_item_color = "#212529"
            list_item_selected_inactive_bg = "#e9ecef"
            list_item_selected_inactive_text = "#212529"
            menu_selected_bg = "#e7f3ff"
            menu_selected_text = "#212529"
            lineedit_border = "#ced4da"
            lineedit_text = "#212529"
            subheader_text = "#495057"
            header_section_text = "#495057"
            messagebox_text = "#212529"

        # CSS template using token placeholders that we'll replace below
        css = """
            /* ==================== GLOBAL STYLES ==================== */
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

        css = (css
               .replace("{MAIN_BG}", main_bg)
               .replace("{STATUS_BG}", status_bg)
               .replace("{TAB_BG}", tab_bg)
               .replace("{TAB_SELECTED_BG}", tab_selected_bg)
               .replace("{GROUPBOX_TEXT}", groupbox_text)
               .replace("{LIST_BG}", list_bg)
               .replace("{LIST_BORDER}", list_border)
               .replace("{SEL_START}", sel_start)
               .replace("{SEL_END}", sel_end)
               .replace("{HEADER_START}", header_start)
               .replace("{HEADER_END}", header_end)
               .replace("{BUTTON_START}", button_start)
               .replace("{BUTTON_END}", button_end)
               .replace("{HOVER}", hover_start)
               .replace("{HOVER_START}", hover_start)
               .replace("{HOVER_END}", hover_end)
               .replace("{BUTTON_PRESSED}", button_pressed)
               .replace("{PRIMARY_BUTTON_START}", primary_button_start)
               .replace("{PRIMARY_BUTTON_END}", primary_button_end)
               .replace("{LINEEDIT_FOCUS}", lineedit_focus)
               .replace("{LABEL_COLOR}", label_color)
               .replace("{LABEL_HEADER_COLOR}", label_header_color)
               .replace("{TOOLTIP_BG}", tooltip_bg)
               .replace("{TOOLTIP_TEXT}", tooltip_text)
               .replace("{LIST_ITEM_COLOR}", list_item_color)
               .replace("{LIST_ITEM_SELECTED_INACTIVE_BG}", list_item_selected_inactive_bg)
               .replace("{LIST_ITEM_SELECTED_INACTIVE_TEXT}", list_item_selected_inactive_text)
               .replace("{MENU_SELECTED_BG}", menu_selected_bg)
               .replace("{MENU_SELECTED_TEXT}", menu_selected_text)
               .replace("{LINEEDIT_BORDER}", lineedit_border)
               .replace("{LINEEDIT_TEXT}", lineedit_text)
               .replace("{SUBHEADER_TEXT}", subheader_text)
               .replace("{HEADER_SECTION_TEXT}", header_section_text)
               .replace("{MESSAGEBOX_TEXT}", messagebox_text)
               .replace("{SURFACE}", SURFACE)
               .replace("{BORDER}", BORDER)
               .replace("{MUTED}", MUTED)
               .replace("{TEXT}", TEXT)
               .replace("{BG_LIGHT}", BG_LIGHT)
               .replace("{PRIMARY}", PRIMARY)
               )

        app.setStyleSheet(css)
    except Exception as e:
        print(f"Stylesheet uygulanamadı: {e}")


def toggle_contrast(app: QApplication, window):
    """Toggle application stylesheet: switch between saved stylesheet and empty stylesheet to test contrast."""
    try:
        # toggle stylesheet
        if not hasattr(window, "_previous_stylesheet"):
            window._previous_stylesheet = app.styleSheet() or ""
            app.setStyleSheet("")
        else:
            app.setStyleSheet(getattr(window, "_previous_stylesheet", ""))
            delattr(window, "_previous_stylesheet")

        # toggle palette
        if not hasattr(window, "_previous_palette"):
            window._previous_palette = app.palette()
            lightPalette = QPalette()
            lightPalette.setColor(QPalette.Window, QColor("#f5f6f7"))
            lightPalette.setColor(QPalette.WindowText, QColor("#212529"))
            lightPalette.setColor(QPalette.Base, QColor("#ffffff"))
            lightPalette.setColor(QPalette.AlternateBase, QColor("#f8f9fa"))
            lightPalette.setColor(QPalette.Highlight, QColor("#3498db"))
            lightPalette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
            app.setPalette(lightPalette)
        else:
            app.setPalette(window._previous_palette)
            delattr(window, "_previous_palette")
    except Exception:
        pass


def toggle_tok_theme(app: QApplication, window):
    """Toggle between TOK light and dark theme variants.

    Stores the current variant on the window object as `_tok_variant` so the UI can toggle back and forth.
    """
    try:
        current = getattr(window, "_tok_variant", "light")
        new_variant = "dark" if current == "light" else "light"
        apply_stylesheet(app, theme="tok", variant=new_variant)
        setattr(window, "_tok_variant", new_variant)
    except Exception:
        pass
