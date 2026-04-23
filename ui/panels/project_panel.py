from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QListWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
    QListWidgetItem,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal, QTimer, QSignalBlocker
from PySide6.QtGui import QIcon, QColor, QBrush, QPixmap, QPainter, QPen, QFont
from typing import List, Dict
import itertools
from models import ProjeModel


class ProjectPanel(QWidget):
    """
    Panel for displaying and managing project lists.

    Provides both list and tree views of projects with status-based coloring,
    search functionality, and advanced filtering options.

    Signals:
        project_selected: Emitted when a project is selected (ProjeModel or None)
        project_moved: Emitted when a project is moved to a new category (proje_id, kategori_id)
        advanced_filter_clicked: Emitted when the advanced filter button is clicked
        clear_filter_clicked: Emitted when the clear filter button is clicked
    """

    project_selected = Signal(object)  # Emits ProjeModel or None
    project_moved = Signal(int, int)  # proje_id, yeni_kategori_id
    advanced_filter_clicked = Signal()
    clear_filter_clicked = Signal()

    def __init__(self, parent=None):
        """Initialize the ProjectPanel."""
        super().__init__(parent)
        self.tum_projeler: List[ProjeModel] = []
        self.kategori_items_map: Dict[int, QTreeWidgetItem] = {}
        self._kategori_yolu_cache: Dict[int, str] = {}
        self._batch_size = 50  # UI'ya projeleri parça parça eklemek için
        self._pending_project_iter = None
        self.setup_ui()
        # Create default status icons
        self._status_icons = self._create_status_icons()
        # No legend UI to set - the list and tree icons represent the status

    def setup_ui(self):
        """Set up the user interface components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Arama ve Filtre
        search_layout = QHBoxLayout()
        self.arama_kutusu = QLineEdit()
        self.arama_kutusu.setPlaceholderText("Proje Ara (Kod veya İsim)...")
        self.arama_kutusu.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.arama_kutusu)

        # Filtre Butonları
        self.btn_adv_filter = QPushButton("Filtrele")
        self.btn_adv_filter.setIcon(QIcon.fromTheme("view-filter"))
        self.btn_adv_filter.setToolTip("Gelişmiş Filtreleme")
        self.btn_adv_filter.clicked.connect(self.advanced_filter_clicked.emit)
        search_layout.addWidget(self.btn_adv_filter)

        self.btn_clear_filter = QPushButton("Temizle")
        self.btn_clear_filter.setIcon(QIcon.fromTheme("edit-clear"))
        self.btn_clear_filter.setToolTip("Filtreleri Temizle")
        self.btn_clear_filter.clicked.connect(self.clear_filter_clicked.emit)
        search_layout.addWidget(self.btn_clear_filter)

        self.filter_indicator = QLabel("Filtre: Yok")
        self.filter_indicator.setStyleSheet("color: #666; padding: 5px;")
        search_layout.addWidget(self.filter_indicator)
        # No legend in filter bar - the icons in list/tree are sufficient
        layout.addLayout(search_layout)

        # Splitter for List and Tree
        self.splitter = QSplitter(Qt.Horizontal)

        # Liste Görünümü
        self.proje_listesi_widget = QListWidget()
        self.proje_listesi_widget.setAlternatingRowColors(
            False
        )  # Renklendirme için kapalı olmalı
        # Allow multi-selection with Shift/Ctrl
        # Check for attribute availability instead of importing extra Qt widgets
        if hasattr(QListWidget, "ExtendedSelection"):
            self.proje_listesi_widget.setSelectionMode(QListWidget.ExtendedSelection)
        else:
            # Fallback: ExtendedSelection may not be available on some Qt versions
            self.proje_listesi_widget.setSelectionMode(QListWidget.MultiSelection)
        self.proje_listesi_widget.itemSelectionChanged.connect(
            self._on_list_selection_changed
        )
        self.splitter.addWidget(self.proje_listesi_widget)

        # Ağaç Görünümü
        from widgets import KategoriAgaci

        self.proje_agaci_widget = KategoriAgaci(self)
        self.proje_agaci_widget.setHeaderHidden(True)
        self.proje_agaci_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.proje_agaci_widget.setAlternatingRowColors(
            False
        )  # Renklendirme için kapalı olmalı
        # Allow selecting multiple projects in the tree with Shift/Ctrl
        try:
            self.proje_agaci_widget.setSelectionMode(QTreeWidget.ExtendedSelection)
        except Exception:
            # Keep default if not available
            pass
        self.proje_agaci_widget.itemSelectionChanged.connect(
            self._on_tree_selection_changed
        )
        self.proje_agaci_widget.setDragEnabled(True)
        self.proje_agaci_widget.setAcceptDrops(True)
        self.proje_agaci_widget.setDropIndicatorShown(True)
        self.proje_agaci_widget.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.splitter.addWidget(self.proje_agaci_widget)

        layout.addWidget(self.splitter)

        # Timer for search debounce
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self._apply_search_filter)

    def set_categories(self, categories: List[tuple]):
        """Set the categories list for the tree view."""
        self.categories = categories

    def load_projects(self, projects: List[ProjeModel]):
        self.tum_projeler = projects
        self._populate_ui(projects)

    def _populate_ui(self, projects: List[ProjeModel]):
        """Projeleri UI'a kademeli olarak yükle (donmayı önler)."""
        selected_project_id = self._get_selected_project_id()

        # Ön hazırlık: temizle ve kategorileri kur
        self.proje_listesi_widget.setUpdatesEnabled(False)
        self.proje_agaci_widget.setUpdatesEnabled(False)
        list_blocker = QSignalBlocker(self.proje_listesi_widget)
        tree_blocker = QSignalBlocker(self.proje_agaci_widget)
        try:
            self.proje_listesi_widget.clear()
            self.proje_agaci_widget.clear()
            self.kategori_items_map.clear()

            # Kategorisiz kök
            kategorisiz_item = QTreeWidgetItem(self.proje_agaci_widget, ["Kategorisiz"])
            KATEGORI_ID_ROL = Qt.UserRole + 1
            kategorisiz_item.setData(0, KATEGORI_ID_ROL, 0)
            kategorisiz_item.setFlags(kategorisiz_item.flags() | Qt.ItemIsDropEnabled)
            self.kategori_items_map[0] = kategorisiz_item

            # Kategoriler
            if hasattr(self, "categories") and self.categories:
                for cid, isim, parent in self.categories:
                    parent_item = self.kategori_items_map.get(parent) if parent else None
                    if parent_item:
                        item = QTreeWidgetItem(parent_item, [isim])
                    else:
                        item = QTreeWidgetItem(self.proje_agaci_widget, [isim])
                    item.setData(0, KATEGORI_ID_ROL, cid)
                    item.setFlags(item.flags() | Qt.ItemIsDropEnabled)
                    self.kategori_items_map[cid] = item
        finally:
            del list_blocker
            del tree_blocker

        # Batch ekleme için iterator hazırla
        self._pending_project_iter = iter(projects)

        def _add_batch():
            nonlocal kategorisiz_item
            batch = list(itertools.islice(self._pending_project_iter, self._batch_size))
            if not batch:
                # Tüm projeler eklendi
                self.proje_listesi_widget.setUpdatesEnabled(True)
                self.proje_agaci_widget.setUpdatesEnabled(True)
                if not getattr(self, "_tree_expanded_once", False):
                    try:
                        self.proje_agaci_widget.expandAll()
                        self._tree_expanded_once = True
                    except Exception:
                        pass
                self._restore_selection(selected_project_id)
                return

            for proje in batch:
                # Liste görünümü
                if proje.durum == "Onayli":
                    icon = self._status_icons.get('onayli')
                    color = QColor("#d4edda")
                elif proje.durum == "Notlu Onayli":
                    icon = self._status_icons.get('notlu_onayli')
                    color = QColor("#fff3cd")
                elif proje.durum == "Reddedildi":
                    icon = self._status_icons.get('reddedildi')
                    color = QColor("#f8d7da")
                else:
                    icon = self._status_icons.get('default')
                    color = None

                display_text = f"{proje.proje_kodu} - {proje.proje_ismi}"
                item = QListWidgetItem(display_text)
                if icon:
                    try:
                        item.setIcon(icon)
                    except Exception:
                        pass
                item.setData(Qt.UserRole, proje)
                if color:
                    item.setBackground(QBrush(color))
                self.proje_listesi_widget.addItem(item)

                # Ağaç görünümü
                icon_tree = None
                if proje.durum == "Onayli":
                    icon_tree = self._status_icons.get('onayli')
                elif proje.durum == "Notlu Onayli":
                    icon_tree = self._status_icons.get('notlu_onayli')
                elif proje.durum == "Reddedildi":
                    icon_tree = self._status_icons.get('reddedildi')

                kategori_id = proje.kategori_id if proje.kategori_id is not None else 0
                parent_item = self.kategori_items_map.get(kategori_id, kategorisiz_item)

                t_item = QTreeWidgetItem(parent_item)
                t_item.setText(0, display_text)
                if icon_tree:
                    try:
                        t_item.setIcon(0, icon_tree)
                    except Exception:
                        pass
                t_item.setData(0, Qt.UserRole, proje)

                if proje.durum == "Onayli":
                    t_item.setBackground(0, QColor("#d4edda"))
                elif proje.durum == "Notlu Onayli":
                    t_item.setBackground(0, QColor("#fff3cd"))
                elif proje.durum == "Reddedildi":
                    t_item.setBackground(0, QColor("#f8d7da"))

            # Bir sonraki parti için event loop'a dön
            QTimer.singleShot(0, _add_batch)

        # İlk parti
        QTimer.singleShot(0, _add_batch)

    def _create_status_icons(self, size: int = 16) -> dict:
        """Return a dict of QIcons for statuses (onayli, notlu_onayli, reddedildi, default).

        Icons are generated at runtime, so no asset files are needed.
        """
        icons = {}
        def make_icon(color_hex: str, symbol: str = None):
            pix = QPixmap(size, size)
            pix.fill(QColor(0,0,0,0))
            painter = QPainter(pix)
            try:
                painter.setRenderHint(QPainter.Antialiasing)
                c = QColor(color_hex)
                pen = QPen(c.darker(110))
                pen.setWidth(max(1, size // 10))
                painter.setPen(pen)
                painter.setBrush(c)
                rect = pix.rect().adjusted(1,1,-1,-1)
                painter.drawEllipse(rect)
                if symbol:
                    # Draw a white symbol text centered
                    font = QFont()
                    font.setBold(True)
                    font.setPointSize(max(8, size - 4))
                    painter.setFont(font)
                    painter.setPen(QPen(QColor('#ffffff')))
                    painter.drawText(rect, int(Qt.AlignCenter), symbol)
            finally:
                painter.end()
            return QIcon(pix)

        icons['onayli'] = make_icon('#28a745', '✓')
        icons['notlu_onayli'] = make_icon('#ff9800', '!')
        icons['reddedildi'] = make_icon('#dc3545', '×')
        icons['default'] = make_icon('#6c757d', '')
        return icons

    def _on_search_text_changed(self):
        self.filter_timer.start(500)  # Optimized: 300ms → 500ms (daha az ara sorgulama)

    def _apply_search_filter(self):
        text = self.arama_kutusu.text().lower()
        filtered = [
            p
            for p in self.tum_projeler
            if text in p.proje_kodu.lower()
            or text in p.proje_ismi.lower()
            or text in (p.hiyerarsi or "").lower()
        ]
        self._populate_ui(filtered)

    def _get_selected_project_id(self):
        try:
            items = self.proje_listesi_widget.selectedItems()
            if items:
                proje = items[0].data(Qt.UserRole)
                if proje and getattr(proje, "id", None) is not None:
                    return proje.id
        except Exception:
            pass
        try:
            items = self.proje_agaci_widget.selectedItems()
            if items:
                proje = items[0].data(0, Qt.UserRole)
                if proje and getattr(proje, "id", None) is not None:
                    return proje.id
        except Exception:
            pass
        return None

    def _restore_selection(self, project_id):
        list_blocker = QSignalBlocker(self.proje_listesi_widget)
        tree_blocker = QSignalBlocker(self.proje_agaci_widget)
        if project_id is None:
            self.proje_listesi_widget.clearSelection()
            self.proje_agaci_widget.clearSelection()
            del list_blocker
            del tree_blocker
            self.project_selected.emit(None)
            return

        matched_project = None

        try:
            for row in range(self.proje_listesi_widget.count()):
                item = self.proje_listesi_widget.item(row)
                proje = item.data(Qt.UserRole)
                if proje and getattr(proje, "id", None) == project_id:
                    self.proje_listesi_widget.setCurrentItem(item)
                    matched_project = proje
                    break
        except Exception:
            pass

        try:
            root = self.proje_agaci_widget.invisibleRootItem()
            stack = [root.child(i) for i in range(root.childCount())]
            while stack:
                item = stack.pop()
                proje = item.data(0, Qt.UserRole)
                if proje and getattr(proje, "id", None) == project_id:
                    self.proje_agaci_widget.setCurrentItem(item)
                    if matched_project is None:
                        matched_project = proje
                    break
                for idx in range(item.childCount()):
                    stack.append(item.child(idx))
        except Exception:
            pass

        if matched_project is None:
            self.proje_listesi_widget.clearSelection()
            self.proje_agaci_widget.clearSelection()

        del list_blocker
        del tree_blocker
        self.project_selected.emit(matched_project)

    def _on_list_selection_changed(self):
        items = self.proje_listesi_widget.selectedItems()
        if items:
            proje = items[0].data(Qt.UserRole)
            self._sync_tree_selection(getattr(proje, "id", None))
            self.project_selected.emit(proje)
        else:
            self._sync_tree_selection(None)
            self.project_selected.emit(None)

    def _on_tree_selection_changed(self):
        items = self.proje_agaci_widget.selectedItems()
        if items:
            proje = items[0].data(0, Qt.UserRole)
            if proje:  # Kategori değilse
                self._sync_list_selection(getattr(proje, "id", None))
                self.project_selected.emit(proje)
                return
        self._sync_list_selection(None)
        self.project_selected.emit(None)

    def _sync_list_selection(self, project_id):
        blocker = QSignalBlocker(self.proje_listesi_widget)
        try:
            if project_id is None:
                self.proje_listesi_widget.clearSelection()
                return
            for row in range(self.proje_listesi_widget.count()):
                item = self.proje_listesi_widget.item(row)
                proje = item.data(Qt.UserRole)
                if proje and getattr(proje, "id", None) == project_id:
                    self.proje_listesi_widget.setCurrentItem(item)
                    return
            self.proje_listesi_widget.clearSelection()
        finally:
            del blocker

    def _sync_tree_selection(self, project_id):
        blocker = QSignalBlocker(self.proje_agaci_widget)
        try:
            if project_id is None:
                self.proje_agaci_widget.clearSelection()
                return
            root = self.proje_agaci_widget.invisibleRootItem()
            stack = [root.child(i) for i in range(root.childCount())]
            while stack:
                item = stack.pop()
                proje = item.data(0, Qt.UserRole)
                if proje and getattr(proje, "id", None) == project_id:
                    self.proje_agaci_widget.setCurrentItem(item)
                    return
                for idx in range(item.childCount()):
                    stack.append(item.child(idx))
            self.proje_agaci_widget.clearSelection()
        finally:
            del blocker
