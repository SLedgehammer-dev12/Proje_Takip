"""Tests for main window UI layout integrity.

Catches regressions where UI components (menubar, toolbar, tabs, sort combo)
are missing or incorrectly wired after refactoring.
"""

import os
import tempfile
import pytest
from PySide6.QtWidgets import QApplication, QMenuBar, QToolBar, QTabWidget, QComboBox


@pytest.fixture(scope="module")
def app():
    qapp = QApplication.instance()
    if qapp is None:
        qapp = QApplication([])
    return qapp


@pytest.fixture
def main_window(app):
    from database import ProjeTakipDB
    from main_window import AnaPencere

    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test_ui_layout.db")

    db = ProjeTakipDB(db_path)
    window = AnaPencere(db_dosyasi=db_path, db=db)
    window.setup_ui()
    # Ensure menus are created (main_window.py does this in try/except)
    try:
        window._setup_menubar()
    except Exception:
        pass
    app.processEvents()
    yield window
    db.close()
    window.close()
    window.deleteLater()
    app.processEvents()
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)


class TestMenuBar:
    def test_menubar_exists(self, main_window):
        menubar = main_window.menuBar()
        assert menubar is not None

    def test_file_menu_exists(self, main_window):
        actions = main_window.menuBar().actions()
        texts = [a.text().replace("&", "") for a in actions]
        assert "Dosya" in texts

    def test_project_menu_exists(self, main_window):
        actions = main_window.menuBar().actions()
        texts = [a.text().replace("&", "") for a in actions]
        assert "Proje" in texts

    def test_revision_menu_exists(self, main_window):
        actions = main_window.menuBar().actions()
        texts = [a.text().replace("&", "") for a in actions]
        assert "Revizyon" in texts

    def test_filter_menu_exists(self, main_window):
        actions = main_window.menuBar().actions()
        texts = [a.text().replace("&", "") for a in actions]
        assert "Filtre" in texts

    def test_view_menu_exists(self, main_window):
        actions = main_window.menuBar().actions()
        texts = [a.text().replace("&", "") for a in actions]
        assert "Görünüm" in texts

    def test_report_menu_exists(self, main_window):
        actions = main_window.menuBar().actions()
        texts = [a.text().replace("&", "") for a in actions]
        assert "Rapor" in texts

    def test_help_menu_exists(self, main_window):
        actions = main_window.menuBar().actions()
        texts = [a.text().replace("&", "") for a in actions]
        assert "Yardım" in texts

    def test_menubar_has_all_expected_menus(self, main_window):
        actions = main_window.menuBar().actions()
        texts = [a.text().replace("&", "") for a in actions]
        expected = ["Dosya", "Proje", "Revizyon", "Filtre", "Görünüm", "Rapor", "Yardım"]
        for menu_name in expected:
            assert menu_name in texts, f"Menu '{menu_name}' not found in menubar"


class TestProjectPanel:
    def test_search_box_exists(self, main_window):
        assert hasattr(main_window, "arama_kutusu")
        assert main_window.arama_kutusu is not None

    def test_sort_combo_exists(self, main_window):
        assert hasattr(main_window, "sort_combo")
        assert main_window.sort_combo is not None
        assert isinstance(main_window.sort_combo, QComboBox)

    def test_sort_combo_has_items(self, main_window):
        assert main_window.sort_combo.count() > 0
        assert main_window.sort_combo.count() >= 10

    def test_project_list_exists(self, main_window):
        assert hasattr(main_window, "proje_listesi_widget")
        assert main_window.proje_listesi_widget is not None

    def test_project_tree_exists(self, main_window):
        assert hasattr(main_window, "proje_agaci_widget")
        assert main_window.proje_agaci_widget is not None

    def test_tab_widget_exists(self, main_window):
        assert hasattr(main_window, "sekme_widget")
        assert main_window.sekme_widget is not None
        assert isinstance(main_window.sekme_widget, QTabWidget)

    def test_tab_widget_has_tabs(self, main_window):
        tab_widget = main_window.sekme_widget
        assert tab_widget.count() >= 4
        tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
        assert "Tüm Projeler" in tab_names
        assert "Kategori Görünümü" in tab_names
        assert "Gösterge Paneli" in tab_names
        assert "Loglar" in tab_names


class TestToolbar:
    def test_toolbar_exists(self, main_window):
        toolbars = main_window.findChildren(QToolBar)
        assert len(toolbars) > 0
