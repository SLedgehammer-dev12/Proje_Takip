# main_window.py
import sys
import os
import logging
import datetime

# 'Tuple' tipi yerine ProjeModel ve RevizyonModel kullanılacak
from typing import Optional, Dict, List

# Counter removed - not used directly in this module

from PySide6.QtWidgets import (
    QMainWindow,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QInputDialog,
    QApplication,
    QTreeWidgetItem,
    QDialog,
    QVBoxLayout,
    QMenu,
)

# QTimer, çökme düzeltmesi için eklendi
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSettings, QUrl
from PySide6.QtGui import (
    QBrush,
    QColor,
    QAction,
    QDesktopServices,
    QPixmap,
    QImage,
    QFont,
    QIcon,
)  # QFont eklendi

# Modüllerimizden içe aktarma
from config import (
    APP_NAME,
    APP_VERSION,
    ENABLE_WATERMARK,
    UPDATE_RELEASE_ASSET_EXTENSIONS,
    UPDATE_RELEASE_ASSET_PATTERN,
    UPDATE_RELEASE_PAGE_URL,
    UPDATE_REPO_NAME,
    UPDATE_REPO_OWNER,
    WATERMARK_IMAGE_PATH,
    WATERMARK_OPACITY,
)

# YENİ: Veri modelleri import edildi
from models import Durum, ProjeModel, RevizyonModel
from database import ProjeTakipDB
from utils import dosyadan_tarih_sayi_cikar, dosyadan_proje_bilgisi_cikar, get_class_logger

# Arayüz modüllerimizden içe aktarma
from dialogs import (
    ProjeDialog,
    YeniRevizyonDialog,
    OnayRedDialog,
    CokluProjeDialog,
    DurumDegistirDialog,
    ManuelProjeGirisiDialog,
    RevizyonSecDialog,  # noqa: F401 (imported for tests and for backwards compatibility)
    YaziTuruSecDialog,  # noqa: F401 (imported for tests and for backwards compatibility)
    DosyadanCokluProjeDialog,
)
from widgets import WatermarkOverlay
from filters import AdvancedFilterManager
from AdvancedFilterDialog import AdvancedFilterDialog

# =============================================================================
# ANA PENCERE SINIFI
# =============================================================================

# Kategori ID'sini saklamak için özel rol
KATEGORI_ID_ROL = Qt.UserRole + 1


class AnaPencere(QMainWindow):
    # --- ÇÖKME DÜZELTMESİ (ADIM 1): Sinyale rev_id (int) eklendi ---
    _start_pdf_render = Signal(bytes, float, int)
    # New: signal to request rendering of a yazi (incoming letter) document
    _start_yazi_render = Signal(bytes, float, str)
    # Signal emitted when background update check finishes.
    _update_check_complete = Signal(object)
    _update_download_complete = Signal(object)

    def __init__(self, parent=None, db_dosyasi="projeler.db", db=None, auth_service=None):
        super().__init__(parent)
        self.secili_proje_id: Optional[int] = None
        self.tum_projeler: List[ProjeModel] = []
        resolved_db_path = getattr(db, "db_adi", db_dosyasi)
        self.current_db_file = os.path.abspath(resolved_db_path)  # Mutlak yol
        self.db = db if db is not None else ProjeTakipDB(self.current_db_file)
        self.logger = get_class_logger(self)
        # Read saved TOK theme variant from QSettings
        try:
            settings = QSettings(APP_NAME, APP_NAME)
            self._tok_variant = settings.value("ui/tok_variant", "light") or "light"
        except Exception:
            self._tok_variant = "light"
        # Lazy loading için private değişkenler (servisler ilk erişimde yüklenecek)
        self._controller = None
        self._document_service = None
        self._file_service = None
        self._preview_state_helper = None
        self._preview_render_service = None
        self._report_service = None
        self._excel_loader = None
        self._excel_loader_initialized = False  # None valid bir değer olduğu için ayrı flag
        self._update_check_in_progress = False
        self._update_download_in_progress = False

        # Initialize authentication service (login için gerekli, lazy yapılamaz)
        from services.auth_service import AuthService
        self.auth_service = auth_service if auth_service is not None else AuthService(self.db)

        # Otomatik yedekleme - uygulama açılışında
        self._acilista_yedek_al()

        # Cache mekanizması - sık kullanılan verileri önbelleğe al
        self._kategori_yolu_cache: Dict[int, str] = {}
        self._proje_detay_cache: Dict[int, ProjeModel] = {}
        self._cache_max_size = 500  # Maksimum cache boyutu (optimized: 100 → 500)

        self.kategori_items_map: Dict[int, QTreeWidgetItem] = {}
        self.istatistik_etiketleri = {}  # Initialize to prevent AttributeError

        self.filter_manager = AdvancedFilterManager(self.db)
        self.filter_manager.filter_changed.connect(self.on_filters_changed)
        # Guard flag used when we clear filters programmatically to avoid re-entrancy
        self._clearing_filters = False
        self._sadece_takipteki_revizyonlar = False

        # Otomatik kayıt mekanizması
        self._degisiklik_sayaci = 0
        self._son_otomatik_kayit = datetime.datetime.now()
        self._otomatik_kayit_esik = 10  # 10 değişiklikte bir kaydet
        # Default to 3 minutes = 180 seconds. Allow user override via QSettings: db/autosave_interval_sec
        try:
            settings = QSettings(APP_NAME, APP_NAME)
            self._otomatik_kayit_suresi = int(
                settings.value("db/autosave_interval_sec", 180)
            )
        except Exception:
            self._otomatik_kayit_suresi = 180  # fallback 3 minutes

        # Otomatik kayıt timer'ı
        self.otomatik_kayit_timer = QTimer()
        self.otomatik_kayit_timer.timeout.connect(self._otomatik_kayit_kontrol)
        self.otomatik_kayit_timer.start(self._otomatik_kayit_suresi * 1000)  # ms

        self.zoom_factor = 1.5
        self.MIN_ZOOM = 0.5
        self.MAX_ZOOM = 5.0
        self.ZOOM_STEP = 0.2

        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self._arama_kutusu_degisti)

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._trigger_preview_update)

        # Memory monitoring timer - interval uzatıldı ve daha hafif yapıldı
        self.mem_timer = QTimer(self)
        self.mem_timer.setInterval(15000)  # Optimized: 5s → 15s (daha az kaynak kullanımı)
        self.mem_timer.timeout.connect(self._update_memory_label)

        # Placeholder label, created in toolbar setup
        self.memory_label = None

        self.setup_ui()
        # Connect update-check signal
        try:
            self._update_check_complete.connect(self._on_update_check_complete)
        except Exception:
            pass
        try:
            self._update_download_complete.connect(self._on_update_download_complete)
        except Exception:
            pass

        # Configure auto-check-on-startup setting and queue a silent check if enabled
        try:
            settings = QSettings(APP_NAME, APP_NAME)
            auto_check = settings.value("updates/auto_check_on_startup", False)
            # Normalize to boolean (QSettings might return string)
            auto_check = True if str(auto_check).lower() in ("1", "true", "yes") else False
            if hasattr(self, "auto_check_update_action"):
                try:
                    self.auto_check_update_action.setChecked(auto_check)
                except Exception:
                    pass
            if auto_check:
                # Delay initial check slightly so UI finishes starting
                try:
                    QTimer.singleShot(2000, lambda: self.check_for_updates(silent=True))
                except Exception:
                    pass
        except Exception:
            pass
        # Delegate PDF worker setup to controller
        try:
            if getattr(self, "controller", None) and hasattr(
                self.controller, "setup_pdf_worker"
            ):
                self.controller.setup_pdf_worker()
            else:
                self.setup_pdf_worker()
        except Exception:
            pass
        # Proje yuklemesini ertele - UI once gorunur, sonra veri yuklenir
        QTimer.singleShot(0, self.projeleri_yukle)
        # Ensure we clean up workers and DB on app exit to avoid dangling QThreads
        try:
            app = QApplication.instance()
            if app:
                app.aboutToQuit.connect(self._on_app_about_to_quit)
        except Exception:
            pass

    def _on_app_about_to_quit(self):
        """Ensure that cleanup is invoked when the QApplication is about to quit."""
        try:
            # Disconnect signals to prevent race conditions during shutdown
            try:
                self._update_check_complete.disconnect(self._on_update_check_complete)
            except Exception:
                pass
            try:
                self._update_download_complete.disconnect(
                    self._on_update_download_complete
                )
            except Exception:
                pass
            # Ensure pending changes are committed before any cleanup/close
            try:
                if hasattr(self, "db") and hasattr(self.db, "otomatik_kaydet"):
                    self.db.otomatik_kaydet()
            except Exception:
                pass
            if getattr(self, "controller", None) and hasattr(
                self.controller, "cleanup_pdf_worker"
            ):
                self.controller.cleanup_pdf_worker()
            else:
                self.cleanup_pdf_worker()
        except Exception:
            pass
        try:
            if hasattr(self, "db") and hasattr(self.db, "cleanup_connections"):
                self.db.cleanup_connections()
        except Exception:
            pass

    # =========================================================================
    # LAZY LOADING PROPERTIES - Servisler ilk erişimde yüklenir (startup hızlandırma)
    # =========================================================================

    @property
    def controller(self):
        """Lazy loading for MainController - sadece gerektiğinde yüklenir."""
        if self._controller is None:
            try:
                from controllers.main_controller import MainController
                self._controller = MainController(self)
                self._controller.initialize()
                self.logger.debug("MainController lazy loaded")
            except Exception as e:
                self.logger.warning(f"MainController yüklenemedi: {e}")
                return None
        return self._controller

    @controller.setter
    def controller(self, value):
        """Controller setter for backward compatibility."""
        self._controller = value

    @property
    def file_service(self):
        """Lazy loading for FileService - sadece gerektiğinde yüklenir."""
        if self._file_service is None:
            try:
                from services.file_service import FileService
                self._file_service = FileService(parent=self)
                self.logger.debug("FileService lazy loaded")
            except Exception as e:
                self.logger.warning(f"FileService yüklenemedi: {e}")
                return None
        return self._file_service

    @file_service.setter
    def file_service(self, value):
        """FileService setter for backward compatibility."""
        self._file_service = value

    @property
    def document_service(self):
        """Lazy loading for DocumentService - sadece gerektiğinde yüklenir."""
        if self._document_service is None:
            try:
                from services.document_service import DocumentService

                file_service = self.file_service
                if file_service is None:
                    self.logger.warning("DocumentService için FileService yüklenemedi")
                    return None

                self._document_service = DocumentService(
                    db=self.db,
                    file_service=file_service,
                    parent=self,
                )
                self.logger.debug("DocumentService lazy loaded")
            except Exception as e:
                self.logger.warning(f"DocumentService yüklenemedi: {e}")
                return None
        return self._document_service

    @document_service.setter
    def document_service(self, value):
        """DocumentService setter for backward compatibility."""
        self._document_service = value

    @property
    def report_service(self):
        """Lazy loading for ReportService - sadece gerektiğinde yüklenir."""
        if self._report_service is None:
            try:
                from services.report_service import ReportService
                self._report_service = ReportService(db=self.db, parent=self)
                self.logger.debug("ReportService lazy loaded")
            except Exception as e:
                self.logger.warning(f"ReportService yüklenemedi: {e}")
                return None
        return self._report_service

    @report_service.setter
    def report_service(self, value):
        """ReportService setter for backward compatibility."""
        self._report_service = value

    @property
    def preview_state(self):
        """Lazy loading for PreviewStateHelper - sadece gerektiğinde yüklenir."""
        if self._preview_state_helper is None:
            try:
                from ui.preview_state_helper import PreviewStateHelper

                self._preview_state_helper = PreviewStateHelper(self)
            except Exception as e:
                self.logger.warning(f"PreviewStateHelper yüklenemedi: {e}")
                return None
        return self._preview_state_helper

    @preview_state.setter
    def preview_state(self, value):
        """PreviewStateHelper setter for backward compatibility."""
        self._preview_state_helper = value

    @property
    def preview_render_service(self):
        """Lazy loading for PreviewRenderService - sadece gerektiğinde yüklenir."""
        if self._preview_render_service is None:
            try:
                from services.preview_render_service import PreviewRenderService

                self._preview_render_service = PreviewRenderService(db=self.db)
            except Exception as e:
                self.logger.warning(f"PreviewRenderService yüklenemedi: {e}")
                return None
        return self._preview_render_service

    @preview_render_service.setter
    def preview_render_service(self, value):
        """PreviewRenderService setter for backward compatibility."""
        self._preview_render_service = value

    @property
    def excel_loader(self):
        """Lazy loading for ExcelLoaderService - sadece gerektiğinde yüklenir."""
        if not self._excel_loader_initialized:
            self._excel_loader_initialized = True
            try:
                from services.excel_loader_service import ExcelLoaderService
                excel_path = os.path.join(os.path.dirname(self.current_db_file), "proje_listesi.xlsx")
                self._excel_loader = ExcelLoaderService(excel_path)
                self.logger.debug(f"ExcelLoaderService lazy loaded: {excel_path}")
            except Exception as e:
                self._excel_loader = None
                self.logger.warning(f"ExcelLoaderService yüklenemedi: {e}")
        return self._excel_loader

    @excel_loader.setter
    def excel_loader(self, value):
        """ExcelLoader setter for backward compatibility."""
        self._excel_loader = value
        self._excel_loader_initialized = True

    def closeEvent(self, event):
        """Ensure worker threads and DB connections are properly cleaned on window close."""
        try:
            # Stop timers to avoid racing signals while closing
            try:
                if hasattr(self, "preview_timer"):
                    self.preview_timer.stop()
            except Exception:
                pass
            try:
                if hasattr(self, "otomatik_kayit_timer"):
                    self.otomatik_kayit_timer.stop()
            except Exception:
                pass
            try:
                if hasattr(self, "mem_timer"):
                    self.mem_timer.stop()
            except Exception:
                pass

            # Dokuman cache temizle
            try:
                if self.preview_render_service:
                    self.preview_render_service.clear_cache()
            except Exception:
                pass

            # Update thread'ini bekle
            try:
                if hasattr(self, "_update_check_thread") and self._update_check_thread is not None:
                    self._update_check_thread.join(timeout=2.0)
            except Exception:
                pass
            try:
                if hasattr(self, "_update_download_thread") and self._update_download_thread is not None:
                    self._update_download_thread.join(timeout=2.0)
            except Exception:
                pass

            # Backup thread'ini bekle
            try:
                if hasattr(self, "_backup_thread") and self._backup_thread is not None:
                    self._backup_thread.join(timeout=5.0)
            except Exception:
                pass

            # Cleanup PDF worker (controller or local)
            try:
                if getattr(self, "controller", None) and hasattr(
                    self.controller, "cleanup_pdf_worker"
                ):
                    self.controller.cleanup_pdf_worker()
                elif hasattr(self, "cleanup_pdf_worker"):
                    self.cleanup_pdf_worker()
            except Exception:
                pass

            # Cleanup DB connections
            try:
                # Ensure one final commit before closing
                try:
                    if hasattr(self, "db") and hasattr(self.db, "close"):
                        self.db.close()
                    elif hasattr(self, "db") and hasattr(self.db, "otomatik_kaydet"):
                        self.db.otomatik_kaydet()
                except Exception:
                    pass
                if (
                    hasattr(self, "db")
                    and hasattr(self.db, "cleanup_connections")
                    and not hasattr(self.db, "close")
                ):
                    self.db.cleanup_connections()
            except Exception:
                pass
        except Exception:
            # Ensure close still happens even if cleanup had errors
            pass
        # Call base class closeEvent to allow default handling
        try:
            super().closeEvent(event)
        except Exception:
            # If any issue with the event handling, just accept
            try:
                event.accept()
            except Exception:
                pass

    def _otomatik_kayit_kontrol(self):
        """Periyodik olarak çağrılan otomatik kayıt kontrolü.
        Belirlenen eşik ya da süre aşıldığında veritabanına commit yapar,
        cache'leri temizler ve sayacı sıfırlar.
        """
        try:
            if not hasattr(self, "db"):
                return
            if not self.db.degisiklik_var_mi():
                return

            now = datetime.datetime.now()
            elapsed = (now - getattr(self, "_son_otomatik_kayit", now)).total_seconds()
            change_count = getattr(self, "_degisiklik_sayaci", 0)
            threshold = getattr(self, "_otomatik_kayit_esik", 10)
            interval = getattr(self, "_otomatik_kayit_suresi", 30)

            # Eğer eşik veya süre aşıldıysa kaydet
            if change_count >= threshold or elapsed >= interval:
                try:
                    # Centralize commit call to DB method
                    try:
                        saved = self.db.otomatik_kaydet()
                    except Exception:
                        saved = 0
                    # Reset UI level counter
                    try:
                        self._degisiklik_sayaci = 0
                    except Exception:
                        pass
                    self._son_otomatik_kayit = now

                    # Clear caches to ensure fresh reads
                    try:
                        self._proje_detay_cache.clear()
                    except Exception:
                        pass
                    try:
                        self._kategori_yolu_cache.clear()
                    except Exception:
                        pass

                    self.logger.info(
                        f"✅ Otomatik kayıt: {saved} değişiklik kaydedildi ve cache temizlendi"
                    )
                    # Inform user through status bar (short) about an autosave
                    try:
                        if getattr(self, "_status", None) and saved > 0:
                            self._status.showMessage("Otomatik kayıt yapıldı", 3000)
                    except Exception:
                        pass
                    # Update small UI element so user sees status
                    try:
                        self._update_memory_label()
                    except Exception:
                        pass
                except Exception as e:
                    self.logger.error(f"Otomatik kayıtta hata: {e}", exc_info=True)
        except Exception:
            pass

    def _cache_temizle(self):
        """Clear in-memory caches used by the UI to avoid stale data after DB reset."""
        try:
            if hasattr(self, "_proje_detay_cache") and isinstance(
                self._proje_detay_cache, dict
            ):
                self._proje_detay_cache.clear()
        except Exception:
            pass
        try:
            if hasattr(self, "_kategori_yolu_cache") and isinstance(
                self._kategori_yolu_cache, dict
            ):
                self._kategori_yolu_cache.clear()
        except Exception:
            pass
        try:
            if self.preview_render_service:
                self.preview_render_service.clear_cache()
        except Exception:
            pass
        try:
            self._degisiklik_sayaci = 0
        except Exception:
            pass
        try:
            self.db.degisiklikleri_sifirla()
        except Exception:
            pass
        try:
            # Force an action state refresh and UI updates
            self._update_action_states()
        except Exception:
            pass

    def _invalidate_filter_cache_and_reload(self, keep_project_id: Optional[int] = None, keep_rev_id: Optional[int] = None):
        """Clear filter cache and re-load projects to ensure UI doesn't show stale results."""
        try:
            if getattr(self, "filter_manager", None):
                try:
                    self.filter_manager.clear_cache()
                except Exception:
                    pass
            # Optionally preserve selection: set secili_proje_id so projeleri_yukle can reselect
            # Determine which project/revision to preserve - use provided keep values, else fallback to current selections
            try:
                preserve_proj = keep_project_id if keep_project_id is not None else getattr(self, 'secili_proje_id', None)
                # If keep_rev_id not provided, attempt to get current selected rev id from the UI
                if keep_rev_id is not None:
                    preserve_rev = keep_rev_id
                else:
                    try:
                        item = self._get_secili_revizyon_item()
                        preserve_rev = item.data(0, Qt.UserRole).id if item else None
                    except Exception:
                        preserve_rev = None
                if preserve_proj is not None:
                    self.secili_proje_id = preserve_proj
            except Exception:
                preserve_proj = getattr(self, 'secili_proje_id', None)
                preserve_rev = None
            # Re-load projects which will reapply filters if any are active
            try:
                # If we have a specific project to keep but filters may exclude it,
                # we'll fetch filtered projects and append the preserved project to ensure the UI keeps focus.
                projects = None
                try:
                    if getattr(self, 'filter_manager', None) and len(getattr(self.filter_manager, 'active_filters', [])):
                        projects = self.filter_manager.get_filtered_projects()
                    else:
                        projects = self.db.projeleri_listele()
                except Exception:
                    projects = self.db.projeleri_listele()

                # If we need to preserve a project that is not in the list, fetch it and append.
                try:
                    if preserve_proj is not None and all(getattr(p, 'id', None) != preserve_proj for p in (projects or [])):
                        # Attempt to find the project in the full project list and append it if found
                        try:
                            all_projects = self.db.projeleri_listele()
                        except Exception:
                            all_projects = []
                        for ap in all_projects:
                            if getattr(ap, 'id', None) == preserve_proj:
                                projects = list(projects or [])
                                projects.insert(0, ap)
                                break
                except Exception:
                    pass

                # Display projects via existing helper which applies search box filter on top
                try:
                    self.display_filtered_projects(projects or [])
                except Exception:
                    self.projeleri_yukle()
            except Exception:
                pass
            # If rev_id is provided, try to reselect revision after project reload
            try:
                self.logger.debug(f"_invalidate_filter_cache_and_reload called. keep_project_id={keep_project_id}, keep_rev_id={keep_rev_id}, preserve_proj={preserve_proj}, preserve_rev={preserve_rev}")
                if preserve_proj is not None and (keep_rev_id is not None or preserve_rev is not None):
                    self.logger.debug(f"_invalidate_filter_cache_and_reload: will reload revisions for project {preserve_proj}")
                    self.revizyonlari_yukle(preserve_proj)
                    # Prefer explicit keep_rev_id when given, fallback to preserved rev
                    rid = keep_rev_id if keep_rev_id is not None else preserve_rev
                    if rid is not None:
                        self.logger.debug(f"_invalidate_filter_cache_and_reload: attempting _select_revizyon_by_id({rid})")
                        self._select_revizyon_by_id(rid)
            except Exception:
                pass
        except Exception:
            pass

    def projeleri_yukle(self):
        """Load projects list from controller or database and update UI.
        This is a minimal adapter in refactored code to ensure older call sites work.
        """
        try:
            if getattr(self, "controller", None):
                projects = self.controller.get_projects()
            else:
                projects = self.db.projeleri_listele()
            # normalize to list
            self.tum_projeler = projects or []
            # Clear filter cache to avoid returning stale cached results after DB changes
            try:
                if getattr(self, "filter_manager", None):
                    self.filter_manager.clear_cache()
            except Exception:
                pass
            # If any advanced filters are active, re-apply them instead of blindly populating all projects
            if getattr(self, "filter_manager", None) and len(
                getattr(self.filter_manager, "active_filters", [])
            ):
                try:
                    self.apply_filters()
                except Exception as e:
                    self.logger.error(
                        f"apply_filters sırasında hata: {e}", exc_info=True
                    )
            else:
                # Update UI - populate the list and category tree
                try:
                    # Use UI population helper to render the loaded projects
                    self._populate_projects_ui(self.tum_projeler)
                    self.logger.info(
                        f"Projeler başarıyla yüklendi (Toplam: {len(self.tum_projeler)})"
                    )
                except Exception as e_inner:
                    self.logger.error(
                        f"projeleri_yukle UI update hata: {e_inner}", exc_info=True
                    )
                    # Fallback: if display_filtered_projects is not present, try to set items directly
                    try:
                        self.proje_listesi_widget.clear()
                    except Exception:
                        pass
        except Exception as e:
            self.logger.error(f"projeleri_yukle hata: {e}", exc_info=True)

    def _acilista_yedek_al(self):
        """Uygulama açılışında arka planda otomatik yedek al"""
        import threading

        db_path = self.current_db_file
        backup_service = self.db.backup_service

        def _backup_worker():
            try:
                src_conn = self.db.create_independent_connection(db_path)
                try:
                    yedek_dosya = backup_service.create_backup(src_conn, "Acilis")
                    if yedek_dosya:
                        self.logger.info(f"Açılış yedeği alındı: {yedek_dosya}")
                finally:
                    src_conn.close()
            except Exception as e:
                self.logger.warning(f"Açılış yedeği alınamadı: {e}")

        self._backup_thread = threading.Thread(target=_backup_worker, daemon=True)
        self._backup_thread.start()

    def _update_memory_label(self):
        """Update the memory usage labels - optimize edilmiş, UI thread'i bloklamaz"""
        text = "Bellek: n/a"
        try:
            # Önce tracemalloc'u dene (daha hafif)
            import tracemalloc

            if tracemalloc.is_tracing():
                current, _peak = tracemalloc.get_traced_memory()
                text = f"Bellek: {current/1024/1024:.1f} MB"
            else:
                # tracemalloc yoksa psutil'i dene
                try:
                    import psutil

                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    text = f"Bellek: {memory_mb:.1f} MB"
                except ImportError:
                    # psutil mevcut değil, basit alternatif kullan
                    import resource

                    try:
                        memory_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                        # Linux'ta kb, Windows/Mac'te bytes olabilir
                        if sys.platform == "darwin":  # macOS
                            memory_mb = memory_kb / 1024 / 1024
                        elif sys.platform == "linux":
                            memory_mb = memory_kb / 1024
                        else:  # Windows
                            memory_mb = memory_kb / 1024 / 1024
                        text = f"Bellek: {memory_mb:.1f} MB"
                    except Exception:
                        text = "Bellek: n/a"
        except Exception:
            text = "Bellek: n/a"

        # Update labels - hata durumunda UI'ı bloklamadan atla
        try:
            memory_label = getattr(self, "status_mem_label", None) or getattr(
                self, "memory_label", None
            )
            if memory_label:
                # Otomatik kayıt durumunu da göster
                if hasattr(self, "_degisiklik_sayaci") and self._degisiklik_sayaci > 0:
                    memory_label.setText(
                        f"{text} | ⚠️ {self._degisiklik_sayaci} değişiklik"
                    )
                else:
                    memory_label.setText(text)
        except Exception:
            pass

    def _restore_ui_state(self):
        """Restore saved window geometry, splitter sizes, and tab indexes from QSettings."""
        s = QSettings(APP_NAME, APP_NAME)
        try:
            g = s.value("window/geometry")
            if g is not None:
                self.restoreGeometry(g)
            st = s.value("window/state")
            if st is not None:
                self.restoreState(st)
            sizes_main = s.value("splitter/main")
            if sizes_main:
                self.ana_bolunmus_pencere.setSizes([int(x) for x in sizes_main])
            sizes_right = s.value("splitter/right")
            if sizes_right:
                self.sag_dikey_bolucu.setSizes([int(x) for x in sizes_right])
            tab_index = s.value("tabs/index")
            if tab_index is not None:
                self.sekme_widget.setCurrentIndex(int(tab_index))
        except Exception as e:
            self.logger.debug(f"UI state restore failed: {e}")

    def _save_ui_state(self):
        s = QSettings(APP_NAME, APP_NAME)
        try:
            s.setValue("window/geometry", self.saveGeometry())
            s.setValue("window/state", self.saveState())
            s.setValue("splitter/main", self.ana_bolunmus_pencere.sizes())
            s.setValue("splitter/right", self.sag_dikey_bolucu.sizes())
            s.setValue("tabs/index", self.sekme_widget.currentIndex())
        except Exception as e:
            self.logger.debug(f"UI state save failed: {e}")

    def setup_ui(self):
        # Delegate UI construction to the ui module; keep only wiring/menus here.
        from ui.main_window_ui import setup_ui as _ui_setup

        _ui_setup(self)
        # Status bar for professional app feedback
        try:
            self._status = self.statusBar()
            self.status_mem_label = QLabel("Bellek: -")
            self._status.addPermanentWidget(self.status_mem_label)
            self.memory_label = self.status_mem_label
            self._update_memory_label()
        except Exception:
            self._status = None
            self.status_mem_label = None
            self.memory_label = None
        # Ensure we have menu and toolbar setup (UI module already performs this but keep idempotent)
        try:
            self._setup_menubar()
        except Exception:
            pass
        try:
            self._setup_toolbar()
        except Exception:
            pass
        # The UI module already configured splitters and widgets; just ensure event wiring below.
        # Restore UI state if available
        try:
            self._restore_ui_state()
        except Exception as e:
            self.logger.warning(f"UI durumu geri yüklenemedi: {e}")

        # Watermark overlay (center, thin)
        try:
            if ENABLE_WATERMARK:
                self._watermark = WatermarkOverlay(
                    parent=self.ana_widget,
                    image_path=WATERMARK_IMAGE_PATH,
                    opacity=WATERMARK_OPACITY,
                )
                self._watermark.setGeometry(self.ana_widget.rect())
                self._watermark.raise_()
        except Exception as e:
            # Watermark failing should not break the UI
            self.logger.warning(f"Filigran yüklenemedi: {e}")

        self.proje_agaci_widget.projeTasindi.connect(self.on_proje_tasindi)
        self.revizyon_agaci.itemSelectionChanged.connect(
            self._on_revizyon_selection_changed
        )
        self.revizyon_agaci.setContextMenuPolicy(Qt.CustomContextMenu)
        self.revizyon_agaci.customContextMenuRequested.connect(
            self._revizyon_context_menu
        )
        self.sekme_widget.currentChanged.connect(self._on_ana_sekme_degisti)
        self.proje_agaci_widget.customContextMenuRequested.connect(
            self._kategori_gorunumu_context_menu
        )
        # Event filter'ı sadece gerekli widget'lara uygula (tüm pencere yerine)
        self.proje_listesi_widget.installEventFilter(self)
        self.proje_agaci_widget.installEventFilter(self)
        self.revizyon_agaci.installEventFilter(self)

        # Pencere başlığını DB dosyası ile güncelle
        db_name = os.path.basename(self.current_db_file)
        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION} - [{db_name}]")

        # Son kullanılan dosyayı kaydet
        self._son_kullanilan_dosya_kaydet()
        # Initialize action states
        try:
            self._update_action_states()
        except Exception:
            pass

    def _reset_layout(self):
        """Reset UI layout: restore settings and re-apply finalize UI adjustments."""
        try:
            self._restore_ui_state()
            from ui.main_window_ui import _finalize_ui

            _finalize_ui(self)
        except Exception as e:
            self.logger.warning(f"Layout reset failed: {e}")

    def _setup_toolbar(self):
        # middleware: call UI helper
        from ui.main_window_ui import _setup_toolbar as _ui_setup_toolbar

        return _ui_setup_toolbar(self)

    def _toggle_auto_update_check(self, checked: bool):
        """Persist the user's preference for automatic update checks on startup."""
        try:
            settings = QSettings(APP_NAME, APP_NAME)
            settings.setValue("updates/auto_check_on_startup", bool(checked))
            # If they enabled it, schedule an immediate silent check
            if checked:
                try:
                    QTimer.singleShot(2000, lambda: self.check_for_updates(silent=True))
                except Exception:
                    pass
        except Exception as e:
            self.logger.warning(f"Auto-update toggle failed: {e}")

    def _get_downloads_dir(self) -> str:
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        return downloads_dir

    def _open_release_page(self, release_url: Optional[str] = None) -> bool:
        return QDesktopServices.openUrl(QUrl(release_url or UPDATE_RELEASE_PAGE_URL))

    def _set_update_action_enabled(self, enabled: bool):
        try:
            if hasattr(self, "update_action") and self.update_action is not None:
                self.update_action.setEnabled(enabled)
        except Exception:
            pass

    def _download_release_asset(self, release: Dict, asset: Dict, release_url: str):
        """Download the selected release asset in the background."""
        try:
            if self._update_download_in_progress:
                if getattr(self, "_status", None):
                    self._status.showMessage(
                        "Zaten bir güncelleme indirme işlemi sürüyor.", 4000
                    )
                return

            from PySide6.QtWidgets import QFileDialog
            dest_dir = QFileDialog.getExistingDirectory(
                self,
                "Güncelleme İndirilecek Klasörü Seçin",
                self._get_downloads_dir(),
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if not dest_dir:
                if getattr(self, "_status", None):
                    self._status.showMessage("İndirme işlemi iptal edildi.", 4000)
                return

            self._update_download_in_progress = True
            self._set_update_action_enabled(False)
            asset_name = asset.get("name", "güncelleme paketi")
            if getattr(self, "_status", None):
                self._status.showMessage(f"Güncelleme indiriliyor: {asset_name}", 5000)

            def _worker():
                result = {"asset_name": asset_name, "release_url": release_url}
                try:
                    from services.update_client import download_asset, verify_downloaded_asset

                    path = download_asset(asset, dest_dir)
                    if path:
                        verification = verify_downloaded_asset(release, asset, path)
                        if verification.get("status") == "verified":
                            result.update(
                                {
                                    "status": "downloaded",
                                    "path": path,
                                    "checksum_asset": verification.get(
                                        "checksum_asset", ""
                                    ),
                                }
                            )
                        else:
                            try:
                                if os.path.exists(path):
                                    os.remove(path)
                            except Exception:
                                pass
                            result.update(
                                {
                                    "status": "error",
                                    "error": verification.get(
                                        "error",
                                        "İndirilen dosya doğrulanamadı.",
                                    ),
                                }
                            )
                    else:
                        result.update(
                            {"status": "error", "error": "Dosya indirilemedi."}
                        )
                except Exception as e:
                    result.update({"status": "error", "error": str(e)})

                try:
                    self._update_download_complete.emit(result)
                except Exception:
                    pass

            import threading

            t = threading.Thread(target=_worker, daemon=True)
            t.start()
            self._update_download_thread = t
        except Exception as e:
            self._update_download_in_progress = False
            if not self._update_check_in_progress:
                self._set_update_action_enabled(True)
            self.logger.error(f"Güncelleme indirme başlatılamadı: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "İndirme Başlatılamadı",
                f"Güncelleme indirmesi başlatılamadı:\n{e}",
            )

    def check_for_updates(self, silent: bool = False):
        """Trigger a background GitHub Release check."""
        try:
            if self._update_check_in_progress:
                if not silent and getattr(self, "_status", None):
                    self._status.showMessage(
                        "Güncelleme kontrolü zaten devam ediyor.", 4000
                    )
                return

            self._update_check_in_progress = True
            self._set_update_action_enabled(False)
            if getattr(self, "_status", None):
                self._status.showMessage("Güncellemeler kontrol ediliyor...", 4000)

            def _worker():
                result = {"silent": bool(silent)}
                try:
                    from services.update_client import get_latest_release_info

                    result.update(
                        get_latest_release_info(
                            UPDATE_REPO_OWNER,
                            UPDATE_REPO_NAME,
                            APP_VERSION,
                            UPDATE_RELEASE_ASSET_PATTERN,
                            preferred_extensions=UPDATE_RELEASE_ASSET_EXTENSIONS,
                        )
                    )
                except Exception as e:
                    result.update(
                        {
                            "status": "error",
                            "error_type": "unknown",
                            "error": str(e),
                        }
                    )

                try:
                    self._update_check_complete.emit(result)
                except Exception:
                    pass

            import threading

            t = threading.Thread(target=_worker, daemon=True)
            t.start()
            self._update_check_thread = t
        except Exception as e:
            try:
                self._update_check_in_progress = False
                if not self._update_download_in_progress:
                    self._set_update_action_enabled(True)
                self.logger.error(f"Güncelleme kontrolü başlatılamadı: {e}", exc_info=True)
            except Exception:
                pass

    def _on_update_check_complete(self, result: object):
        """Handle the result of the background update check."""
        try:
            payload = result if isinstance(result, dict) else {}
            silent = bool(payload.get("silent"))
            status = payload.get("status")
            latest_tag = payload.get("latest_tag") or payload.get("latest_version") or ""
            release = payload.get("release") or {}
            release_url = payload.get("release_url") or UPDATE_RELEASE_PAGE_URL
            asset = payload.get("asset")
            self._update_check_in_progress = False
            if not self._update_download_in_progress:
                self._set_update_action_enabled(True)

            if status == "up_to_date":
                if getattr(self, "_status", None):
                    self._status.showMessage("Güncelleme bulunamadı.", 3000)
                if not silent:
                    QMessageBox.information(
                        self, "Güncelleme", "Yeni sürüm bulunamadı."
                    )
                return

            if status == "update_available":
                if getattr(self, "_status", None):
                    self._status.showMessage(
                        f"Yeni sürüm bulundu: {latest_tag or 'güncel release'}", 6000
                    )
                if silent:
                    return

                notes = (release.get("body") or "").strip()
                published_at = release.get("published_at") or "-"
                asset_name = asset.get("name") if isinstance(asset, dict) else "-"

                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("Güncelleme Bulundu")
                msg.setText(f"Yeni sürüm bulundu: {latest_tag}")
                msg.setInformativeText(
                    "Yeni sürümü indirebilir veya release sayfasını açabilirsiniz."
                )
                msg.setDetailedText(
                    f"Sürüm: {latest_tag}\n"
                    f"Yayın Tarihi: {published_at}\n"
                    f"Dosya: {asset_name}\n"
                    f"Release URL: {release_url}\n\n"
                    f"Release Notları:\n{notes or 'Release notu bulunamadı.'}"
                )
                download_btn = msg.addButton("İndir", QMessageBox.AcceptRole)
                open_btn = msg.addButton("Release Sayfasını Aç", QMessageBox.ActionRole)
                msg.addButton("Sonra", QMessageBox.RejectRole)
                msg.exec()

                clicked = msg.clickedButton()
                if clicked == download_btn and isinstance(asset, dict):
                    self._download_release_asset(release, asset, release_url)
                elif clicked == open_btn and not self._open_release_page(release_url):
                    QMessageBox.warning(
                        self,
                        "Bağlantı Açılamadı",
                        f"Release sayfası açılamadı:\n{release_url}",
                    )
                return

            if status == "asset_missing":
                if getattr(self, "_status", None):
                    self._status.showMessage(
                        "Yeni sürüm bulundu ancak indirilebilir dosya bulunamadı.",
                        5000,
                    )
                if silent:
                    return
                reply = QMessageBox.question(
                    self,
                    "Güncelleme Bulundu",
                    "Yeni sürüm bulundu ancak uygun indirme dosyası release içinde bulunamadı.\n"
                    "Release sayfasını açmak ister misiniz?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if reply == QMessageBox.Yes and not self._open_release_page(release_url):
                    QMessageBox.warning(
                        self,
                        "Bağlantı Açılamadı",
                        f"Release sayfası açılamadı:\n{release_url}",
                    )
                return

            if status == "asset_unverified":
                if getattr(self, "_status", None):
                    self._status.showMessage(
                        "Yeni sürüm bulundu ancak checksum doğrulaması yapılamıyor.",
                        5000,
                    )
                if not silent:
                    QMessageBox.warning(
                        self,
                        "Güncelleme Doğrulanamadı",
                        "Yeni sürüm bulundu ancak release içinde doğrulama için checksum dosyası yok.\n"
                        "Doğrudan indirme kapatıldı. Lütfen release sayfasından paketi manuel doğrulayın.",
                    )
                return

            error_text = payload.get("error") or "Bilinmeyen hata"
            error_type = payload.get("error_type") or "unknown"
            if getattr(self, "_status", None):
                self._status.showMessage("Güncelleme kontrolü başarısız.", 5000)
            if not silent:
                if error_type == "network":
                    message = f"Ağ bağlantısı kurulamadı.\n\nDetay: {error_text}"
                elif error_type == "http" and "404" in str(error_text):
                    message = (
                        "Henüz yayınlanmış bir güncelleme bulunamadı.\n\n"
                        "Bu sürüm zaten en güncel halde olabilir veya "
                        "henüz yeni bir release yayınlanmamış olabilir.\n\n"
                        f"Detay: {error_text}"
                    )
                elif error_type == "http":
                    message = f"GitHub release bilgisi alınamadı.\n\nDetay: {error_text}"
                else:
                    message = f"Güncelleme kontrolü sırasında hata oluştu.\n\nDetay: {error_text}"
                QMessageBox.warning(
                    self,
                    "Güncelleme Kontrolü Başarısız",
                    message,
                )
        except Exception as e:
            try:
                self._update_check_in_progress = False
                if not self._update_download_in_progress:
                    self._set_update_action_enabled(True)
                self.logger.error(f"_on_update_check_complete hata: {e}", exc_info=True)
            except Exception:
                pass

    def _on_update_download_complete(self, result: object):
        """Show the user the outcome of a completed update download."""
        try:
            payload = result if isinstance(result, dict) else {}
            self._update_download_in_progress = False
            if not self._update_check_in_progress:
                self._set_update_action_enabled(True)
            if payload.get("status") == "downloaded":
                path = payload.get("path", "")
                if getattr(self, "_status", None):
                    self._status.showMessage("Güncelleme indirildi.", 5000)
                QMessageBox.information(
                    self,
                    "Güncelleme İndirildi",
                    "Güncelleme dosyası indirildi.\n\n"
                    f"Konum:\n{path}\n\n"
                    f"Doğrulama: {payload.get('checksum_asset', 'checksum dosyası')}\n\n"
                    "Kurulumu bu dosya üzerinden manuel olarak başlatabilirsiniz.",
                )
                return

            if getattr(self, "_status", None):
                self._status.showMessage("Güncelleme indirilemedi.", 5000)
            QMessageBox.warning(
                self,
                "İndirme Başarısız",
                "Güncelleme dosyası indirilemedi.\n\n"
                f"Detay: {payload.get('error', 'Bilinmeyen hata')}",
            )
        except Exception as e:
            try:
                self._update_download_in_progress = False
                if not self._update_check_in_progress:
                    self._set_update_action_enabled(True)
                self.logger.error(
                    f"_on_update_download_complete hata: {e}", exc_info=True
                )
            except Exception:
                pass

    def _setup_projeler_panel(self):
        from ui.panels.project_panel import ProjectPanel

        self.project_panel = ProjectPanel()
        self.project_panel.project_selected.connect(self.on_project_selected_from_panel)
        self.project_panel.project_moved.connect(self.on_proje_tasindi)

        # Connect filter signals
        self.project_panel.advanced_filter_clicked.connect(self.show_advanced_filters)
        self.project_panel.clear_filter_clicked.connect(self.clear_filters)

        # Compatibility aliases for existing code
        self.proje_listesi_widget = self.project_panel.proje_listesi_widget
        self.proje_agaci_widget = self.project_panel.proje_agaci_widget
        self.arama_kutusu = self.project_panel.arama_kutusu
        self.filter_indicator = self.project_panel.filter_indicator
        self.arama_kutusu.textChanged.connect(self._on_search_text_changed)

        return self.project_panel

    def _setup_rapor_paneli(self):
        from ui.panels.report_panel import ReportPanel

        self.report_panel = ReportPanel()
        self.rapor_tablosu = self.report_panel.rapor_tablosu  # Compatibility
        return self.report_panel

    def _setup_revizyonlar_panel(self):
        from ui.panels.revision_panel import RevisionPanel
        from PySide6.QtWidgets import QSplitter, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea
        from PySide6.QtCore import Qt

        self.revision_panel = RevisionPanel()
        self.revision_panel.letter_clicked.connect(
            self.on_letter_clicked
        )
        self.revision_panel.revision_double_clicked.connect(
            self._open_revision_document
        )
        self.revision_panel.view_letter_requested.connect(
            self._on_view_letter_from_revision
        )

        # Compatibility aliases
        self.revizyon_agaci = self.revision_panel.revizyon_agaci

        # ---- Letter preview panel (below revision tree) ----
        self.yazi_onizleme_panel = QWidget()
        yazi_layout = QVBoxLayout(self.yazi_onizleme_panel)
        yazi_layout.setContentsMargins(0, 4, 0, 0)
        yazi_layout.setSpacing(4)

        yazi_baslik = QLabel("<b>📬 Yazı Ön İzleme</b>")
        yazi_baslik.setStyleSheet("font-size: 11pt; color: #212529;")
        yazi_layout.addWidget(yazi_baslik)

        self.yazi_onizleme_etiketi = QLabel("Revizyona ait yazı ön izlemesi burada görünür.")
        self.yazi_onizleme_etiketi.setAlignment(Qt.AlignCenter)
        self.yazi_onizleme_etiketi.setWordWrap(True)
        self.yazi_onizleme_etiketi.setStyleSheet("color: #777; font-size: 10pt;")

        self.yazi_onizleme_scroll = QScrollArea()
        self.yazi_onizleme_scroll.setWidget(self.yazi_onizleme_etiketi)
        self.yazi_onizleme_scroll.setWidgetResizable(True)
        yazi_layout.addWidget(self.yazi_onizleme_scroll)

        self.yazi_ac_btn = QPushButton("📄 Yazıyı Tam Ekran Aç")
        self.yazi_ac_btn.setEnabled(False)
        self.yazi_ac_btn.setFixedHeight(30)
        self.yazi_ac_btn.setCursor(Qt.PointingHandCursor)
        self.yazi_ac_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff;
                color: #2f3542;
                border: 1px solid #d9dee7;
                border-radius: 8px;
                padding: 4px 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #eaf4ff;
                border-color: #6baed6;
            }
            QPushButton:pressed {
                background-color: #d0e8fb;
            }
            QPushButton:disabled {
                background-color: #f4f6f9;
                color: #9aa3b2;
                border-color: #e6e9ef;
            }
            """
        )
        self.yazi_ac_btn.clicked.connect(self._on_yazi_ac_btn_clicked)
        yazi_layout.addWidget(self.yazi_ac_btn)

        # Store references for use in the open handler
        self._current_yazi_payload = None

        # Wrap in vertical splitter: revision tree (top, larger) + letter preview (bottom)
        rev_splitter = QSplitter(Qt.Vertical)
        rev_splitter.addWidget(self.revision_panel)
        rev_splitter.addWidget(self.yazi_onizleme_panel)
        rev_splitter.setSizes([550, 250])
        rev_splitter.setCollapsible(1, True)

        return rev_splitter


    def _setup_detaylar_panel(self):
        from ui.panels.detail_panel import DetailPanel

        self.detail_panel = DetailPanel()
        self.detay_etiketleri = self.detail_panel.detay_etiketleri  # Compatibility
        return self.detail_panel

    def _setup_onizleme_panel(self):
        from ui.panels.preview_panel import PreviewPanel

        self.preview_panel = PreviewPanel()
        self.preview_panel.view_document_clicked.connect(
            self._goruntule_dokuman_wrapper
        )

        # Compatibility aliases
        self.onizleme_etiketi = self.preview_panel.onizleme_etiketi
        self.goruntule_btn = self.preview_panel.goruntule_btn

        return self.preview_panel

    def _add_menu_action(self, menu, icon, text, callback, shortcut=""):
        """Helper method to create and add a menu action."""
        from ui.main_window_ui import _add_menu_action as _ui_add_menu_action

        return _ui_add_menu_action(self, menu, icon, text, callback, shortcut)

    def _setup_menubar(self):
        from ui.main_window_ui import _setup_menubar as _ui_setup_menubar

        return _ui_setup_menubar(self)

    def show_user_guide_tab(self):
        from ui.main_window_ui import show_user_guide_tab as _ui_show_guide

        return _ui_show_guide(self)

        # original method body moved to ui/main_window_ui.show_user_guide_tab

    def show_version_info(self):
        """Sürüm bilgisi ve katkı mesajını göster."""
        try:
            mesaj = (
                f"{APP_NAME} {APP_VERSION}\n\n"
                "ALPER BERKAN YILMAZ VE ÖMER ERBAŞ’IN katkıları ile hazırlanmıştır."
            )
            QMessageBox.information(self, "Sürüm Bilgisi", mesaj)
        except Exception as e:
            self.logger.error(f"Sürüm bilgisi gösterilemedi: {e}")

    def focus_search(self):
        """Place focus into the main search box (arama_kutusu)."""
        try:
            if hasattr(self, "arama_kutusu") and self.arama_kutusu is not None:
                self.arama_kutusu.setFocus()
        except Exception:
            pass

    def toggle_contrast(self):
        """Toggle application stylesheet: switch between saved stylesheet and empty stylesheet to test contrast."""
        try:
            from PySide6.QtGui import QPalette, QColor

            app = QApplication.instance()
            # toggle stylesheet
            if not hasattr(self, "_previous_stylesheet"):
                self._previous_stylesheet = app.styleSheet() or ""
                app.setStyleSheet("")
            else:
                app.setStyleSheet(getattr(self, "_previous_stylesheet", ""))
                delattr(self, "_previous_stylesheet")

            # toggle palette
            if not hasattr(self, "_previous_palette"):
                self._previous_palette = app.palette()
                lightPalette = QPalette()
                lightPalette.setColor(QPalette.Window, QColor("#f7f7f7"))
                lightPalette.setColor(QPalette.WindowText, QColor("#000000"))
                lightPalette.setColor(QPalette.Base, QColor("#ffffff"))
                lightPalette.setColor(QPalette.AlternateBase, QColor("#f4f8ff"))
                lightPalette.setColor(QPalette.Highlight, QColor("#0078D7"))
                lightPalette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
                app.setPalette(lightPalette)
            else:
                app.setPalette(self._previous_palette)
                delattr(self, "_previous_palette")
        except Exception as e:
            self.logger.warning(f"Tema değiştirme hatası: {e}")

    def toggle_tok_theme(self):
        """Toggle Tok theme between light and dark by calling ui.styles toggle helper.

        This stores the currently selected variant on the window object via the helper in styles.py.
        """
        try:
            app = QApplication.instance()
            from ui.styles import toggle_tok_theme as _toggle
            from PySide6.QtCore import QSettings

            _toggle(app, self)
            # Persist setting in QSettings
            try:
                settings = QSettings(APP_NAME, APP_NAME)
                settings.setValue("ui/tok_variant", getattr(self, "_tok_variant", "light"))
            except Exception:
                pass
            # Update menu checked state if available
            try:
                if hasattr(self, "tok_action"):
                    is_dark = getattr(self, "_tok_variant", "light") == "dark"
                    self.tok_action.setChecked(is_dark)
                    try:
                        self.tok_action.setText("Tok: Koyu" if is_dark else "Tok: Açık")
                        self.tok_action.setIcon(QIcon.fromTheme("weather-night") if is_dark else QIcon.fromTheme("weather-clear"))
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception as e:
            self.logger.warning(f"TOK tema değiştirme hatası: {e}")

    # =============================================================================
    # SÜRÜKLE-BIRAK SLOTU (ADIM 4.3 GÜNCELLEMESİ)
    # =============================================================================

    @Slot(int, int)
    def on_proje_tasindi(self, proje_id: int, yeni_kategori_id: int):
        """KategoriAgaci widget'ından gelen 'projeTasindi' sinyalini işler."""
        try:
            # "Kategorisiz" item'ı ID 0 olarak gelir.
            # Veritabanında bunu NULL (None) olarak saklamalıyız.
            db_kategori_id = yeni_kategori_id if yeni_kategori_id > 0 else None

            # Adım 4.1'de eklediğimiz ID tabanlı yeni fonksiyonu kullanıyoruz.
            self.db.projeyi_kategoriye_tasi(proje_id, db_kategori_id)

            # (Adım 3'ten gelen) Çökmeyi önleyen ertelenmiş yenileme
            QTimer.singleShot(0, self.yenile)

        except Exception as e:
            # --- LOG GÜNCELLEMESİ ---
            self.logger.critical(
                f"Proje (ID: {proje_id}) taşınırken hata: {e}", exc_info=True
            )
            QMessageBox.critical(
                self, "Taşıma Hatası", f"Proje taşınırken bir hata oluştu: {e}"
            )

    # =============================================================================
    # PANEL SIGNAL HANDLERS (BRIDGE METHODS)
    # =============================================================================

    def on_project_selected_from_panel(self, proje: Optional[ProjeModel]):
        """Bridge method for ProjectPanel selection signal"""
        # Update internal state
        if proje:
            self.secili_proje_id = proje.id
            revizyonlar = self._get_project_revisions_for_ui(proje.id)
            # Trigger existing logic
            self.proje_detaylarini_goster(proje, revizyonlar=revizyonlar)
            self.revizyonlari_yukle(proje.id, revizyonlar=revizyonlar)
        else:
            self.secili_proje_id = None
            self.revizyon_agaci.clear()
            self.detaylari_temizle()
            self._clear_preview()

        # Update action states
        try:
            self._update_action_states()
        except Exception:
            pass

    def on_revision_selected_from_panel(self, rev: Optional[RevizyonModel]):
        """Bridge method for RevisionPanel selection signal"""
        # Trigger existing logic
        self.revizyon_secilince_detay_guncelle()
        self.preview_timer.start(250)
        try:
            self._update_action_states()
        except Exception:
            pass

    def _get_yazi_dokumani_lookup(
        self, rev: Optional[RevizyonModel], yazi_turu: str
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        if not self.document_service:
            return None, None, None
        return self.document_service.get_letter_lookup(rev, yazi_turu)

    def _build_preview_letter_payload(self, yazi_no: str) -> Optional[dict]:
        item = self._get_secili_revizyon_item()
        rev = item.data(0, Qt.UserRole) if item else None
        if not self.document_service:
            return None
        return self.document_service.build_preview_letter_payload(rev, yazi_no)

    def _build_letter_payload_for_revision(
        self, rev: Optional[RevizyonModel]
    ) -> Optional[dict]:
        """Resolve the exact incoming/outgoing letter payload for a revision."""
        if not rev or not self.document_service:
            return None

        yazi_turu = getattr(rev, "yazi_turu", None)
        if yazi_turu == "giden":
            if getattr(rev, "onay_yazi_no", None):
                yazi_turu = "onay"
            elif getattr(rev, "red_yazi_no", None):
                yazi_turu = "red"

        if not yazi_turu or yazi_turu == "yok":
            return None

        return self.document_service.build_letter_payload_from_revision(rev, yazi_turu)

    def _open_binary_document(
        self,
        dosya_adi: str,
        dosya_verisi: bytes,
        *,
        temp_prefix: str,
        error_title: str,
    ) -> bool:
        """Delegate temp-file document opening to FileService."""
        if not self.file_service:
            self.logger.error("FileService mevcut olmadığı için doküman açılamadı.")
            QMessageBox.critical(
                self,
                error_title,
                "Doküman açma servisi yüklenemedi.",
            )
            return False

        return self.file_service.open_temporary_document(
            dosya_adi,
            dosya_verisi,
            temp_prefix=temp_prefix,
            error_title=error_title,
        )

    def _open_revision_document(self, rev: Optional[RevizyonModel]) -> bool:
        """Open the exact revision document represented by the payload."""
        if not self.document_service:
            QMessageBox.critical(self, "Açma Hatası", "Doküman servisi yüklenemedi.")
            return False
        return self.document_service.open_revision_document(rev)

    def _open_letter_document(self, payload: Optional[dict]) -> bool:
        """Open the exact letter document represented by the preview payload."""
        if not self.document_service:
            QMessageBox.critical(self, "Açma Hatası", "Doküman servisi yüklenemedi.")
            return False
        return self.document_service.open_letter_document(payload)

    def _on_view_letter_from_revision(self, rev: Optional[RevizyonModel]) -> bool:
        """Open the selected revision's associated incoming/outgoing letter."""
        try:
            if not self.document_service:
                QMessageBox.critical(self, "AÃ§ma HatasÄ±", "DokÃ¼man servisi yÃ¼klenemedi.")
                return False
            if not rev:
                QMessageBox.warning(self, "UyarÄ±", "AÃ§Ä±lacak revizyon bulunamadÄ±.")
                return False

            payload = self._build_letter_payload_for_revision(rev)
            if not payload:
                QMessageBox.information(
                    self,
                    "YazÄ± BulunamadÄ±",
                    "SeÃ§ili revizyona ait aÃ§Ä±labilir yazÄ± dokÃ¼manÄ± bulunamadÄ±.",
                )
                return False

            return self._open_letter_document(payload)
        except Exception as e:
            self.logger.error(
                "Revizyondan yazÄ± dokÃ¼manÄ± aÃ§Ä±lÄ±rken hata: %s",
                e,
                exc_info=True,
            )
            QMessageBox.critical(
                self,
                "Hata",
                f"YazÄ± dokÃ¼manÄ± aÃ§Ä±lÄ±rken hata oluÅŸtu:\n{str(e)}"
            )
            return False

    def on_letter_clicked(self, yazi_no: str, yazi_turu: str):
        """Handle double-click on letter numbers - open associated PDF"""
        try:
            item = self._get_secili_revizyon_item()
            secili_rev = item.data(0, Qt.UserRole) if item else None
            # Try getting exact letter data (type & exact date) by matching number
            payload = (
                self.document_service.build_preview_letter_payload(
                    secili_rev,
                    yazi_no,
                )
                if self.document_service
                else None
            )
            
            # Fallback to the looser matching method
            if not payload and self.document_service:
                payload = self.document_service.build_letter_payload_from_revision(
                    secili_rev,
                    yazi_turu,
                    fallback_yazi_no=yazi_no,
                )
            self._open_letter_document(payload)
        except Exception as e:
            self.logger.error(f"Yazı dokümanı açılırken hata: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Hata",
                f"Yazı dokümanı açılırken hata oluştu:\n{str(e)}"
            )

    def _on_yazi_ac_btn_clicked(self) -> bool:
        """Open the letter document currently shown in the lower preview panel."""
        payload = getattr(self, "_current_yazi_payload", None)
        if not payload:
            QMessageBox.information(
                self,
                "YazÄ± BulunamadÄ±",
                "Tam ekran aÃ§Ä±lacak yazÄ± dokÃ¼manÄ± bulunamadÄ±.",
            )
            return False
        return self._open_letter_document(payload)

    def _is_same_as_revision_document(self, rev_id: int, doc_bytes: bytes) -> bool:
        """Return True when uploaded outgoing letter doc is identical to revision doc."""
        if not doc_bytes:
            return False
        try:
            rev_dokuman = self.db.dokumani_getir(rev_id)
            if not rev_dokuman:
                return False
            return rev_dokuman[1] == doc_bytes
        except Exception:
            self.logger.debug("Revizyon dokumani kiyaslamasi yapilamadi", exc_info=True)
            return False

    def _confirm_if_suspicious_letter_doc(
        self, rev_id: int, doc_bytes: bytes, letter_type: str
    ) -> bool:
        """Ask confirmation if outgoing letter doc looks suspiciously identical."""
        if not self._is_same_as_revision_document(rev_id, doc_bytes):
            return True
        cevap = QMessageBox.warning(
            self,
            "Şüpheli Doküman Uyarısı",
            f"Seçtiğiniz {letter_type} dokümanı, revizyon dokümanı ile birebir aynı görünüyor.\n\n"
            "Bu dosya yanlışlıkla yüklenmiş olabilir. Yine de kaydetmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return cevap == QMessageBox.Yes

    def _goruntule_dokuman_wrapper(self, payload):
        """Bridge method for PreviewPanel view button."""
        if isinstance(payload, RevizyonModel):
            self._open_revision_document(payload)
        if isinstance(payload, dict) and payload.get("kind") == "letter":
            self._open_letter_document(payload)
            return
        self._goruntule_dokuman()

    # =============================================================================
    # SEÇİM İŞLEMLERİ
    # =============================================================================

    def proje_secilince(self):
        """Listeden proje seçildiğinde"""
        items = self.proje_listesi_widget.selectedItems()
        if not items:
            self.secili_proje_id = None
            self.revizyon_agaci.clear()
            self.detaylari_temizle()
            self._clear_preview()
            return

        item = items[0]
        proje: ProjeModel = item.data(Qt.UserRole)
        self.secili_proje_id = proje.id
        revizyonlar = self._get_project_revisions_for_ui(proje.id)

        # Detayları güncelle
        self.proje_detaylarini_goster(proje, revizyonlar=revizyonlar)

        # Revizyonları yükle
        self.revizyonlari_yukle(proje.id, revizyonlar=revizyonlar)

    def _agactan_proje_secilince(self):
        """Ağaçtan proje seçildiğinde"""
        items = self.proje_agaci_widget.selectedItems()
        if not items:
            self.secili_proje_id = None
            self.revizyon_agaci.clear()
            self.detaylari_temizle()
            self._clear_preview()
            return

        item = items[0]
        proje: Optional[ProjeModel] = item.data(0, Qt.UserRole)

        if not proje:
            # Kategori seçildi, temizle
            self.secili_proje_id = None
            self.revizyon_agaci.clear()
            self.detaylari_temizle()
            self._clear_preview()
            return

        self.secili_proje_id = proje.id
        revizyonlar = self._get_project_revisions_for_ui(proje.id)

        # Detayları güncelle
        self.proje_detaylarini_goster(proje, revizyonlar=revizyonlar)

        # Revizyonları yükle
        self.revizyonlari_yukle(proje.id, revizyonlar=revizyonlar)

    def _get_project_revisions_for_ui(self, proje_id: int):
        try:
            if getattr(self, "controller", None):
                return self.controller.get_revisions(proje_id)
            return self.db.revizyonlari_getir(proje_id)
        except Exception:
            self.logger.debug("UI için revizyonlar yüklenemedi", exc_info=True)
            return []

    def _get_excel_validation_info(self, proje_kodu: str) -> Optional[dict]:
        """Get Excel validation information for a project code.
        
        Args:
            proje_kodu: Project code to validate against Excel list
            
        Returns:
            Dictionary with validation info (is_in_list, project_type, project_name)
            or None if Excel loader is not available
        """
        if not self.excel_loader:
            return None
        
        try:
            project_info = self.excel_loader.find_project(proje_kodu)
            if project_info:
                excel_type, excel_name = project_info
                self.logger.debug(f"Proje '{proje_kodu}' Excel listesinde bulundu: {excel_type}")
                return {
                    'is_in_list': True,
                    'project_type': excel_type,
                    'project_name': excel_name
                }
            else:
                self.logger.debug(f"Proje '{proje_kodu}' Excel listesinde bulunamadı")
                return {
                    'is_in_list': False,
                    'project_type': '-',
                    'project_name': '-'
                }
        except Exception as e:
            self.logger.warning(f"Excel validation error for {proje_kodu}: {e}")
            return None

    def proje_detaylarini_goster(self, proje: ProjeModel, revizyonlar=None):
        """Seçili proje detaylarını sağ panelde göster"""
        try:
            if not proje:
                return

            self.detay_etiketleri["Proje Kodu:"].setText(proje.proje_kodu)
            self.detay_etiketleri["Proje İsmi:"].setText(proje.proje_ismi)
            self.detay_etiketleri["Proje Türü:"].setText(proje.proje_turu or "-")

            # Hiyerarşi yolunu bul (kategori_id'den)
            hiyerarsi = self.db.get_kategori_yolu(proje.kategori_id)
            self.detay_etiketleri["Hiyerarşi Yolu:"].setText(hiyerarsi)

            # Get all revisions for smart gelen/giden lookup
            if revizyonlar is None:
                revizyonlar = self._get_project_revisions_for_ui(proje.id)

            # Find most recent gelen and giden yazı
            gelen_yazi_no = "-"
            gelen_yazi_tarih = "-"
            gelen_rev_code = ""

            giden_yazi_no = "-"
            giden_yazi_tarih = "-"
            giden_rev_code = ""

            # Search through revisions starting from newest (list is already sorted newest to oldest DESC)
            for rev in revizyonlar:  # No need to reverse - already DESC
                # Look for gelen yazı if not found yet
                if gelen_yazi_no == "-" and rev.gelen_yazi_no:
                    gelen_yazi_no = rev.gelen_yazi_no
                    gelen_yazi_tarih = rev.gelen_yazi_tarih or "-"
                    gelen_rev_code = rev.revizyon_kodu

                # Look for giden yazı if not found yet
                if giden_yazi_no == "-":
                    if rev.onay_yazi_no:
                        giden_yazi_no = rev.onay_yazi_no
                        giden_yazi_tarih = rev.onay_yazi_tarih or "-"
                        giden_rev_code = rev.revizyon_kodu
                    elif rev.red_yazi_no:
                        giden_yazi_no = rev.red_yazi_no
                        giden_yazi_tarih = rev.red_yazi_tarih or "-"
                        giden_rev_code = rev.revizyon_kodu

                # Break if both found
                if gelen_yazi_no != "-" and giden_yazi_no != "-":
                    break

            # Display with revision code in parentheses
            if gelen_yazi_no != "-" and gelen_rev_code:
                self.detay_etiketleri["En Son Gelen Yazı No:"].setText(
                    f"{gelen_yazi_no} ({gelen_rev_code})"
                )
                self.detay_etiketleri["En Son Gelen Yazı Tarihi:"].setText(
                    gelen_yazi_tarih
                )
            else:
                self.detay_etiketleri["En Son Gelen Yazı No:"].setText("-")
                self.detay_etiketleri["En Son Gelen Yazı Tarihi:"].setText("-")

            if giden_yazi_no != "-" and giden_rev_code:
                self.detay_etiketleri["En Son Giden Yazı No:"].setText(
                    f"{giden_yazi_no} ({giden_rev_code})"
                )
                self.detay_etiketleri["En Son Giden Yazı Tarihi:"].setText(
                    giden_yazi_tarih
                )
            else:
                self.detay_etiketleri["En Son Giden Yazı No:"].setText("-")
                self.detay_etiketleri["En Son Giden Yazı Tarihi:"].setText("-")

            # En son revizyon bilgisi
            son_rev = revizyonlar[0] if revizyonlar else None
            if son_rev:
                self.detay_etiketleri["En Son Revizyon Kodu:"].setText(
                    son_rev.revizyon_kodu
                )
                self.detay_etiketleri["Onay Durumu:"].setText(son_rev.durum)

                tse_durum = "Gönderildi" if son_rev.tse_gonderildi else "Gönderilmedi"
                self.detay_etiketleri["TSE Durumu:"].setText(tse_durum)
            else:
                self.detay_etiketleri["En Son Revizyon Kodu:"].setText("-")
                self.detay_etiketleri["Onay Durumu:"].setText(proje.durum or "-")
                self.detay_etiketleri["TSE Durumu:"].setText("-")

            # Excel validation - check if project exists in master list
            excel_validation_info = self._get_excel_validation_info(proje.proje_kodu)

            # Update detail panel labels directly (for now, maintains backward compatibility)
            # Check if new fields exist (for backward compatibility with old UI)
            if excel_validation_info and "Liste Durumu:" in self.detay_etiketleri:
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
                if "Listedeki Tür:" in self.detay_etiketleri:
                    self.detay_etiketleri["Listedeki Tür:"].setText(excel_type)
            elif "Liste Durumu:" in self.detay_etiketleri:
                # No validation info available
                self.detay_etiketleri["Liste Durumu:"].setText("-")
                self.detay_etiketleri["Liste Durumu:"].setStyleSheet("")
                if "Listedeki Tür:" in self.detay_etiketleri:
                    self.detay_etiketleri["Listedeki Tür:"].setText("-")

        except Exception as e:
            self.logger.error(f"Proje detayları gösterilirken hata: {e}")

    def revizyonlari_yukle(self, proje_id, revizyonlar=None):
        """Seçili projenin revizyonlarını yükle"""
        try:
            # Fetch revisions
            if revizyonlar is None:
                revizyonlar = self._get_project_revisions_for_ui(proje_id)

            if getattr(self, "_sadece_takipteki_revizyonlar", False):
                revizyonlar = [
                    r
                    for r in revizyonlar
                    if int(getattr(r, "takipte_mi", 0) or 0) == 1
                ]

            self._show_revision_document_warnings(revizyonlar)

            # Use RevisionPanel if available
            if hasattr(self, "revision_panel") and hasattr(
                self.revision_panel, "load_revisions"
            ):
                self.revision_panel.load_revisions(revizyonlar)
                return

            # Fallback to direct tree population
            self.revizyon_agaci.setSortingEnabled(False)
            # Enforce sorting: Newest -> Oldest (RevNo DESC, ID DESC)
            revizyonlar.sort(key=lambda r: (int(r.proje_rev_no) if r.proje_rev_no is not None else -1, int(r.id)), reverse=True)
            
            self.revizyon_agaci.clear()
            headers = [
                "Revizyon",
                "Durum",
                "Açıklama",
                "Yazı Türü",
                "Yazı No",
                "Yazı Tarihi",
                "Doküman",
                "Yazı Dok.",
                "Uyarı",
                "Takip",
            ]
            self.revizyon_agaci.setHeaderLabels(headers)

            for rev in revizyonlar:
                try:
                    self.logger.debug(f"Loading rev item: id={rev.id}, kod={rev.revizyon_kodu}, yazi_turu={rev.yazi_turu}, gelen={rev.gelen_yazi_no}, onay={rev.onay_yazi_no}, red={rev.red_yazi_no}")
                except Exception:
                    pass
                # Yazı bilgilerini belirle
                yazi_no = "-"
                yazi_tarih = "-"

                if rev.yazi_turu == "gelen":
                    yazi_no = rev.gelen_yazi_no or "-"
                    yazi_tarih = rev.gelen_yazi_tarih or "-"
                elif rev.yazi_turu == "giden":
                    if rev.onay_yazi_no:
                        yazi_no = rev.onay_yazi_no
                        yazi_tarih = rev.onay_yazi_tarih or "-"
                    elif rev.red_yazi_no:
                        yazi_no = rev.red_yazi_no
                        yazi_tarih = rev.red_yazi_tarih or "-"

                # Yazı türü gösterimini iyileştir
                yazi_turu_display = {
                    "gelen": "📥 Gelen Yazı",
                    "giden": "📤 Giden Yazı",
                    "yok": "-"
                }.get(rev.yazi_turu, "-")

                item = QTreeWidgetItem(self.revizyon_agaci)
                item.setText(0, rev.revizyon_kodu)
                item.setText(1, rev.durum)
                item.setText(2, rev.aciklama or "")
                item.setText(3, yazi_turu_display)
                item.setText(4, yazi_no)
                item.setText(5, str(yazi_tarih))
                # Show filename if we have it; otherwise show Var/Yok
                filename_display = getattr(rev, "dosya_adi", None) or rev.dokuman_durumu
                item.setText(6, filename_display)
                yazi_dokuman_durumu = getattr(rev, "yazi_dokuman_durumu", None) or "-"
                item.setText(7, yazi_dokuman_durumu)
                supheli = int(getattr(rev, "supheli_yazi_dokumani", 0) or 0)
                item.setText(8, "Aynı Dosya" if supheli else "-")
                takipte_mi = int(getattr(rev, "takipte_mi", 0) or 0)
                item.setText(9, "Takipte" if takipte_mi else "-")
                takip_notu = getattr(rev, "takip_notu", None)
                if takip_notu:
                    item.setToolTip(9, takip_notu)

                # Renklendirme
                if rev.durum == Durum.ONAYLI.value:
                    item.setForeground(1, QBrush(QColor("green")))
                elif rev.durum == Durum.REDDEDILDI.value:
                    item.setForeground(1, QBrush(QColor("red")))
                elif rev.durum == Durum.ONAYLI_NOTLU.value:
                    item.setForeground(1, QBrush(QColor("orange")))
                if yazi_dokuman_durumu == "Eksik":
                    item.setForeground(7, QBrush(QColor("red")))
                elif yazi_dokuman_durumu == "Yüklü":
                    item.setForeground(7, QBrush(QColor("green")))
                if supheli:
                    item.setForeground(8, QBrush(QColor("darkorange")))
                if takipte_mi:
                    item.setForeground(9, QBrush(QColor("blue")))
                    takip_fill = QBrush(QColor("#ffe7db"))
                    for col in range(10):
                        item.setBackground(col, takip_fill)

                item.setData(0, Qt.UserRole, rev)

            # Sütun genişlikleri
            for i in range(10):
                self.revizyon_agaci.resizeColumnToContents(i)

        except Exception as e:
            self.logger.error(f"Revizyonlar yüklenirken hata: {e}")
        finally:
            try:
                self._update_action_states()
            except Exception:
                pass

    def _show_revision_document_warnings(self, revizyonlar: List[RevizyonModel]):
        """Show missing/suspicious outgoing letter doc warnings for the selected project."""
        try:
            eksik = sum(
                1
                for rev in revizyonlar
                if (getattr(rev, "yazi_dokuman_durumu", None) or "") == "Eksik"
            )
            supheli = sum(
                1
                for rev in revizyonlar
                if int(getattr(rev, "supheli_yazi_dokumani", 0) or 0) == 1
            )
            if eksik or supheli:
                parcalar = []
                if eksik:
                    parcalar.append(f"{eksik} eksik yazı dokümanı")
                if supheli:
                    parcalar.append(f"{supheli} şüpheli aynı dosya")
                mesaj = "Uyarı: " + ", ".join(parcalar)
                if hasattr(self, "_status") and self._status is not None:
                    self._status.showMessage(mesaj, 8000)
        except Exception:
            self.logger.debug("Yazı dokümanı uyarıları hesaplanamadı", exc_info=True)

    def revizyon_secilince_detay_guncelle(self):
        """Revizyon seçildiğinde detayları güncelle (varsa)"""
        # Şu an için ekstra bir detay paneli yok, sadece preview tetikleniyor

    def _get_secili_revizyon_item(self) -> Optional[QTreeWidgetItem]:
        """Seçili revizyon öğesini döndürür"""
        items = self.revizyon_agaci.selectedItems()
        if items:
            return items[0]
        return None

    def _select_revizyon_by_id(self, rev_id: int) -> bool:
        """Select a revision in the tree by its DB id. Returns True if selection was successful."""
        try:
            for i in range(self.revizyon_agaci.topLevelItemCount()):
                item = self.revizyon_agaci.topLevelItem(i)
                r = item.data(0, Qt.UserRole)
                if r and getattr(r, "id", None) == rev_id:
                    self.revizyon_agaci.setCurrentItem(item)
                    try:
                        self.revizyon_agaci.setFocus()
                    except Exception:
                        pass
                    return True
        except Exception:
            pass
        return False

    def eventFilter(self, obj, event):
        """Catch key events for specific widgets (like Delete on revision tree)."""
        from PySide6.QtCore import QEvent

        try:
            if event.type() == QEvent.KeyPress:
                key = event.key()
                if key == Qt.Key_Delete and obj == getattr(self, 'revizyon_agaci', None):
                    # Trigger delete revision action
                    try:
                        self.arayuzden_revizyonu_sil()
                    except Exception:
                        pass
                    return True
                # Delete key in category tree: delete selected categories
                if key == Qt.Key_Delete and obj == getattr(self, 'proje_agaci_widget', None):
                    try:
                        items = self.proje_agaci_widget.selectedItems()
                        for it in items:
                            # If the selected item is a category (not a project)
                            if not it.data(0, Qt.UserRole):
                                kategori_id = it.data(0, KATEGORI_ID_ROL)
                                if kategori_id and kategori_id > 0:
                                    self._kategori_sil(kategori_id)
                        return True
                    except Exception:
                        pass
        except Exception:
            # Fallback to default processing
            pass
        return super().eventFilter(obj, event)

    def detaylari_temizle(self):
        """Detay panelini temizle"""
        for etiket in self.detay_etiketleri.values():
            etiket.setText("")

    def _clear_preview(self):
        """Önizleme panelini temizle"""
        if self.preview_state:
            self.preview_state.clear()
        else:
            self.onizleme_etiketi.clear()
        self.onizleme_etiketi.setText("Bir revizyon seçerek dokümanı ön izleyin.")
        self.goruntule_btn.setEnabled(False)

        if hasattr(self, "yazi_onizleme_etiketi"):
            self.yazi_onizleme_etiketi.clear()
            self.yazi_onizleme_etiketi.setText("Revizyona ait yazı ön izlemesi burada görünür.")
            self.yazi_ac_btn.setEnabled(False)
            self._current_yazi_payload = None

    def _refresh_current_project(self, keep_rev_id: Optional[int] = None):
        """Reload the revisions for the current project and reselect a revision if given.

        This avoids reloading the full projects list and possibly changing the visible projects
        which can cause unwanted UI jumps when editing a single revision.
        """
        try:
            # Clear filter cache only, do not re-populate the project list
            try:
                if getattr(self, 'filter_manager', None):
                    self.filter_manager.clear_cache()
            except Exception as e:
                self.logger.debug(f"Filter cache clear failed in _refresh_current_project: {e}")
            # reload revisions for the current project
            spid = getattr(self, 'secili_proje_id', None)
            if spid:
                try:
                    self.revizyonlari_yukle(spid)
                    self.logger.debug(f"Revisions reloaded for project {spid}")
                except Exception as e:
                    self.logger.warning(f"Failed to reload revisions for project {spid}: {e}")
            # now reselect revision if requested
            if keep_rev_id is not None:
                try:
                    # Add a small delay to ensure UI has updated
                    QTimer.singleShot(50, lambda: self._select_revizyon_by_id(keep_rev_id))
                    # Ensure the revision tree regains focus after reselection
                    QTimer.singleShot(80, lambda: getattr(self, "revizyon_agaci", None) and self.revizyon_agaci.setFocus())
                    self.logger.debug(f"Scheduled revision reselection for rev_id={keep_rev_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to schedule revision reselection: {e}")
        except Exception as e:
            self.logger.error(f"_refresh_current_project failed: {e}", exc_info=True)

    def arayuzden_revizyonu_sil(self):
        """Delete the selected revision from UI and DB after confirmation"""
        # Permission check
        if not self._check_write_permission("revizyon silmek"):
            return
        
        item = self._get_secili_revizyon_item()
        if not item:
            return
        rev: Optional[RevizyonModel] = item.data(0, Qt.UserRole)
        if not rev:
            return
        # Confirm delete
        reply = QMessageBox.question(
            self,
            "Revizyon Sil", 
            f"'{rev.revizyon_kodu}' revizyonunu silmek istediğinize emin misiniz?\nBu işlem geri alınamaz.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            if self.db.revizyonu_sil(rev.id):
                # Refresh revisions list
                if getattr(self, 'secili_proje_id', None):
                    self.revizyonlari_yukle(self.secili_proje_id)
                # Ensure filter cache is invalidated and projects reloaded
                    try:
                        self._invalidate_filter_cache_and_reload(keep_project_id=self.secili_proje_id)
                    except Exception:
                        pass
                QMessageBox.information(self, "Başarılı", "Revizyon başarıyla silindi.")
            else:
                QMessageBox.critical(self, "Hata", "Revizyon silinemedi.")
        except Exception as e:
            self.logger.error(f"Revizyon silme hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Revizyon silinirken hata oluştu: {e}")

    # =============================================================================
    # FİLTRELEME İŞLEMLERİ
    # =============================================================================

    def show_advanced_filters(self):
        """Gelişmiş filtreleme dialogunu göster"""
        dialog = AdvancedFilterDialog(self, self.filter_manager)
        self.filter_manager.begin_batch_update()
        try:
            accepted = bool(dialog.exec())
        finally:
            self.filter_manager.end_batch_update(emit=accepted)

    def apply_filters(self):
        """Aktif filtreleri uygula"""
        try:
            filtered_projects = self.filter_manager.get_filtered_projects()
            self.display_filtered_projects(filtered_projects)
            self.update_filter_indicator()
            self.guncelle_gosterge_panelini()
            self.logger.info(
                f"Filtreler uygulandı: {len(self.filter_manager.active_filters)} aktif filtre"
            )
        except Exception as e:
            # --- LOG GÜNCELLEMESİ ---
            self.logger.critical(f"Filtre uygulanırken hata: {e}")
            QMessageBox.critical(
                self, "Filtre Hatası", f"Filtreler uygulanırken hata oluştu: {e}"
            )

    def display_filtered_projects(self, projects: List[ProjeModel]):
        """Filtrelenmiş projeleri göster"""
        # Set current project pool and populate UI according to current search/filter
        self.tum_projeler = projects
        # Apply any search box filter on top
        self.projeleri_filtrele(
            self.arama_kutusu.text() if hasattr(self, "arama_kutusu") else None
        )

    def update_filter_indicator(self):
        """Filtre göstergesini güncelle"""
        filter_count = len(self.filter_manager.active_filters)
        if filter_count > 0:
            self.filter_indicator.setText(f"Filtre: {filter_count} aktif")
            self.filter_indicator.setStyleSheet(
                "color: blue; font-weight: bold; background-color: #e6f3ff; padding: 5px; border: 1px solid #b3d9ff; border-radius: 3px;"
            )
            try:
                if getattr(self, "status_mem_label", None) and getattr(
                    self, "_status", None
                ):
                    # Optional status message to reflect active filters
                    self._status.showMessage(f"{filter_count} aktif filtre", 2000)
            except Exception:
                pass
        else:
            self.filter_indicator.setText("Filtre: Yok")
            self.filter_indicator.setStyleSheet("color: #666; padding: 5px;")

    def clear_filters(self):
        """Tüm filtreleri temizle"""
        try:
            self._clearing_filters = True
            self.filter_manager.clear_filters()
            # Use centralized invalidation and reload helper
            self._invalidate_filter_cache_and_reload(keep_project_id=self.secili_proje_id)
        finally:
            # Ensure the flag is cleared
            self._clearing_filters = False
        self.update_filter_indicator()
        self.logger.info("Filtreler temizlendi")

    def on_filters_changed(self):
        """Filtreler değiştiğinde otomatik uygula"""
        # Avoid re-entrancy: if we are currently in the process of clearing filters, ignore the signal
        if getattr(self, "_clearing_filters", False):
            return
        self.apply_filters()

    # =============================================================================
    # ARAYÜZ YÜKLEME VE GÜNCELLEME METODLARI
    # =============================================================================

    def _on_search_text_changed(self):
        self.filter_timer.start(300)

    def _on_list_selection_changed(self):
        # Preview timer gereksiz - revizyonlari_yukle içinde otomatik tetikleniyor
        self.proje_secilince()
        # Update enabled/disabled action states
        try:
            self._update_action_states()
        except Exception:
            pass

    def _on_tree_selection_changed(self):
        # Preview timer gereksiz - revizyonlari_yukle içinde otomatik tetikleniyor
        self._agactan_proje_secilince()
        try:
            self._update_action_states()
        except Exception:
            pass

    def _on_revizyon_selection_changed(self):
        self.revizyon_secilince_detay_guncelle()
        self.preview_timer.start(250)
        try:
            self._update_action_states()
        except Exception:
            pass

    def _on_revizyon_double_clicked(self, item, column):
        """Handle double-click on revision tree - open letter PDF if clicked on Yazı No column"""
        try:
            # Column 4 is "Yazı No"
            if column == 4:
                yazi_no = item.text(4)
                # Get yazi_turu from the revision data
                rev = item.data(0, Qt.UserRole)
                if rev and yazi_no and yazi_no != "-":
                    yazi_turu = getattr(rev, 'yazi_turu', None)
                    if yazi_turu:
                        self.on_letter_clicked(yazi_no, yazi_turu)
        except Exception as e:
            self.logger.error(f"Revizyon çift tıklama hatası: {e}", exc_info=True)

    def _update_action_states(self):
        """Enable/disable menu and toolbar actions based on current selection state."""
        try:
            selected_project_ids = set()
            if hasattr(self, "proje_listesi_widget"):
                for item in self.proje_listesi_widget.selectedItems():
                    proje = item.data(Qt.UserRole)
                    proje_id = getattr(proje, "id", None)
                    if proje_id is not None:
                        selected_project_ids.add(proje_id)
            if hasattr(self, "proje_agaci_widget"):
                for item in self.proje_agaci_widget.selectedItems():
                    proje = item.data(0, Qt.UserRole)
                    proje_id = getattr(proje, "id", None)
                    if proje_id is not None:
                        selected_project_ids.add(proje_id)
            selected_projects = len(selected_project_ids)

            try:
                rev_sel = len(self.revizyon_agaci.selectedItems())
            except Exception:
                rev_sel = 0
            secili_rev = None
            takipte_secili_rev = False
            try:
                item = self._get_secili_revizyon_item()
                if item:
                    secili_rev = item.data(0, Qt.UserRole)
                takipte_secili_rev = bool(
                    secili_rev and int(getattr(secili_rev, "takipte_mi", 0) or 0) == 1
                )
            except Exception:
                takipte_secili_rev = False

            # Project-level actions
            if hasattr(self, "proje_duzenle_action"):
                self.proje_duzenle_action.setEnabled(selected_projects == 1)
            if hasattr(self, "proje_sil_action"):
                self.proje_sil_action.setEnabled(selected_projects > 0)
            # Bulk actions
            if hasattr(self, "proje_toplu_gelen_action"):
                self.proje_toplu_gelen_action.setEnabled(selected_projects > 0)
            if hasattr(self, "proje_toplu_onay_action"):
                self.proje_toplu_onay_action.setEnabled(selected_projects > 0)
            if hasattr(self, "proje_toplu_notlu_action"):
                self.proje_toplu_notlu_action.setEnabled(selected_projects > 0)
            if hasattr(self, "proje_toplu_red_action"):
                self.proje_toplu_red_action.setEnabled(selected_projects > 0)

            # Revision-level actions
            if hasattr(self, "revizyon_duzenle_action"):
                self.revizyon_duzenle_action.setEnabled(rev_sel > 0)
            if hasattr(self, "revizyon_sil_action"):
                self.revizyon_sil_action.setEnabled(rev_sel > 0)
            if hasattr(self, "rev_indir_action"):
                self.rev_indir_action.setEnabled(rev_sel > 0)
            if hasattr(self, "revizyon_takip_notu_action"):
                self.revizyon_takip_notu_action.setEnabled(rev_sel > 0)
            if hasattr(self, "revizyon_takip_kaldir_action"):
                self.revizyon_takip_kaldir_action.setEnabled(takipte_secili_rev)
            if hasattr(self, "revizyon_takip_export_action"):
                self.revizyon_takip_export_action.setEnabled(True)
            if hasattr(self, "revizyon_takip_btn"):
                self.revizyon_takip_btn.setEnabled(rev_sel > 0)
            if hasattr(self, "revizyon_takip_kaldir_btn"):
                self.revizyon_takip_kaldir_btn.setEnabled(takipte_secili_rev)

            # Toolbar quick actions reflect menu states where applicable
            if hasattr(self, "new_project_action"):
                self.new_project_action.setEnabled(True)
            if hasattr(self, "new_revision_action"):
                self.new_revision_action.setEnabled(True)
            if hasattr(self, "excel_export_action"):
                self.excel_export_action.setEnabled(True)
            if hasattr(self, "refresh_action"):
                self.refresh_action.setEnabled(True)
        except Exception as e:
            self.logger.debug(f"_update_action_states error: {e}")

    def _setup_permissions(self):
        """Configure UI elements based on user permissions (guest vs logged in)."""
        is_guest = self.auth_service.is_guest
        
        try:
            # List of actions/buttons to disable for guest users
            restricted_actions = [
                # Menu actions
                "yeni_proje_action",
                "proje_duzenle_action",
                "proje_sil_action",
                "yeni_revizyon_action",
                "revizyon_duzenle_action",
                "revizyon_sil_action",
                "revizyon_takip_notu_action",
                "revizyon_takip_kaldir_action",
                "proje_toplu_gelen_action",
                "proje_toplu_onay_action",
                "proje_toplu_notlu_action",
                "proje_toplu_red_action",
                "kategori_duzenle_action",
                "veritabani_ac_action",
                "yeni_veritabani_action",
                # Toolbar actions
                "new_project_action",
                "new_revision_action",
                "revizyon_takip_btn",
                "revizyon_takip_kaldir_btn",
            ]
            
            # Disable restricted actions for guest users
            for action_name in restricted_actions:
                if hasattr(self, action_name):
                    action = getattr(self, action_name)
                    action.setEnabled(not is_guest)
                    
            # Update UI to show permission status
            if is_guest:
                self.logger.info("Guest mode: UI restrictions applied")
            else:
                self.logger.info(f"Full access granted to user: {self.auth_service.get_current_username()}")
                
        except Exception as e:
            self.logger.error(f"Permission setup error: {e}", exc_info=True)

    def _update_user_status_label(self):
        """Update status bar to show current user or guest mode."""
        try:
            if hasattr(self, "_status"):
                user_display = self.auth_service.get_current_display_name()
                if self.auth_service.is_guest:
                    status_text = f"👤 {user_display} (Sadece Görüntüleme)"
                else:
                    status_text = f"✅ {user_display}"
                
                # Create or update user status label
                if not hasattr(self, "user_status_label"):
                    from PySide6.QtWidgets import QLabel
                    self.user_status_label = QLabel()
                    self._status.addPermanentWidget(self.user_status_label)
                
                self.user_status_label.setText(status_text)
        except Exception as e:
            self.logger.warning(f"Failed to update user status label: {e}")

    def _check_write_permission(self, action_name: str = "bu işlemi yapmak") -> bool:
        """Check if user has write permission. Shows warning if not.
        
        Args:
            action_name: Description of the action being attempted
            
        Returns:
            True if user has permission, False otherwise
        """
        if not self.auth_service.has_permission('write'):
            QMessageBox.warning(
                self,
                "Yetki Yok",
                f"Misafir modunda {action_name} için yetkiniz yok.\n\n"
                "Düzenleme yapmak için giriş yapmanız gerekiyor."
            )
            return False
        return True

    def _trigger_preview_update(self):
        """Update the preview window with the current revision's document - optimize edilmiş"""
        try:
            item = self._get_secili_revizyon_item()
            if not item:
                self._clear_preview()
                return

            secili_revizyon: RevizyonModel = item.data(0, Qt.UserRole)
            if not secili_revizyon:
                self._clear_preview()
                return

            render_service = self.preview_render_service
            if not render_service:
                self._clear_preview()
                return

            rev_id = secili_revizyon.id
            load_result = render_service.prepare_revision_preview(secili_revizyon)
            if load_result.status != "ready":
                self._clear_preview()
                if load_result.message:
                    if self.preview_state:
                        self.preview_state.show_status(
                            load_result.message,
                            revision=secili_revizyon,
                            payload=secili_revizyon,
                            clear_visual=True,
                        )
                    else:
                        self.onizleme_etiketi.setText(load_result.message)
                return

            dokuman_verisi = load_result.document_bytes

            # Log debug info about document size
            try:
                size_len = len(dokuman_verisi) if dokuman_verisi else 0
                self.logger.debug(f"Preview will render rev_id={rev_id}, dokuman_size={size_len} bytes, zoom={self.zoom_factor}")
            except Exception:
                pass

            # Guard against rendering after window close
            if not hasattr(self, "_start_pdf_render") or not self.isVisible():
                return

            if self.preview_state:
                self.preview_state.show_loading(secili_revizyon)
            else:
                self.onizleme_etiketi.setText("Ön izleme yükleniyor...")
                self.goruntule_btn.setEnabled(False)

            self._start_pdf_render.emit(dokuman_verisi, self.zoom_factor, rev_id)

            # --- START LETTER PREVIEW RENDER ---
            letter_payload = self._build_letter_payload_for_revision(secili_revizyon)
            yazi_no = letter_payload.get("yazi_no") if letter_payload else None

            if hasattr(self, "yazi_onizleme_etiketi"):
                self.yazi_ac_btn.setEnabled(False)
                self._current_yazi_payload = None
                self.yazi_onizleme_etiketi.clear()

                if letter_payload and yazi_no:
                    self.yazi_onizleme_etiketi.setText("Yazı ön izlemesi yükleniyor...")
                    yazi_dok = self.db.yazi_dokumani_getir(
                        yazi_no,
                        letter_payload.get("yazi_tarih"),
                        letter_payload.get("yazi_turu"),
                    )
                    if yazi_dok and hasattr(self, "_start_yazi_render"):
                        yazi_veri = yazi_dok[1]
                        self._start_yazi_render.emit(yazi_veri, self.zoom_factor, yazi_no)
                    else:
                        self.yazi_onizleme_etiketi.setText("Bu revizyona ait yazı dokümanı bulunamadı.")
                else:
                    self.yazi_onizleme_etiketi.setText("Revizyonun yazısı yok.")
            # --- END LETTER PREVIEW RENDER ---

        except Exception as e:
            self.logger.error(f"Preview update error: {e}", exc_info=True)
            self._clear_preview()
            if self.preview_state:
                self.preview_state.show_status("Ön izleme hatası", clear_visual=True)
            else:
                self.onizleme_etiketi.setText("Ön izleme hatası")

    # --- ÇÖKME DÜZELTMESİ (ADIM 3): Slot'a rev_id (int) eklendi ve GÜVENLİK KONTROLÜ yapıldı ---
    @Slot(QImage, int)
    def _on_image_ready(self, image: QImage, rendered_rev_id: int):
        # --- GÜVENLİK KONTROLÜ (YARIŞ DURUMU ÖNLEME) ---
        item = self._get_secili_revizyon_item()
        if not item:
            return  # Arayüz temizlendi (örn: yenile'ye basıldı), bu eski bir sinyal, yok say.

        current_rev: RevizyonModel = item.data(0, Qt.UserRole)
        if current_rev.id != rendered_rev_id:
            # self.logger.warning(f"Eski sinyal yok sayıldı. Mevcut: {current_rev.id}, Gelen: {rendered_rev_id}")
            return  # Kullanıcı bu arada başka bir şey seçti, bu eski sinyali yok say.
        # --- KONTROL BİTTİ ---

        # Sadece mevcut revizyon ile eşleşirse işlem yap:
        try:
            self.logger.debug(f"_on_image_ready: received image for rev_id={rendered_rev_id}, image_size={image.width()}x{image.height()}, bytes={image.sizeInBytes()}")
        except Exception:
            pass
        pixmap = QPixmap.fromImage(image)
        if self.preview_state:
            self.preview_state.show_revision_preview(current_rev, pixmap)
            return
        self.onizleme_etiketi.setPixmap(pixmap)
        self.goruntule_btn.setEnabled(True)

    @Slot(QImage, str)
    def _on_yazi_image_ready(self, image: QImage, yazi_no: str):
        """Handle the preview of an incoming letter (gelen yazi) image."""
        try:
            self.logger.debug(f"_on_yazi_image_ready: received image for yazi_no={yazi_no}, image_size={image.width()}x{image.height()}, bytes={image.sizeInBytes()}")
        except Exception:
            pass
        # Display the image regardless of selected revision — this is a user request to preview the letter
        pixmap = QPixmap.fromImage(image)
        item = self._get_secili_revizyon_item()
        current_rev = item.data(0, Qt.UserRole) if item else None
        letter_payload = self._build_letter_payload_for_revision(current_rev)
        if not letter_payload or letter_payload.get("yazi_no") != yazi_no:
            return

        # NEW LOGIC: Show it on the bottom panel
        if hasattr(self, "yazi_onizleme_etiketi"):
            self.yazi_onizleme_etiketi.setPixmap(pixmap)
            self.yazi_ac_btn.setEnabled(bool(letter_payload))
            self._current_yazi_payload = letter_payload
        else:
            self.onizleme_etiketi.setPixmap(pixmap)
            self.goruntule_btn.setEnabled(bool(letter_payload))

    # --- ÇÖKME DÜZELTMESİ (ADIM 4): Slot'a rev_id (int) eklendi ve GÜVENLİK KONTROLÜ yapıldı ---
    @Slot(str, int)
    def _on_image_error(self, error_msg: str, rendered_rev_id: int):
        # --- GÜVENLİK KONTROLÜ (YARIŞ DURUMU ÖNLEME) ---
        item = self._get_secili_revizyon_item()
        if not item:
            return  # Arayüz temizlendi

        current_rev: RevizyonModel = item.data(0, Qt.UserRole)
        if current_rev.id != rendered_rev_id:
            return  # Eski bir hatayı gösterme
        # --- KONTROL BİTTİ ---

        # Sadece mevcut revizyon ile eşleşirse işlem yap:
        try:
            self.logger.debug(f"_on_image_error: rev_id={rendered_rev_id}, msg={error_msg}")
        except Exception:
            pass
        self.logger.critical(
            f"PDF önizleme hatası (Rev ID: {rendered_rev_id}): {error_msg}"
        )
        if self.preview_state:
            self.preview_state.show_render_error(error_msg)
            return
        self.onizleme_etiketi.setText(f"Önizleme oluşturulamadı.\n{error_msg}")
        self.goruntule_btn.setEnabled(False)

    @Slot(int)
    def _on_ana_sekme_degisti(self, index):
        if index == 0 or index == 1:
            self._arama_kutusu_degisti()
        elif index == 2:
            self.guncelle_gosterge_panelini()
        elif index == 3 and hasattr(self, "log_panel"):
            self.log_panel.refresh_from_disk()

    def _arama_kutusu_degisti(self):
        try:
            current_index = self.sekme_widget.currentIndex()
            if current_index == 0:
                # Pass the search text to the filter method
                search_text = self.arama_kutusu.text() if hasattr(self, "arama_kutusu") else ""
                self.projeleri_filtrele(search_text)
            elif current_index == 1:
                self._kategori_agacini_filtrele()

            if current_index == 2:
                self.guncelle_gosterge_panelini()
        except Exception as e:
            # Catch unexpected errors in search flow to prevent a crash and collect logs
            try:
                self.logger.error(f"Hata: _arama_kutusu_degisti sırasında hata: {e}", exc_info=True)
            except Exception:
                pass
            try:
                QMessageBox.critical(self, "Arama Hatası", f"Arama sırasında hata oluştu: {e}")
            except Exception:
                pass

    def _kategori_agacini_filtrele(self):
        sorgu = self.arama_kutusu.text().lower()
        root = self.proje_agaci_widget.invisibleRootItem()
        any_visible = False
        for i in range(root.childCount()):
            item = root.child(i)
            if self._filtre_uygula_recursive(item, sorgu):
                any_visible = True

        if sorgu and any_visible:
            self.proje_agaci_widget.expandAll()
        elif not sorgu:
            self.proje_agaci_widget.expandAll()

    def _filtre_uygula_recursive(self, item, sorgu):
        item_text = item.text(0).lower()
        mevcut_item_eslesiyor_mu = sorgu in item_text

        proje_data: Optional[ProjeModel] = item.data(0, Qt.UserRole)
        if proje_data and not mevcut_item_eslesiyor_mu:
            proje_kodu = proje_data.proje_kodu.lower()
            mevcut_item_eslesiyor_mu = sorgu in proje_kodu

        cocuklardan_eslesen_var_mi = False
        for i in range(item.childCount()):
            if self._filtre_uygula_recursive(item.child(i), sorgu):
                cocuklardan_eslesen_var_mi = True

        gosterilmeli = mevcut_item_eslesiyor_mu or cocuklardan_eslesen_var_mi
        item.setHidden(not gosterilmeli)

        return gosterilmeli

    def _revizyon_context_menu(self, position):
        """Revizyon ağacı için sağ-tık menüsü."""
        item = self.revizyon_agaci.itemAt(position)
        if not item:
            return
        self.revizyon_agaci.setCurrentItem(item)
        rev = item.data(0, Qt.UserRole)
        if not rev:
            return

        menu = QMenu(self)

        # Yeni Eklenen "Yazıyı Görüntüle" Aksiyonu
        view_letter_action = menu.addAction("📄 Yazıyı Görüntüle")
        has_letter = getattr(rev, "yazi_turu", "yok") in ("gelen", "giden")
        view_letter_action.setEnabled(has_letter)
        menu.addSeparator()

        takip_action = menu.addAction("Takip Notu Ekle/Güncelle...")
        takip_kaldir_action = menu.addAction("Takip İşaretini Kaldır")
        takip_kaldir_action.setEnabled(
            int(getattr(rev, "takipte_mi", 0) or 0) == 1
        )

        secim = menu.exec(self.revizyon_agaci.viewport().mapToGlobal(position))
        
        if secim == view_letter_action:
            self._on_view_letter_from_revision(rev)
        elif secim == takip_action:
            self.revizyon_takip_notu_ekle_duzenle()
        elif secim == takip_kaldir_action:
            self.revizyon_takip_kaldir()

    # --- GÜNCELLEME (ADIM 5.3) ---
    def _kategori_gorunumu_context_menu(self, position):
        menu = QMenu()
        item = self.proje_agaci_widget.itemAt(position)

        # Metin yolu ('hiyerarsi_yolu') yerine doğrudan 'kategori_id' alıyoruz
        kategori_id: Optional[int] = None

        if item:
            # Tıklanan bir proje mi?
            proje_verisi: Optional[ProjeModel] = item.data(0, Qt.UserRole)
            if proje_verisi:
                # Evet, projenin kategori ID'sini al
                kategori_id = proje_verisi.kategori_id
            else:
                # Hayır, tıklanan bir kategori. ID'sini ROL'den al
                # (Kategorisiz item'ı için bu 0 dönecek, o da None'a eşitlenecek)
                kategori_id = item.data(0, KATEGORI_ID_ROL)

        # 'Kategorisiz' (ID=0) ise None ata
        kategori_id = kategori_id if kategori_id and kategori_id > 0 else None

        yeni_proje_action = QAction("Yeni Proje Oluştur...", self)
        # _context_menu_yeni_proje'ye metin yolu yerine kategori_id'yi gönder
        yeni_proje_action.triggered.connect(
            lambda: self._context_menu_yeni_proje(kategori_id)
        )
        menu.addAction(yeni_proje_action)

        # Yeni kategori oluşturma seçeneği
        yeni_kategori_action = QAction("Yeni Kategori Oluştur...", self)
        yeni_kategori_action.triggered.connect(
            lambda: self._context_menu_yeni_kategori(kategori_id)
        )
        menu.addAction(yeni_kategori_action)

        # Kategori silme seçeneğini yalnızca kategori üzerinde göstereceğiz (proje değil)
        # Sadece kategori düğümü üzerinde sağ tıklandıysa silme seçeneğini göster
        if item and not item.data(0, Qt.UserRole) and kategori_id:
            sil_action = QAction("Kategoriyi Sil", self)
            sil_action.triggered.connect(lambda: self._kategori_sil(kategori_id))
            menu.addAction(sil_action)

        menu.exec(self.proje_agaci_widget.viewport().mapToGlobal(position))

    def _kategori_sil(self, kategori_id: int):
        """Sil butonuna tıklanınca veya delete tuşuna basılınca çağrılır.

        Bu fonksiyon DB üzerinde değişiklik yapar: kategoriyi siler ve varsa projeleri üst kategoriye taşır veya NULL set eder.
        """
        # Güvenlik: 0 veya None olan kategoriler silinemez
        if not kategori_id or kategori_id <= 0:
            QMessageBox.warning(self, "Uyarı", "Bu kategori silinemez.")
            return

        try:
            # Get category name and parent
            row = self.db.cursor.execute(
                "SELECT isim, parent_id FROM kategoriler WHERE id = ?",
                (kategori_id,),
            ).fetchone()
            if not row:
                QMessageBox.warning(self, "Uyarı", "Kategori bulunamadı.")
                return
            isim, parent_id = row
            parent_name = None
            if parent_id:
                parent_row = self.db.cursor.execute(
                    "SELECT isim FROM kategoriler WHERE id = ?", (parent_id,)
                ).fetchone()
                parent_name = parent_row[0] if parent_row else None

            hedef = parent_name or "Kategorisiz"
            reply = QMessageBox.question(
                self,
                "Kategoriyi Sil",
                f"'{isim}' kategorisini silmek üzeresiniz. Bu kategori altındaki projeler '{hedef}' kategorisine taşınacaktır. Devam etmek istiyor musunuz?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            # Call DB helper and reload
            success = self.db.kategoriyi_sil(kategori_id)
            if success:
                self._invalidate_filter_cache_and_reload()
                QMessageBox.information(self, "Başarılı", "Kategori silindi ve projeler yeniden atandı.")
            else:
                QMessageBox.critical(self, "Hata", "Kategori silinirken hata oluştu.")
        except Exception as e:
            self.logger.error(f"Kategori silme hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Beklenmedik hata: {e}")

    def _get_item_path(self, item: QTreeWidgetItem) -> str:
        # Bu fonksiyon artık KategoriAgaci tarafından kullanılmıyor,
        # ancak ne olur ne olmaz diye (belki başka bir yerde kullanılır)
        # bırakıyoruz.
        yol_parcalari = []
        gecerli_item = item
        while gecerli_item:
            if not gecerli_item.data(0, Qt.UserRole):
                yol_parcalari.insert(0, gecerli_item.text(0))
            gecerli_item = gecerli_item.parent()
        return "/".join(yol_parcalari)

    # --- GÜNCELLEME (ADIM 5.3) ---
    # Fonksiyon artık 'hiyerarsi_yolu' (str) yerine 'kategori_id' (int) alıyor
    def _context_menu_yeni_proje(self, kategori_id: Optional[int] = None):
        # _proje_penceresi_yonet'e 'hiyerarsi' metni yerine 'kategori_id' gönder
        on_veri = {"kategori_id": kategori_id}
        self._proje_penceresi_yonet(on_veri=on_veri)

    # --- GÜNCELLEME BİTTİ ---

    def _context_menu_yeni_kategori(self, parent_kategori_id: Optional[int] = None):
        """Context menüden yeni kategori oluşturma işlemi.

        parent_kategori_id: None veya üst kategori ID'si (0/None => root)
        """
        # İsim sor
        isim, ok = QInputDialog.getText(self, "Yeni Kategori", "Kategori adı:")
        if not ok:
            return
        isim = (isim or "").strip()
        if not isim:
            QMessageBox.warning(self, "Uyarı", "Kategori adı boş olamaz.")
            return

        # Parent ID: None olarak veritabanına iletilmeli (0 => None)
        db_parent = (
            parent_kategori_id
            if parent_kategori_id and parent_kategori_id > 0
            else None
        )

        yeni_id = self.db.add_kategori(isim, db_parent)
        if yeni_id:
            try:
                self.proje_agaci_widget.setUpdatesEnabled(False)

                # Create or retrieve the 'Kategorisiz' item
                kategorisiz_item = self.kategori_items_map.get(0)
                if not kategorisiz_item:
                    kategorisiz_item = QTreeWidgetItem(
                        self.proje_agaci_widget, ["Kategorisiz"]
                    )
                    kategorisiz_item.setData(0, KATEGORI_ID_ROL, 0)
                    kategorisiz_item.setFlags(Qt.ItemIsDropEnabled)
                    self.kategori_items_map[0] = kategorisiz_item

                # Color and emoji maps for project statuses
                durum_renk_map = {
                    Durum.ONAYLI.value: QColor("#d4edda"),  # Yeşil background
                    Durum.ONAYLI_NOTLU.value: QColor("#fff3cd"),  # Turuncu background
                    Durum.REDDEDILDI.value: QColor("#f8d7da"),  # Kırmızı background
                    "Onaysiz": QColor("#f0f0f0"),  # Açık gri background
                }
                durum_emoji_map = {
                    Durum.ONAYLI.value: "✅",
                    Durum.ONAYLI_NOTLU.value: "📝",
                    Durum.REDDEDILDI.value: "❌",
                    "Onaysiz": "⭕",
                }

                # Batch add projects to the tree under their categories
                for proje in self.tum_projeler:
                    kategori_id_key = (
                        proje.kategori_id if proje.kategori_id is not None else 0
                    )
                    parent_item = self.kategori_items_map.get(
                        kategori_id_key, kategorisiz_item
                    )

                    # Project status
                    durum = proje.durum or "Onaysiz"
                    emoji = durum_emoji_map.get(durum, "⭕")
                    background_color = durum_renk_map.get(durum, QColor("#f0f0f0"))

                    proje_item_text = f"{emoji} {proje.proje_kodu} - {proje.proje_ismi}"
                    proje_item = QTreeWidgetItem(parent_item, [proje_item_text])
                    proje_flags = (
                        proje_item.flags()
                        | Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled
                    )
                    proje_item.setFlags(proje_flags)
                    proje_item.setData(0, Qt.UserRole, proje)
                    proje_item.setBackground(0, background_color)

                if kategorisiz_item.childCount() == 0:
                    if (
                        self.proje_agaci_widget.indexOfTopLevelItem(kategorisiz_item)
                        > -1
                    ):
                        self.proje_agaci_widget.takeTopLevelItem(
                            self.proje_agaci_widget.indexOfTopLevelItem(
                                kategorisiz_item
                            )
                        )

                # Expand the whole tree once
                self.proje_agaci_widget.expandAll()
            except Exception as e:
                self.logger.error(
                    f"Kategori ağacı yüklenirken hata: {e}", exc_info=True
                )
            finally:
                self.proje_agaci_widget.setUpdatesEnabled(True)

    def _revizyon_islem_baslat(self, islem_turu):
        """
        Revizyon onaylama/reddetme işlemi - AYNI REVİZYON KODUNA YENİ SATIR EKLER!
        Mevcut gelen yazı revizyonuna, giden yazı olarak yeni satır ekler.
        """
        item = self._get_secili_revizyon_item()
        if not item:
            return QMessageBox.warning(
                self,
                "Revizyon Seçilmedi",
                f"{islem_turu}lama işlemi için bir revizyon seçin.",
            )

        rev: RevizyonModel = item.data(0, Qt.UserRole)
        rev_id = rev.id
        proje_id = self.secili_proje_id

        if not proje_id:
            return QMessageBox.warning(self, "Hata", "Proje seçili değil.")

        mevcut_yazilar = (
            self.db.mevcut_onay_yazilarini_getir()
            if islem_turu in ["Onay", "Notlu Onay"]
            else self.db.mevcut_red_yazilarini_getir()
        )

        # --- YENİ ÇÖKME DÜZELTMESİ: Zamanlayıcıyı diyalog açılmadan durdur ---
        self.preview_timer.stop()
        dialog = OnayRedDialog(self, islem_turu, mevcut_yazilar)

        if dialog.exec():
            veri = dialog.get_data()
            yazi_turu_db = "onay" if islem_turu in ["Onay", "Notlu Onay"] else "red"

            # Giden yazı dokümanını kaydet
            if veri.get("dosya_yolu"):
                try:
                    with open(veri["dosya_yolu"], "rb") as f:
                        yazi_dok_veri = f.read()
                    if self._confirm_if_suspicious_letter_doc(
                        rev_id, yazi_dok_veri, f"{islem_turu.lower()} yazısı"
                    ):
                        self.db.yazi_dokumani_kaydet(
                            veri["yazi_no"],
                            os.path.basename(veri["dosya_yolu"]),
                            yazi_dok_veri,
                            yazi_turu_db,
                            veri.get("tarih"),
                        )
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Yazı Kayıt Hatası",
                        f"{islem_turu} yazısı kaydedilemedi: {e}",
                    )

            try:
                # AYNI REVİZYON KODUNA YENİ SATIR EKLE (giden yazı)
                ayni_rev_kodu = rev.revizyon_kodu  # Aynı revizyon kodunu kullan

                # Durum belirle
                if islem_turu == "Onay":
                    yeni_durum = Durum.ONAYLI.value
                elif islem_turu == "Notlu Onay":
                    yeni_durum = Durum.ONAYLI_NOTLU.value
                else:  # Red
                    yeni_durum = Durum.REDDEDILDI.value

                # Açıklama
                aciklama = (
                    f"{islem_turu} Yazısı: {veri['yazi_no']} tarihli {veri['tarih']}"
                )

                # Mevcut revizyonun dokümanını kopyala (aynı dosya)
                mevcut_dokuman = self.db.dokumani_getir(rev_id)
                if not mevcut_dokuman:
                    QMessageBox.warning(
                        self, "Hata", "Mevcut revizyonun dokümanı bulunamadı!"
                    )
                    return

                # Yeni: kullanıcının mevcut doküman bytes'ını doğrudan DB'ye gönder
                try:
                    yeni_rev_id = self.db.mevcut_projeye_revizyon_ekle(
                        proje_id,
                        ayni_rev_kodu,
                        (
                            os.path.basename(mevcut_dokuman[0])
                            if mevcut_dokuman[0]
                            else None
                        ),
                        aciklama,
                        "giden",  # yazi_turu
                        yeni_durum,
                        dosya_verisi=mevcut_dokuman[1],
                    )

                    # Onay/Red yazı bilgilerini güncelle
                    if islem_turu in ["Onay", "Notlu Onay"]:
                        self.db.cursor.execute(
                            "UPDATE revizyonlar SET onay_yazi_no = ?, onay_yazi_tarih = ? WHERE id = ?",
                            (veri["yazi_no"], veri["tarih"], yeni_rev_id),
                        )
                    else:  # Red
                        self.db.cursor.execute(
                            "UPDATE revizyonlar SET red_yazi_no = ?, red_yazi_tarih = ? WHERE id = ?",
                            (veri["yazi_no"], veri["tarih"], yeni_rev_id),
                        )

                    self.db.conn.commit()

                    self.logger.info(
                        f"Aynı revizyona {islem_turu} yazısı eklendi: Proje ID {proje_id}, Rev {ayni_rev_kodu}"
                    )

                    QMessageBox.information(
                        self,
                        "Başarılı",
                        f"✅ Giden yazı eklendi!\n\n"
                        f"Revizyon Kodu: {ayni_rev_kodu}\n"
                        f"Durum: {yeni_durum}\n"
                        f"Yazı No: {veri['yazi_no']}\n\n"
                        f"📤 Aynı revizyona giden yazı olarak eklendi.",
                    )

                finally:
                    # No temp file to delete in the new bytes-based flow
                    pass

            except Exception as e:
                self.logger.critical(
                    f"Revizyon {islem_turu} hatası: {e}", exc_info=True
                )
                QMessageBox.critical(self, "Hata", f"Giden yazı eklenemedi: {e}")

            # Listeyi güncellerken mevcut proje ve yeni/aynı revizyon seçimini koru
            try:
                # Ensure project selection stays pinned
                self.secili_proje_id = proje_id
                target_rev_id = yeni_rev_id if "yeni_rev_id" in locals() else rev_id
                self._refresh_current_project(keep_rev_id=target_rev_id)
            except Exception:
                try:
                    self._invalidate_filter_cache_and_reload(keep_project_id=proje_id, keep_rev_id=target_rev_id if "target_rev_id" in locals() else None)
                except Exception:
                    self.yenile(keep_rev_id=target_rev_id if "target_rev_id" in locals() else None, keep_project_id=proje_id)

    def revizyon_durumunu_degistir(self):
        # ... (değişiklik yok) ...
        item = self._get_secili_revizyon_item()
        if not item:
            return QMessageBox.warning(
                self,
                "Revizyon Seçilmedi",
                "Lütfen durumunu düzeltmek için bir revizyon seçin.",
            )
        rev: RevizyonModel = item.data(0, Qt.UserRole)
        mevcut_kod = rev.revizyon_kodu
        mevcut_durum = rev.durum

        # --- YENİ ÇÖKME DÜZELTMESİ: Zamanlayıcıyı durdur ---
        self.preview_timer.stop()
        dialog = DurumDegistirDialog(self, mevcut_durum, mevcut_kod)

        if dialog.exec():
            veri = dialog.get_data()
            yeni_durum = veri["yeni_durum"]
            yeni_kod = veri["yeni_kod"]
            if yeni_durum == mevcut_durum and yeni_kod == mevcut_kod:
                return QMessageBox.information(
                    self, "Değişiklik Yok", "Durum veya kod değiştirilmedi."
                )

            # --- YENİ ÇÖKME DÜZELTMESİ: Zamanlayıcıyı durdur ---
            self.preview_timer.stop()
            yanit = QMessageBox.warning(
                self,
                "Onay Gerekli",
                f"Revizyon '{mevcut_kod}' ({mevcut_durum}) durumundan\n"
                f"'{yeni_kod}' ({yeni_durum}) durumuna geçirilecek.\n\n"
                "<b>Bu işlem revizyonun durumunu ve kodunu değiştirecektir; mevcut onay/red/gelen yazıları korunacaktır.</b>\n\n"
                "Devam etmek istediğinizden emin misiniz?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if yanit == QMessageBox.Yes:
                try:
                    basarili = self.db.revizyon_durum_ve_kod_guncelle(
                        rev.id, yeni_durum, yeni_kod
                    )
                    if basarili:
                        QMessageBox.information(
                            self,
                            "Başarılı",
                            "Revizyon durumu ve kodu başarıyla düzeltildi.",
                        )
                        # Yenileme sırasında mevcut proje/revizyon seçimini koru
                        try:
                            if not getattr(self, "secili_proje_id", None):
                                self.secili_proje_id = rev.proje_id if hasattr(rev, "proje_id") else self.secili_proje_id
                            self._refresh_current_project(keep_rev_id=rev.id)
                        except Exception:
                            try:
                                self._invalidate_filter_cache_and_reload(keep_project_id=self.secili_proje_id, keep_rev_id=rev.id)
                            except Exception:
                                self.yenile(keep_rev_id=rev.id, keep_project_id=self.secili_proje_id)
                    else:
                        QMessageBox.critical(
                            self, "Hata", "Veritabanı güncellenirken bir hata oluştu."
                        )
                except Exception as e:
                    # --- LOG GÜNCELLEMESİ ---
                    self.logger.critical(
                        f"Revizyon durum düzeltme hatası: {e}", exc_info=True
                    )
                    QMessageBox.critical(
                        self,
                        "Kritik Hata",
                        f"Düzeltme işlemi sırasında beklenmedik bir hata oluştu: {e}",
                    )

    def _dosya_kaydet_dialog(self, dosya_adi, dosya_verisi):
        """Delegate to FileService for file saving."""
        return self.file_service.save_file_dialog(dosya_adi, dosya_verisi)

    def dokumani_indir(self):
        """Download the selected revision's document."""
        item = self._get_secili_revizyon_item()
        if not item:
            return

        rev: RevizyonModel = item.data(0, Qt.UserRole)
        dokuman = self.db.dokumani_getir(rev.id)
        self.file_service.download_document(dokuman)

    def gelen_yaziyi_indir(self):
        """Download the selected revision's incoming letter document."""
        item = self._get_secili_revizyon_item()
        if not item:
            return

        rev_data: RevizyonModel = item.data(0, Qt.UserRole)
        if not rev_data:
            return

        yazi_no = rev_data.gelen_yazi_no
        if not yazi_no:
            QMessageBox.warning(
                self,
                "Bilgi",
                "Bu revizyon için ilişkilendirilmiş bir gelen yazı numarası yok.",
            )
            return

        dokuman = self.db.yazi_dokumani_getir(
            yazi_no,
            rev_data.gelen_yazi_tarih,
            "gelen",
        )
        self.file_service.download_letter_document(dokuman, yazi_no, "gelen yazı")

    def onay_red_yazisini_indir(self):
        """Download the selected revision's approval/rejection letter document."""
        item = self._get_secili_revizyon_item()
        if not item:
            return

        rev_verisi: RevizyonModel = item.data(0, Qt.UserRole)
        if not rev_verisi:
            return

        yazi_no = None
        yazi_tipi_str = ""

        if rev_verisi.durum in [Durum.ONAYLI.value, Durum.ONAYLI_NOTLU.value]:
            yazi_no = rev_verisi.onay_yazi_no
            yazi_tarih = rev_verisi.onay_yazi_tarih
            yazi_tipi_str = "Onay"
            yazi_dok_turu = "onay"
        elif rev_verisi.durum == Durum.REDDEDILDI.value:
            yazi_no = rev_verisi.red_yazi_no
            yazi_tarih = rev_verisi.red_yazi_tarih
            yazi_tipi_str = "Red"
            yazi_dok_turu = "red"
        else:
            yazi_tarih = None
            yazi_dok_turu = None

        if not yazi_no:
            QMessageBox.warning(
                self,
                "Bilgi",
                f"Bu revizyon için ilişkilendirilmiş bir {yazi_tipi_str} yazısı numarası yok.",
            )
            return

        dokuman = self.db.yazi_dokumani_getir(yazi_no, yazi_tarih, yazi_dok_turu)
        self.file_service.download_letter_document(
            dokuman, yazi_no, f"{yazi_tipi_str} yazı"
        )

    def revizyon_takip_notu_ekle_duzenle(self):
        """Add/update tracking note for selected revision."""
        if not self._check_write_permission("revizyonu takibe almak"):
            return
        item = self._get_secili_revizyon_item()
        if not item:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir revizyon seçin.")
            return
        rev: RevizyonModel = item.data(0, Qt.UserRole)
        if not rev:
            return

        mevcut = self.db.revizyon_takip_bilgisi_getir(rev.id) or {}
        varsayilan_not = (mevcut.get("takip_notu") or "").strip()
        not_metni, ok = QInputDialog.getMultiLineText(
            self,
            "Takip Notu",
            "Seçili revizyon için takip notu:",
            varsayilan_not,
        )
        if not ok:
            return
        not_metni = (not_metni or "").strip()
        if not not_metni:
            QMessageBox.warning(self, "Eksik Bilgi", "Takip notu boş bırakılamaz.")
            return

        self.db.revizyonu_takibe_al(rev.id, not_metni)
        try:
            self._refresh_current_project(keep_rev_id=rev.id)
        except Exception:
            self.revizyonlari_yukle(self.secili_proje_id)
        QMessageBox.information(self, "Başarılı", "Revizyon takip listesine eklendi.")

    def revizyon_takip_kaldir(self):
        """Remove selected revision from active tracking list."""
        if not self._check_write_permission("revizyon takibini kaldırmak"):
            return
        item = self._get_secili_revizyon_item()
        if not item:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir revizyon seçin.")
            return
        rev: RevizyonModel = item.data(0, Qt.UserRole)
        if not rev:
            return
        if int(getattr(rev, "takipte_mi", 0) or 0) != 1:
            QMessageBox.information(
                self, "Bilgi", "Bu revizyon aktif takip listesinde değil."
            )
            return

        cevap = QMessageBox.question(
            self,
            "Takibi Kaldır",
            f"Rev-{rev.revizyon_kodu} için takip işaretini kaldırmak istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if cevap != QMessageBox.Yes:
            return

        self.db.revizyonu_takipten_cikar(rev.id)
        try:
            self._refresh_current_project(keep_rev_id=rev.id)
        except Exception:
            self.revizyonlari_yukle(self.secili_proje_id)
        QMessageBox.information(self, "Başarılı", "Revizyon takipten çıkarıldı.")

    def takip_listesini_excele_aktar(self):
        """Export revision tracking list to Excel."""
        if not self.report_service:
            QMessageBox.critical(
                self, "Hata", "Rapor servisi başlatılamadı. Excel aktarımı yapılamadı."
            )
            return
        self.report_service.export_revision_tracking_to_excel()

    def revizyon_takip_filtresini_degistir(self, checked: bool):
        """Show only actively tracked revisions in revision tree."""
        self._sadece_takipteki_revizyonlar = bool(checked)
        if self.secili_proje_id:
            self.revizyonlari_yukle(self.secili_proje_id)

    def excele_aktar(self):
        """Export projects to Excel - delegate to ReportService."""
        self.report_service.export_to_excel(
            statistics_labels=self.istatistik_etiketleri,
            report_table=getattr(self, "rapor_tur_table", None),
            report_text_widget=getattr(self, "rapor_tur_listesi", None),
        )

    def projeleri_klasore_cikar(self):
        """Tüm projeleri seçilen klasöre hiyerarşik yapıda çıkar."""
        from dialogs.export_dialog import ProjectExportDialog
        dialog = ProjectExportDialog(self.db.db_adi, self)
        dialog.exec()

    def manuel_yedek_al(self):
        """Manuel olarak veritabanı yedeği al"""
        try:
            yedek_dosya = self.db.otomatik_yedek_al("Manuel")
            if yedek_dosya:
                QMessageBox.information(
                    self,
                    "Yedek Alındı",
                    f"Veritabanı yedeği başarıyla alındı:\n\n{yedek_dosya}\n\n"
                    f"Yedek klasörü: {self.db.yedek_klasoru}",
                )
                self.logger.info(f"Manuel yedek alındı: {yedek_dosya}")
            else:
                QMessageBox.warning(
                    self,
                    "Hata",
                    "Yedek alınırken bir hata oluştu. Lütfen log dosyasını kontrol edin.",
                )
        except Exception as e:
            self.logger.error(f"Manuel yedek alma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yedek alma hatası: {e}")

    def rapor_olustur(self):
        """Generate PDF report - delegate to ReportService."""
        return self.report_service.generate_pdf_report()

    def yedekleri_goster(self):
        """Mevcut yedekleri listele"""
        try:
            yedekler = self.db.yedekleri_listele()

            if not yedekler:
                QMessageBox.information(
                    self, "Yedek Bulunamadı", "Henüz hiç yedek alınmamış."
                )
                return

            # Dialog oluştur
            dialog = QDialog(self)
            dialog.setWindowTitle("Veritabanı Yedekleri")
            dialog.setMinimumSize(700, 400)

            layout = QVBoxLayout(dialog)

            # Bilgi etiketi
            info_label = QLabel(f"Toplam {len(yedekler)} adet yedek bulundu:")
            layout.addWidget(info_label)

            # Tablo oluştur
            from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView

            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(
                ["Dosya Adı", "Tarih", "Boyut (KB)", "Tam Yol"]
            )
            table.setRowCount(len(yedekler))
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)

            for i, yedek in enumerate(yedekler):
                table.setItem(i, 0, QTableWidgetItem(yedek["ad"]))
                table.setItem(i, 1, QTableWidgetItem(yedek["tarih_str"]))
                table.setItem(i, 2, QTableWidgetItem(f"{yedek['boyut_kb']:.2f}"))
                table.setItem(i, 3, QTableWidgetItem(yedek["dosya"]))

            # Sütun genişliklerini ayarla
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.Stretch)

            layout.addWidget(table)

            # Butonlar
            button_layout = QHBoxLayout()
            close_btn = QPushButton("Kapat")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addStretch()
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)

            dialog.exec()

        except Exception as e:
            self.logger.error(f"Yedek listeleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Yedek listeleme hatası: {e}")

    def yedekten_geri_yukle_dialog(self):
        """Yedekten geri yükleme dialogu"""
        try:
            yedekler = self.db.yedekleri_listele()

            if not yedekler:
                QMessageBox.information(
                    self, "Yedek Bulunamadı", "Geri yüklenecek yedek bulunamadı."
                )
                return

            # Dialog oluştur
            dialog = QDialog(self)
            dialog.setWindowTitle("Yedekten Geri Yükle")
            dialog.setMinimumSize(700, 450)

            layout = QVBoxLayout(dialog)

            # Uyarı etiketi
            warning_label = QLabel(
                "⚠️ <b>DİKKAT:</b> Bu işlem mevcut veritabanını seçilen yedek ile değiştirecektir.\\n"
                "Devam etmeden önce mevcut durumun yedeğini almanız önerilir."
            )
            warning_label.setStyleSheet(
                "QLabel { background-color: #fff3cd; border: 1px solid #ffc107; padding: 10px; border-radius: 5px; }"
            )
            warning_label.setWordWrap(True)
            layout.addWidget(warning_label)

            # Tablo oluştur
            from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView

            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Dosya Adı", "Tarih", "Boyut (KB)"])
            table.setRowCount(len(yedekler))
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)

            for i, yedek in enumerate(yedekler):
                table.setItem(i, 0, QTableWidgetItem(yedek["ad"]))
                table.setItem(i, 1, QTableWidgetItem(yedek["tarih_str"]))
                table.setItem(i, 2, QTableWidgetItem(f"{yedek['boyut_kb']:.2f}"))
                # Yedek dosya yolunu row data olarak sakla
                table.item(i, 0).setData(Qt.UserRole, yedek["dosya"])

            # Sütun genişliklerini ayarla
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

            layout.addWidget(table)

            # Butonlar
            button_layout = QHBoxLayout()
            restore_btn = QPushButton("Geri Yükle")
            restore_btn.setStyleSheet(
                "QPushButton { background-color: #28a745; color: white; padding: 5px 15px; }"
            )
            cancel_btn = QPushButton("İptal")

            def on_restore():
                selected_rows = table.selectedItems()
                if not selected_rows:
                    QMessageBox.warning(dialog, "Uyarı", "Lütfen bir yedek seçin.")
                    return

                yedek_dosya = table.item(selected_rows[0].row(), 0).data(Qt.UserRole)

                # Son onay
                reply = QMessageBox.question(
                    dialog,
                    "Onay",
                    f"Bu yedeği geri yüklemek istediğinizden emin misiniz?\\n\\n"
                    f"{yedek_dosya}\\n\\n"
                    "Mevcut veritabanı değiştirilecektir!",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )

                if reply == QMessageBox.Yes:
                    # Geri yükleme yap
                    if self.db.yedekten_geri_yukle(yedek_dosya):
                        QMessageBox.information(
                            dialog,
                            "Başarılı",
                            "Veritabanı başarıyla geri yüklendi.\\n\\n"
                            "Lütfen uygulamayı yeniden başlatın.",
                        )
                        dialog.accept()
                        # Uygulamayı kapat
                        self.close()
                    else:
                        QMessageBox.critical(
                            dialog,
                            "Hata",
                            "Geri yükleme başarısız oldu. Lütfen log dosyasını kontrol edin.",
                        )

            restore_btn.clicked.connect(on_restore)
            cancel_btn.clicked.connect(dialog.reject)

            button_layout.addStretch()
            button_layout.addWidget(restore_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)

            dialog.exec()

        except Exception as e:
            self.logger.error(f"Geri yükleme dialog hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Geri yükleme hatası: {e}")

    # =============================================================================
    # VERİTABANI DOSYASI YÖNETİMİ
    # =============================================================================

    def _son_kullanilan_dosya_kaydet(self):
        """Mevcut veritabanı dosyasını son kullanılanlar listesine ekle"""
        try:
            settings = QSettings(APP_NAME, APP_NAME)

            # Son kullanılan dosyayı kaydet
            settings.setValue("database/last_file", self.current_db_file)

            # Son kullanılan dosyalar listesini al
            recent_files = settings.value("database/recent_files", [])
            if not isinstance(recent_files, list):
                recent_files = []

            # Mevcut dosyayı listenin başına ekle
            if self.current_db_file in recent_files:
                recent_files.remove(self.current_db_file)
            recent_files.insert(0, self.current_db_file)

            # Son 5 dosyayı tut
            recent_files = recent_files[:5]

            # Kaydet
            settings.setValue("database/recent_files", recent_files)

            # Menüyü güncelle
            self._son_kullanilan_dosyalari_guncelle()

        except Exception as e:
            self.logger.warning(f"Son kullanılan dosya kaydedilemedi: {e}")

    def _son_kullanilan_dosyalari_guncelle(self):
        """Son kullanılan dosyalar menüsünü güncelle"""
        try:
            if not hasattr(self, "son_dosyalar_menu"):
                return

            # Menüyü temizle
            self.son_dosyalar_menu.clear()

            # Son kullanılan dosyaları al
            settings = QSettings(APP_NAME, APP_NAME)
            recent_files = settings.value("database/recent_files", [])
            if not isinstance(recent_files, list):
                recent_files = []

            # Var olan dosyaları filtrele
            valid_files = [f for f in recent_files if os.path.exists(f)]

            if valid_files:
                for db_file in valid_files:
                    # Dosya adı ve yolunu göster
                    file_name = os.path.basename(db_file)
                    # file_dir is not used; removed unused variable

                    action = QAction(f"{file_name}", self)
                    action.setToolTip(db_file)
                    action.setStatusTip(db_file)

                    # Mevcut dosya ise işaretle
                    if db_file == self.current_db_file:
                        action.setEnabled(False)
                        action.setText(f"● {file_name} (Açık)")

                    action.triggered.connect(
                        lambda checked, path=db_file: self._veritabani_degistir(path)
                    )
                    self.son_dosyalar_menu.addAction(action)

                # Listeyi temizle seçeneği
                self.son_dosyalar_menu.addSeparator()
                clear_action = QAction("Listeyi Temizle", self)
                clear_action.triggered.connect(self._son_kullanilan_listesini_temizle)
                self.son_dosyalar_menu.addAction(clear_action)
            else:
                # Liste boş
                empty_action = QAction("(Boş)", self)
                empty_action.setEnabled(False)
                self.son_dosyalar_menu.addAction(empty_action)

        except Exception as e:
            self.logger.warning(f"Son kullanılan dosyalar menüsü güncellenemedi: {e}")

    def _son_kullanilan_listesini_temizle(self):
        """Son kullanılan dosyalar listesini temizle"""
        try:
            reply = QMessageBox.question(
                self,
                "Listeyi Temizle",
                "Son kullanılan dosyalar listesini temizlemek istediğinizden emin misiniz?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                settings = QSettings(APP_NAME, APP_NAME)
                settings.setValue("database/recent_files", [])
                self._son_kullanilan_dosyalari_guncelle()
                QMessageBox.information(self, "Başarılı", "Liste temizlendi.")
        except Exception as e:
            self.logger.error(f"Liste temizleme hatası: {e}")

    def _update_excel_loader_path(self):
        """Update Excel loader service path to match current database location."""
        try:
            if hasattr(self, 'excel_loader') and self.excel_loader is not None:
                # Calculate new Excel path based on current database location
                new_excel_path = os.path.join(
                    os.path.dirname(self.current_db_file),
                    "proje_listesi.xlsx"
                )

                # Update the Excel loader's path
                self.excel_loader.excel_path = new_excel_path

                # Clear cache to force reload from new location
                self.excel_loader.reload()

                self.logger.info(f"Excel loader path updated to: {new_excel_path}")
        except Exception as e:
            self.logger.warning(f"Excel loader path update failed: {e}")

    def yeni_veritabani_olustur(self):
        """Yeni bir veritabanı dosyası oluştur"""
        try:
            # Dosya adı sor
            dosya_yolu, _ = QFileDialog.getSaveFileName(
                self,
                "Yeni Veritabanı Oluştur",
                "",
                "SQLite Veritabanı (*.db);;Tüm Dosyalar (*.*)",
            )

            if not dosya_yolu:
                return  # İptal edildi

            # .db uzantısı yoksa ekle
            if not dosya_yolu.endswith(".db"):
                dosya_yolu += ".db"

            # Dosya zaten var mı kontrol et
            if os.path.exists(dosya_yolu):
                reply = QMessageBox.question(
                    self,
                    "Dosya Mevcut",
                    f"'{os.path.basename(dosya_yolu)}' zaten mevcut.\n\nÜzerine yazmak istiyor musunuz?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )

                if reply == QMessageBox.No:
                    return

                # Eski dosyayı sil
                try:
                    os.remove(dosya_yolu)
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Dosya silinemedi: {e}")
                    return

            # Yeni veritabanına geç
            self._veritabani_degistir(dosya_yolu)

            QMessageBox.information(
                self,
                "Başarılı",
                f"Yeni veritabanı oluşturuldu:\n\n{dosya_yolu}\n\n"
                "Şimdi bu veritabanı ile çalışabilirsiniz.",
            )

        except Exception as e:
            self.logger.error(f"Yeni veritabanı oluşturma hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Yeni veritabanı oluşturulamadı:\n{e}")

    def veritabani_ac(self):
        """Mevcut bir veritabanı dosyası aç"""
        try:
            # Dosya seç
            dosya_yolu, _ = QFileDialog.getOpenFileName(
                self,
                "Veritabanı Aç",
                "",
                "SQLite Veritabanı (*.db);;Tüm Dosyalar (*.*)",
            )

            if not dosya_yolu:
                return  # İptal edildi

            # Dosya var mı kontrol et
            if not os.path.exists(dosya_yolu):
                QMessageBox.critical(self, "Hata", "Seçilen dosya bulunamadı.")
                return

            # Veritabanına geç
            self._veritabani_degistir(dosya_yolu)

        except Exception as e:
            self.logger.error(f"Veritabanı açma hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Veritabanı açılamadı:\n{e}")

    def _veritabani_degistir(self, yeni_dosya_yolu):
        """Aktif veritabanını değiştir"""
        try:
            # Mutlak yol
            yeni_dosya_yolu = os.path.abspath(yeni_dosya_yolu)

            # Aynı dosya ise işlem yapma
            if yeni_dosya_yolu == self.current_db_file:
                QMessageBox.information(self, "Bilgi", "Bu veritabanı zaten açık.")
                return

            # Mevcut değişiklikleri kontrol et
            if hasattr(self, "db") and self.db.degisiklik_var_mi():
                reply = QMessageBox.question(
                    self,
                    "Kaydedilmemiş Değişiklikler",
                    f"Mevcut veritabanında {self.db._degisiklik_sayisi} kaydedilmemiş değişiklik var.\n\n"
                    "Değiştirmeden önce kaydetmek ister misiniz?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Yes,
                )

                if reply == QMessageBox.Cancel:
                    return  # İptal
                elif reply == QMessageBox.Yes:
                    # Kaydet
                    try:
                        self.db.conn.commit()
                        for conn in self.db._connection_pool.values():
                            try:
                                conn.commit()
                            except Exception:
                                pass
                        self.db.degisiklikleri_sifirla()
                    except Exception as e:
                        QMessageBox.warning(self, "Uyarı", f"Kaydetme hatası: {e}")

            # Eski veritabanını kapat
            try:
                if hasattr(self, "db"):
                    if hasattr(self.db, "close"):
                        self.db.close()
                    else:
                        self.db.cleanup_connections()
                        self.db.conn.close()
            except Exception as e:
                self.logger.warning(f"Eski veritabanı kapatma uyarısı: {e}")
            # Yeni veritabanını aç
            self.current_db_file = yeni_dosya_yolu
            self.db = ProjeTakipDB(self.current_db_file)

            # Update Excel loader path for new database location
            self._update_excel_loader_path()

            # Update dependent components that keep a reference to db
            try:
                if getattr(self, "controller", None):
                    # Controller uses self.window.db property now; ensure its filter_manager reference is current
                    self.controller.filter_manager = self.filter_manager
            except Exception:
                pass
            try:
                if getattr(self, "filter_manager", None):
                    self.filter_manager.db = self.db
            except Exception:
                pass
            try:
                if getattr(self, "report_service", None):
                    self.report_service.db = self.db
            except Exception:
                pass

            # UI'ı sıfırla ve yeniden yükle
            self.secili_proje_id = None
            self.tum_projeler = []

            # Cache'leri temizle
            self._cache_temizle()

            # Projeleri yükle
            self.projeleri_yukle()

            # Pencere başlığını güncelle
            db_name = os.path.basename(self.current_db_file)
            self.setWindowTitle(f"{APP_NAME} - {APP_VERSION} - [{db_name}]")

            # Son kullanılan dosyayı kaydet
            self._son_kullanilan_dosya_kaydet()

            # Kullanıcıyı bilgilendir
            if hasattr(self, "_status"):
                self._status.showMessage(f"Veritabanı değiştirildi: {db_name}", 5000)

            self.logger.info(f"Veritabanı değiştirildi: {self.current_db_file}")

        except Exception as e:
            self.logger.error(f"Veritabanı değiştirme hatası: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Kritik Hata",
                f"Veritabanı değiştirilemedi:\n\n{e}\n\n"
                "Uygulama yeniden başlatılabilir.",
            )

            # Eski veritabanına geri dönmeye çalış
            try:
                if self.current_db_file != yeni_dosya_yolu:
                    self.db = ProjeTakipDB(self.current_db_file)
                    self.projeleri_yukle()
            except Exception:
                pass

    def yeni_proje_penceresi(self):
        """Yeni proje oluşturma penceresini aç"""
        self._proje_penceresi_yonet()

    def _proje_penceresi_yonet(self, proje_id=None, on_veri=None):
        """Proje ekleme/düzenleme penceresini yönet"""
        try:
            # Dialog açılmadan önce timer'ı durdur
            if hasattr(self, "preview_timer"):
                self.preview_timer.stop()

            # Kategorileri hazırla
            # ProjeDialog (id, "Tam/Yol") formatında liste bekliyor
            kategoriler_raw = self.db.get_kategoriler()
            kategori_listesi = []
            for kat_id, kat_isim, _ in kategoriler_raw:
                yol = self.db.get_kategori_yolu(kat_id)
                kategori_listesi.append((kat_id, yol))

            # Listeyi yola göre sırala
            kategori_listesi.sort(key=lambda x: x[1])

            # on_veri hazırla
            dialog_data = on_veri or {}
            if proje_id:
                proje = self.db.proje_bul_id_ile(proje_id)
                if proje:
                    # proje tuple: id, kod, isim, tur, tarih, hiyerarsi, durum, kategori_id
                    dialog_data.update(
                        {
                            "id": proje[0],
                            "kod": proje[1],
                            "isim": proje[2],
                            "tur": proje[3],
                            # proje_bul_id_ile returns: id, proje_kodu, proje_ismi, proje_turu, olusturma_tarihi, hiyerarsi, kategori_id
                            "kategori_id": proje[6],
                        }
                    )

            dialog = ProjeDialog(self, kategori_listesi, dialog_data)

            if dialog.exec():
                veri = dialog.get_data()

                if proje_id:
                    try:
                        updated = self.db.projeyi_guncelle(
                            proje_id,
                            veri["kod"],
                            veri["isim"],
                            veri.get("tur"),
                            veri.get("kategori_id"),
                        )
                        if not updated:
                            QMessageBox.critical(
                                self,
                                "Hata",
                                "Proje güncellenemedi. Kod zaten mevcut olabilir.",
                            )
                            return
                        self.logger.info(f"Proje güncellendi: {veri['kod']}")
                    except Exception as e:
                        self.logger.error(f"Proje güncelleme hatası: {e}")
                        QMessageBox.critical(self, "Hata", f"Proje güncellenemedi: {e}")
                        return
                else:
                    try:
                        new_project_id = self.db.proje_ekle(
                            veri["kod"],
                            veri["isim"],
                            veri.get("tur"),
                            veri.get("kategori_id"),
                        )
                        if not new_project_id:
                            QMessageBox.critical(
                                self,
                                "Hata",
                                "Proje oluşturulamadı. Kod zaten mevcut olabilir.",
                            )
                            return
                        proje_id = new_project_id
                        self.logger.info(f"Yeni proje oluşturuldu: {veri['kod']}")
                    except Exception as e:
                        self.logger.error(f"Proje oluşturma hatası: {e}")
                        QMessageBox.critical(self, "Hata", f"Proje oluşturulamadı: {e}")
                        return

                # Başarılı ise listeyi yenile ve filtre cache temizle
                self._invalidate_filter_cache_and_reload()

                # Yeni eklenen/düzenlenen projeyi seç
                if proje_id:
                    self.secili_proje_id = proje_id
                    # Listede bul ve seç (basitçe yenileme sonrası seçim koruma mantığı eklenebilir)

        except Exception as e:
            self.logger.error(f"Proje penceresi hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"İşlem sırasında hata oluştu: {e}")

    def proje_duzenleme_penceresi(self):
        """Seçili projeyi düzenle"""
        # Permission check
        if not self._check_write_permission("proje düzenlemek"):
            return
        if not self.secili_proje_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlenecek projeyi seçin.")
            return
        self._proje_penceresi_yonet(proje_id=self.secili_proje_id)

    def dosyadan_proje_olustur(self):
        """Dosya isminden proje oluştur"""
        dosyalar, _ = QFileDialog.getOpenFileNames(
            self, "Dosyadan Proje Oluştur", "", "Tüm Dosyalar (*.*)"
        )
        if not dosyalar:
            return
        eklenen_projeler = []
        hatali_dosyalar = []

        files_info = []
        for dosya_yolu in dosyalar:
            dosya_adi = os.path.basename(dosya_yolu)
            bilgi = dosyadan_proje_bilgisi_cikar(dosya_adi) or {}
            files_info.append(
                {
                    "dosya_adi": dosya_adi,
                    "dosya_yolu": dosya_yolu,
                    "kod": bilgi.get("kod", ""),
                    "isim": bilgi.get("isim", ""),
                    "tur": bilgi.get("tur", ""),
                    "kategori_id": bilgi.get("kategori_id"),
                    "gelen_yazi_no": bilgi.get("gelen_yazi_no", ""),
                    "gelen_yazi_tarih": bilgi.get("gelen_yazi_tarih", ""),
                    "mevcut": bool(self.db.proje_var_mi(bilgi.get("kod", ""))),
                    "yeni_revizyon_kodu": "",
                }
            )

        bulk_dialog = DosyadanCokluProjeDialog(self, self.db, files_info)
        if not bulk_dialog.exec():
            return

        results = bulk_dialog.get_results()
        for info, res in zip(files_info, results):
            if not res.get("ekle"):
                continue

            dosya_yolu = info["dosya_yolu"]
            rev_yazi_turu = "gelen" if res.get("gelen_yazi_no") else "yok"
            proj_id = self.db.proje_var_mi(res.get("kod"))

            if proj_id:
                rev_kodu = res.get("yeni_revizyon_kodu") or self.db.sonraki_revizyon_kodu_onerisi(
                    proj_id, rev_yazi_turu
                )
                try:
                    with open(dosya_yolu, "rb") as f:
                        dosya_verisi = f.read()
                    self.db.mevcut_projeye_revizyon_ekle(
                        proj_id,
                        rev_kodu,
                        dosya_yolu,
                        aciklama=f"Revizyon {rev_kodu} - dosyadan eklendi",
                        yazi_turu=rev_yazi_turu,
                        durum=Durum.ONAYSIZ.value,
                        dosya_verisi=dosya_verisi,
                        gelen_yazi_no=res.get("gelen_yazi_no") or None,
                        gelen_yazi_tarih=res.get("gelen_yazi_tarih") or None,
                    )
                    eklenen_projeler.append(res.get("kod"))
                except Exception as e:
                    self.logger.error(f"Revizyon ekleme hatası (bulk): {e}")
                    hatali_dosyalar.append(
                        f"{res.get('dosya_adi')} (rev ekleme hatası: {e})"
                    )
            else:
                try:
                    new = self.db.dosyadan_proje_ve_revizyon_ekle(
                        res.get("kod"),
                        res.get("isim"),
                        dosya_yolu,
                        yazi_turu=rev_yazi_turu,
                        proje_turu=res.get("tur") or None,
                        kategori_id=res.get("kategori_id"),
                        gelen_yazi_no=res.get("gelen_yazi_no") or None,
                        gelen_yazi_tarih=res.get("gelen_yazi_tarih") or None,
                    )
                    if new:
                        eklenen_projeler.append(res.get("kod"))
                except Exception as e:
                    self.logger.error(f"Yeni proje ekleme hatası (bulk): {e}")
                    hatali_dosyalar.append(
                        f"{res.get('dosya_adi')} (proje ekleme hatası: {e})"
                    )

        if eklenen_projeler:
            self._invalidate_filter_cache_and_reload()
            QMessageBox.information(
                self, "İşlem Tamamlandı", f"{len(eklenen_projeler)} proje işlendi."
            )
        if hatali_dosyalar:
            QMessageBox.warning(
                self, "Bazı Dosyalar İşlenemedi", f"{len(hatali_dosyalar)} dosya işlenemedi: {', '.join(hatali_dosyalar)}"
            )

    def yeni_revizyon_yukle(self):
        """Yeni revizyon ekle"""
        # Permission check
        if not self._check_write_permission("revizyon eklemek"):
            return
        if not self.secili_proje_id:
            QMessageBox.warning(
                self, "Uyarı", "Lütfen revizyon eklenecek projeyi seçin."
            )
            return

        try:
            # Dialog açılmadan önce timer'ı durdur
            if hasattr(self, "preview_timer"):
                self.preview_timer.stop()

            # Projeyi bul
            proje = self.db.proje_bul_id_ile(self.secili_proje_id)
            if not proje:
                QMessageBox.critical(self, "Hata", "Proje bulunamadı.")
                return

            proje_kodu = proje[1]  # proje_kodu

            # Mevcut gelen yazıları al
            mevcut_yazilar = self.db.mevcut_gelen_yazilari_getir()

            # First ask which revision code to use (like bulk/file flow)
            mevcut_revizyonlar = [r[0] for r in self.db.cursor.execute(
                "SELECT revizyon_kodu FROM revizyonlar WHERE proje_id = ?",
                (self.secili_proje_id,),
            ).fetchall()]
            suggested_rev = self.db.sonraki_revizyon_kodu_onerisi(
                self.secili_proje_id, "gelen"
            )
            # Open the combined YeniRevizyonDialog with suggested rev code
            dialog = YeniRevizyonDialog(
                self,
                suggested_rev,
                mevcut_yazilar=mevcut_yazilar,
            )

            if dialog.exec():
                veri = dialog.get_data()
                # Determine yazi_turu
                yazi_turu = "yok"
                if veri.get("gelen_yazi_no"):
                    yazi_turu = "gelen"
                elif veri.get("onay_yazi_no") or veri.get("red_yazi_no"):
                    yazi_turu = "giden"

                # Read rev file bytes
                dosya_yolu = veri.get("dosya_yolu")
                if not dosya_yolu and veri.get("yeni_rev_dosya_yolu"):
                    dosya_yolu = veri.get("yeni_rev_dosya_yolu")
                dosya_verisi = None
                dosya_adi = None
                if dosya_yolu:
                    with open(dosya_yolu, "rb") as f:
                        dosya_verisi = f.read()
                        dosya_adi = os.path.basename(dosya_yolu)

                try:
                    rev_id = self.db.mevcut_projeye_revizyon_ekle(
                        self.secili_proje_id,
                        veri.get("revizyon_kodu"),
                        dosya_yolu,
                        veri.get("aciklama", ""),
                        yazi_turu,
                        Durum.ONAYSIZ.value,
                        dosya_verisi=dosya_verisi,
                    )

                    if rev_id:
                        # If there are yazı numbers, update the new revision entry accordingly
                        if yazi_turu == "gelen" and veri.get("gelen_yazi_no"):
                            sql = "UPDATE revizyonlar SET gelen_yazi_no = ?, gelen_yazi_tarih = ? WHERE id = ?"
                            params = (veri.get("gelen_yazi_no"), veri.get("gelen_yazi_tarih"), rev_id)
                            # running update sql
                            self.db.cursor.execute(sql, params)
                            # Save gelen yazı dokümanı if provided
                            if veri.get("yeni_yazi_dosya_yolu"):
                                try:
                                    with open(veri["yeni_yazi_dosya_yolu"], "rb") as f:
                                        dok_veri = f.read()
                                        res = self.db.yazi_dokumani_kaydet(
                                            veri.get("gelen_yazi_no"),
                                            os.path.basename(veri["yeni_yazi_dosya_yolu"]),
                                            dok_veri,
                                            "gelen",
                                            veri.get("gelen_yazi_tarih"),
                                        )
                                    self.logger.info(f"Gelen yazı dokümanı kaydedildi: {res}, yazi_no={veri.get('gelen_yazi_no')} (rev_kodu={veri.get('revizyon_kodu')})")
                                    # Render the yazi for preview
                                    try:
                                        self._start_yazi_render.emit(dok_veri, self.zoom_factor, veri.get("gelen_yazi_no"))
                                    except Exception:
                                        self.logger.debug("_start_yazi_render emit failed in new rev flow", exc_info=True)
                                except Exception as e:
                                    self.logger.error(f"Gelen yazı dokümanı kaydedilemedi: {e}", exc_info=True)
                                    raise
                        elif yazi_turu == "giden":
                            if veri.get("onay_yazi_no"):
                                self.db.cursor.execute(
                                    "UPDATE revizyonlar SET onay_yazi_no = ?, onay_yazi_tarih = ? WHERE id = ?",
                                    (veri.get("onay_yazi_no"), veri.get("onay_yazi_tarih"), rev_id),
                                )
                                if veri.get("yeni_onay_dosya_yolu"):
                                    with open(veri["yeni_onay_dosya_yolu"], "rb") as f:
                                        onay_dok_veri = f.read()
                                    if self._confirm_if_suspicious_letter_doc(
                                        rev_id, onay_dok_veri, "onay yazısı"
                                    ):
                                        self.db.yazi_dokumani_kaydet(
                                            veri.get("onay_yazi_no"),
                                            os.path.basename(veri["yeni_onay_dosya_yolu"]),
                                            onay_dok_veri,
                                            "onay",
                                            veri.get("onay_yazi_tarih"),
                                        )
                            if veri.get("red_yazi_no"):
                                self.db.cursor.execute(
                                    "UPDATE revizyonlar SET red_yazi_no = ?, red_yazi_tarih = ? WHERE id = ?",
                                    (veri.get("red_yazi_no"), veri.get("red_yazi_tarih"), rev_id),
                                )
                                if veri.get("yeni_red_dosya_yolu"):
                                    with open(veri["yeni_red_dosya_yolu"], "rb") as f:
                                        red_dok_veri = f.read()
                                    if self._confirm_if_suspicious_letter_doc(
                                        rev_id, red_dok_veri, "red yazısı"
                                    ):
                                        self.db.yazi_dokumani_kaydet(
                                            veri.get("red_yazi_no"),
                                            os.path.basename(veri["yeni_red_dosya_yolu"]),
                                            red_dok_veri,
                                            "red",
                                            veri.get("red_yazi_tarih"),
                                        )

                        self.db.conn.commit()
                        QMessageBox.information(self, "Başarılı", "Yeni revizyon eklendi.")
                except Exception as e:
                    self.logger.error(f"Revizyon ekleme hatası: {e}", exc_info=True)
                    QMessageBox.critical(self, "Hata", f"Yeni revizyon eklenemedi: {e}")

                # Refresh lists and clear filter cache after DB write - preserve new revision selection
                self.revizyonlari_yukle(self.secili_proje_id)
                try:
                    self._invalidate_filter_cache_and_reload(keep_project_id=self.secili_proje_id, keep_rev_id=rev_id)
                except Exception:
                    self._invalidate_filter_cache_and_reload(keep_project_id=self.secili_proje_id)

        except Exception as e:
            self.logger.error(f"Revizyon ekleme hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Revizyon eklenirken hata oluştu: {e}")

    def arayuzden_revizyonu_duzenle(self):
        """Seçili revizyonu düzenle - yeni sisteme uyumlu"""
        # Permission check
        if not self._check_write_permission("revizyon düzenlemek"):
            return
        
        item = self._get_secili_revizyon_item()
        if not item:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlenecek revizyonu seçin.")
            return

        rev: RevizyonModel = item.data(0, Qt.UserRole)
        if not rev:
            return

        try:
            # Dialog açılmadan önce timer'ı durdur
            if hasattr(self, "preview_timer"):
                self.preview_timer.stop()

            # Projeyi bul
            proje = self.db.proje_bul_id_ile(self.secili_proje_id)
            if not proje:
                QMessageBox.critical(self, "Hata", "Proje bulunamadı.")
                return

            # proje_kodu not needed here; avoid unused local variable

            # Revizyon verilerini hazırla
            on_veri = {
                "id": rev.id,
                "aciklama": rev.aciklama or "",
                "durum": rev.durum,
                "gelen_yazi_no": rev.gelen_yazi_no,
                "gelen_yazi_tarih": rev.gelen_yazi_tarih,
                "onay_yazi_no": rev.onay_yazi_no,
                "onay_yazi_tarih": rev.onay_yazi_tarih,
                "red_yazi_no": rev.red_yazi_no,
                "red_yazi_tarih": rev.red_yazi_tarih,
                "tse_gonderildi": rev.tse_gonderildi,
            }

            # TSE bilgileri varsa ekle (database'den çekilmeli)
            try:
                tse_bilgisi = self.db.cursor.execute(
                    "SELECT tse_yazi_no, tse_yazi_tarih FROM revizyonlar WHERE id = ?",
                    (rev.id,),
                ).fetchone()
                if tse_bilgisi:
                    on_veri["tse_yazi_no"] = tse_bilgisi[0]
                    on_veri["tse_yazi_tarih"] = tse_bilgisi[1]
            except Exception:
                pass

            # Mevcut yazıları al (yazi_turu'ya göre)
            if rev.yazi_turu == "gelen":
                mevcut_yazilar = self.db.mevcut_gelen_yazilari_getir()
            else:  # giden veya yok
                mevcut_yazilar = {}

            # Revizyon düzenleme dialogu aç
            dialog = YeniRevizyonDialog(
                self,
                rev.revizyon_kodu,
                mevcut_yazilar=mevcut_yazilar,
                on_veri=on_veri,
                yazi_turu=rev.yazi_turu,
            )

            if dialog.exec():
                # Dialog'dan verileri al
                veri = dialog.get_data()
                try:
                    self.logger.debug(f"Revizyon düzenleme dialog sonucu: {veri}")
                except Exception:
                    pass

                # Deduce new yazı türü from the dialog's submitted data (in case it changed)
                yeni_yazi_turu = rev.yazi_turu or "yok"
                if veri.get("gelen_yazi_no"):
                    yeni_yazi_turu = "gelen"
                elif veri.get("onay_yazi_no") or veri.get("red_yazi_no"):
                    yeni_yazi_turu = "giden"
                try:
                    self.logger.debug(f"Revizyon {rev.id} eski yazi_turu={rev.yazi_turu}, yeni yazi_turu={yeni_yazi_turu}")
                except Exception:
                    pass
                # Call update with computed yazi_turu
                self._revizyon_guncelle_db(rev.id, veri, yeni_yazi_turu)
                # Refresh only the current project to avoid full project list reloads that might hide the project
                try:
                    self._refresh_current_project(keep_rev_id=rev.id)
                except Exception:
                    try:
                        self._invalidate_filter_cache_and_reload(keep_project_id=self.secili_proje_id, keep_rev_id=rev.id)
                    except Exception:
                        pass

        except Exception as e:
            self.logger.error(f"Revizyon düzenleme hatası: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Hata", f"Revizyon düzenlenirken hata oluştu: {e}"
            )

    def _revizyon_guncelle_db(self, rev_id, veri, yazi_turu):
        """Revizyon verilerini veritabanında güncelle"""
        # Permission check (defensive)
        if not self.auth_service.has_permission('write'):
            self.logger.warning("Unauthorized attempt to update revision")
            return
        
        try:
            # Temel alanları güncelle (revizyon_kodu dahil)
            self.db.cursor.execute(
                """
                UPDATE revizyonlar 
                SET revizyon_kodu = ?,
                    aciklama = ?,
                    tse_gonderildi = ?,
                    tse_yazi_no = ?,
                    tse_yazi_tarih = ?
                WHERE id = ?
            """,
                (
                    veri.get("revizyon_kodu"),
                    veri.get("aciklama"),
                    veri.get("tse_gonderildi", 0),
                    veri.get("tse_yazi_no"),
                    veri.get("tse_yazi_tarih"),
                    rev_id,
                ),
            )

            # Gelen yazı alanlarını güncelle (sadece gelen türündeyse)
            if yazi_turu == "gelen":
                self.db.cursor.execute(
                    """
                    UPDATE revizyonlar 
                    SET gelen_yazi_no = ?,
                        gelen_yazi_tarih = ?,
                        yazi_turu = 'gelen'
                    WHERE id = ?
                """,
                    (veri.get("gelen_yazi_no"), veri.get("gelen_yazi_tarih"), rev_id),
                )

                # Gelen yazı dokümanı güncellemesi varsa
                if veri.get("yeni_yazi_dosya_yolu"):
                    # Ensure we have a yazi_no; try to infer from filename if missing
                    yazi_no = veri.get("gelen_yazi_no")
                    if not yazi_no:
                        # Try to infer from filename
                        try:
                            from utils import dosyadan_tarih_sayi_cikar
                            bilgiler = dosyadan_tarih_sayi_cikar(os.path.basename(veri.get("yeni_yazi_dosya_yolu")))
                            if bilgiler and bilgiler.get("sayi"):
                                yazi_no = bilgiler.get("sayi")
                                # also update the DB's revizyon row with the inferred yazi_no
                                self.db.cursor.execute(
                                    "UPDATE revizyonlar SET gelen_yazi_no = ?, gelen_yazi_tarih = ? WHERE id = ?",
                                    (yazi_no, bilgiler.get("tarih"), rev_id),
                                )
                                self.logger.info(f"Gelen yazı no filename'dan tahmin edildi: {yazi_no} (rev_id={rev_id})")
                        except Exception:
                            pass
                    if not yazi_no:
                        self.logger.warning(f"Gelen yazı dosyası seçilmiş ancak gelen_yazi_no boş. Dosya kaydedilmeyecek: {veri.get('yeni_yazi_dosya_yolu')}")
                    else:
                        try:
                            with open(veri["yeni_yazi_dosya_yolu"], "rb") as f:
                                dok_veri = f.read()
                                saved = self.db.yazi_dokumani_kaydet(
                                    yazi_no,
                                    os.path.basename(veri["yeni_yazi_dosya_yolu"]),
                                    dok_veri,
                                    "gelen",
                                    veri.get("gelen_yazi_tarih"),
                                )
                                self.logger.info(f"Gelen yazı dokümanı kaydedildi: yazi_no={yazi_no}, result={saved}, rev_id={rev_id}")
                                # Trigger preview for the uploaded letter doc if available
                                try:
                                    if hasattr(self, "_start_yazi_render"):
                                        self._start_yazi_render.emit(dok_veri, self.zoom_factor, yazi_no)
                                except Exception:
                                    self.logger.debug("_start_yazi_render emit failed in rev update flow", exc_info=True)
                        except Exception as e:
                            self.logger.error(f"Gelen yazı dokümanı kaydedilemedi: {e}", exc_info=True)
                            # Trigger preview for the uploaded letter doc if available
                            try:
                                if hasattr(self, "_start_yazi_render"):
                                    self._start_yazi_render.emit(dok_veri, self.zoom_factor, veri.get("gelen_yazi_no"))
                            except Exception:
                                self.logger.debug("_start_yazi_render emit failed in rev update flow", exc_info=True)

            # Giden yazı alanlarını güncelle (sadece giden türündeyse)
            elif yazi_turu == "giden":
                # Onay yazısı güncellemesi
                if veri.get("onay_yazi_no"):
                    self.db.cursor.execute(
                        """
                        UPDATE revizyonlar 
                        SET onay_yazi_no = ?,
                            onay_yazi_tarih = ?,
                            yazi_turu = 'giden'
                        WHERE id = ?
                    """,
                        (veri.get("onay_yazi_no"), veri.get("onay_yazi_tarih"), rev_id),
                    )

                    if veri.get("yeni_onay_dosya_yolu"):
                            onay_no = veri.get("onay_yazi_no")
                            if not onay_no:
                                try:
                                    from utils import dosyadan_tarih_sayi_cikar
                                    bilgiler = dosyadan_tarih_sayi_cikar(os.path.basename(veri.get("yeni_onay_dosya_yolu")))
                                    if bilgiler and bilgiler.get("sayi"):
                                        onay_no = bilgiler.get("sayi")
                                        self.db.cursor.execute(
                                            "UPDATE revizyonlar SET onay_yazi_no = ?, onay_yazi_tarih = ? WHERE id = ?",
                                            (onay_no, bilgiler.get("tarih"), rev_id),
                                        )
                                        self.logger.info(f"Onay yazı no filename'dan tahmin edildi: {onay_no} (rev_id={rev_id})")
                                except Exception:
                                    pass
                            if not onay_no:
                                self.logger.warning(f"Onay yazısı dosyası seçilmiş ancak onay_yazi_no boş. Dosya kaydedilmeyecek: {veri.get('yeni_onay_dosya_yolu')}")
                            else:
                                dok_veri = None
                                try:
                                    with open(veri["yeni_onay_dosya_yolu"], "rb") as f:
                                        dok_veri = f.read()
                                        if not self._confirm_if_suspicious_letter_doc(
                                            rev_id, dok_veri, "onay yazısı"
                                        ):
                                            self.logger.info(
                                                f"Şüpheli onay yazısı yükleme kullanıcı tarafından iptal edildi (rev_id={rev_id})"
                                            )
                                            dok_veri = None
                                    if dok_veri is not None:
                                        self.db.yazi_dokumani_kaydet(
                                            onay_no,
                                            os.path.basename(veri["yeni_onay_dosya_yolu"]),
                                            dok_veri,
                                            "onay",
                                            veri.get("onay_yazi_tarih"),
                                        )
                                        try:
                                            if hasattr(self, "_start_yazi_render"):
                                                self._start_yazi_render.emit(dok_veri, self.zoom_factor, onay_no)
                                        except Exception:
                                            self.logger.debug("_start_yazi_render emit failed in rev update flow", exc_info=True)
                                except Exception as e:
                                    self.logger.error(f"Onay yazı dokümanı kaydedilemedi: {e}", exc_info=True)
                                # Trigger preview if possible
                                try:
                                    if dok_veri is not None and hasattr(self, "_start_yazi_render"):
                                        self._start_yazi_render.emit(dok_veri, self.zoom_factor, veri.get("onay_yazi_no"))
                                except Exception:
                                    self.logger.debug("_start_yazi_render emit failed in rev update flow", exc_info=True)

                # Red yazısı güncellemesi
                if veri.get("red_yazi_no"):
                    self.db.cursor.execute(
                        """
                        UPDATE revizyonlar 
                        SET red_yazi_no = ?,
                            red_yazi_tarih = ?,
                            yazi_turu = 'giden'
                        WHERE id = ?
                    """,
                        (veri.get("red_yazi_no"), veri.get("red_yazi_tarih"), rev_id),
                    )

                    if veri.get("yeni_red_dosya_yolu"):
                            red_no = veri.get("red_yazi_no")
                            if not red_no:
                                try:
                                    from utils import dosyadan_tarih_sayi_cikar
                                    bilgiler = dosyadan_tarih_sayi_cikar(os.path.basename(veri.get("yeni_red_dosya_yolu")))
                                    if bilgiler and bilgiler.get("sayi"):
                                        red_no = bilgiler.get("sayi")
                                        self.db.cursor.execute(
                                            "UPDATE revizyonlar SET red_yazi_no = ?, red_yazi_tarih = ? WHERE id = ?",
                                            (red_no, bilgiler.get("tarih"), rev_id),
                                        )
                                        self.logger.info(f"Red yazı no filename'dan tahmin edildi: {red_no} (rev_id={rev_id})")
                                except Exception:
                                    pass
                            if not red_no:
                                self.logger.warning(f"Red yazısı dosyası seçilmiş ancak red_yazi_no boş. Dosya kaydedilmeyecek: {veri.get('yeni_red_dosya_yolu')}")
                            else:
                                dok_veri = None
                                try:
                                    with open(veri["yeni_red_dosya_yolu"], "rb") as f:
                                        dok_veri = f.read()
                                        if not self._confirm_if_suspicious_letter_doc(
                                            rev_id, dok_veri, "red yazısı"
                                        ):
                                            self.logger.info(
                                                f"Şüpheli red yazısı yükleme kullanıcı tarafından iptal edildi (rev_id={rev_id})"
                                            )
                                            dok_veri = None
                                    if dok_veri is not None:
                                        self.db.yazi_dokumani_kaydet(
                                            red_no,
                                            os.path.basename(veri["yeni_red_dosya_yolu"]),
                                            dok_veri,
                                            "red",
                                            veri.get("red_yazi_tarih"),
                                        )
                                        try:
                                            if hasattr(self, "_start_yazi_render"):
                                                self._start_yazi_render.emit(dok_veri, self.zoom_factor, red_no)
                                        except Exception:
                                            self.logger.debug("_start_yazi_render emit failed in rev update flow", exc_info=True)
                                except Exception as e:
                                    self.logger.error(f"Red yazı dokümanı kaydedilemedi: {e}", exc_info=True)
                                # Trigger preview if possible
                                try:
                                    if dok_veri is not None and hasattr(self, "_start_yazi_render"):
                                        self._start_yazi_render.emit(dok_veri, self.zoom_factor, veri.get("red_yazi_no"))
                                except Exception:
                                    self.logger.debug("_start_yazi_render emit failed in rev update flow", exc_info=True)

            # Revizyon dokümanı güncellemesi (her iki tür için de)
            if veri.get("yeni_rev_dosya_yolu"):
                # Yeni revizyon dokümanı verisi veritabanındaki dokumanlar tablosunda saklanır.
                # Revizyonlar tablosunda artık 'dokuman' alanı yok; db helper kullanarak güncelleme yap.
                with open(veri["yeni_rev_dosya_yolu"], "rb") as f:
                    dosya_verisi = f.read()
                    dosya_adi = os.path.basename(veri["yeni_rev_dosya_yolu"])
                try:
                    # Use the DB helper method to update dokumanlar.
                    updated = self.db.dokumani_guncelle(rev_id, dosya_adi, dosya_verisi)
                    self.logger.debug(f"dokumani_guncelle returned {updated} for rev_id={rev_id}")
                    # Try to emit the preview for the updated rev document
                    try:
                        if hasattr(self, "_start_pdf_render"):
                            self._start_pdf_render.emit(dosya_verisi, self.zoom_factor, rev_id)
                    except Exception:
                        self.logger.debug("_start_pdf_render emit failed in rev update flow", exc_info=True)
                    # Invalidate per-revision dokuman cache so preview updates on selection
                    try:
                        # Ensure the cache is cleared for this revizi̇yon regardless of previous row existence
                        if self.preview_render_service:
                            self.preview_render_service.invalidate_revision(rev_id)
                    except Exception:
                        pass
                except Exception as e:
                    self.logger.error(f"Doküman güncellemesi başarısız: {e}")
                    raise
            self.db.conn.commit()
            self.logger.info(f"Revizyon {rev_id} başarıyla güncellendi ({yazi_turu})")

        except Exception as e:
            self.db.conn.rollback()
            self.logger.error(f"Revizyon güncelleme hatası: {e}", exc_info=True)
            raise

    def arayuzden_projeyi_sil(self):
        """Projeyi listeden sil ve DB'den de kaldır"""
        # Permission check
        if not self._check_write_permission("proje silmek"):
            return
        if not self.secili_proje_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek projeyi seçin.")
            return

        # Proje bilgilerini al
        proje = self.db.proje_bul_id_ile(self.secili_proje_id)
        if not proje:
            return

        proje_kodu = proje[1]  # proje_kodu

        reply = QMessageBox.question(
            self,
            "Projeyi Sil",
            f"'{proje_kodu}' kodlu projeyi ve tüm revizyonlarını silmek istediğinize emin misiniz?\n\nBu işlem geri alınamaz!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                if self.db.projeyi_sil(self.secili_proje_id):
                    self.secili_proje_id = None
                    self.revizyon_agaci.clear()
                    self.detaylari_temizle()
                    self._clear_preview()
                    self._invalidate_filter_cache_and_reload()
                    QMessageBox.information(
                        self, "Başarılı", "Proje başarıyla silindi."
                    )
                else:
                    QMessageBox.critical(self, "Hata", "Proje silinemedi.")
            except Exception as e:
                self.logger.error(f"Proje silme hatası: {e}", exc_info=True)
                QMessageBox.critical(self, "Hata", f"Proje silinirken hata oluştu: {e}")

    def gelen_yazidan_coklu_proje_olustur(self):
        """Gelen yazıdan çoklu proje oluştur/güncelle"""
        self._toplu_yazi_islem_baslat("gelen")

    def giden_yazidan_coklu_proje_olustur(self):
        """Giden yazıdan çoklu proje oluştur/güncelle"""
        self._toplu_yazi_islem_baslat("giden")

    def _toplu_yazi_islem_baslat(self, islem_turu):
        """Toplu yazı işlemlerini başlatır (Gelen/Giden)"""
        try:
            # 1. Yazı dosyasını seç
            # Normalize operation type
            itype = (islem_turu or "").strip().lower()
            # Detect DB action based on islem_turu (case-insensitive)
            if itype in ("gelen", "gelen yazı", "gelen_yazi"):
                db_action = "gelen"
            elif itype in ("onay", "giden onay", "giden_onay"):
                db_action = "onay"
            elif itype in ("notlu onay", "notlu_onay", "notlu"):
                db_action = "notlu_onay"
            elif itype in ("red", "reddet"):
                db_action = "red"
            elif itype == "giden":
                db_action = "giden"
            else:
                db_action = "gelen"

            baslik = "Gelen Yazı Seç" if db_action == "gelen" else "Giden Yazı Seç"
            dosya_yolu, _ = QFileDialog.getOpenFileName(
                self, baslik, "", "PDF Dosyaları (*.pdf);;Tüm Dosyalar (*.*)"
            )
            if not dosya_yolu:
                return

            dosya_adi = os.path.basename(dosya_yolu)

            # 2. Yazı bilgilerini çıkar (Tarih ve Sayı)
            bilgiler = dosyadan_tarih_sayi_cikar(dosya_adi)
            if not bilgiler:
                bilgiler = {}
            yazi_no = bilgiler.get("sayi", "")
            tarih = bilgiler.get("tarih", datetime.datetime.now().strftime("%d.%m.%Y"))

            # 3. Yazı bilgilerini teyit et/düzenle
            dialog = OnayRedDialog(
                self,
                islem_turu.capitalize(),
                title=f"Toplu {islem_turu.capitalize()} Yazı İşlemi",
            )
            dialog.yazi_no_combo.setEditText(yazi_no)
            dialog.tarih_entry.setText(tarih)
            # Dosya yolu zaten seçildi, dialogda göstermeye gerek yok veya set edebiliriz
            dialog.dosya_etiketi.setText(dosya_adi)
            dialog.dosya_yolu = dosya_yolu  # Dialogun dosya yolunu set et

            if not dialog.exec():
                return

            yazi_data = dialog.get_data()
            yazi_no = yazi_data["yazi_no"]
            tarih = yazi_data["tarih"]
            # Dosya yolu dialogdan geleni kullan (değiştirilmiş olabilir)
            final_dosya_yolu = yazi_data["dosya_yolu"] or dosya_yolu

            # Determine yazi_turu (db) based on db_action. We need this BEFORE saving the yazi dokuman.
            db_yazi_turu = "gelen"
            if db_action == "giden":
                # Ask user for onay or red for generic giden operation (do this before saving the yazi dokuman)
                msg = QMessageBox(self)
                msg.setWindowTitle("Yazı Türü")
                msg.setText("Bu giden yazı ne tür bir işlemdir?")
                msg.addButton("Onay", QMessageBox.AcceptRole)
                msg.addButton("Red", QMessageBox.RejectRole)
                msg.addButton("İptal", QMessageBox.DestructiveRole)
                ret = msg.exec()

                if ret == QMessageBox.DestructiveRole:
                    return
                db_yazi_turu = "onay" if ret == 0 else "red"
            elif db_action == "onay":
                db_yazi_turu = "onay"
            elif db_action == "notlu_onay":
                db_yazi_turu = "notlu_onay"
            elif db_action == "red":
                db_yazi_turu = "red"

            # 4. Yazı dosyasını veritabanına kaydet (yazı dokümanını kayıt et)
            with open(final_dosya_yolu, "rb") as f:
                dosya_verisi = f.read()
            # Save the actual yazi document in the yazi_dokumanlari table so it can be opened later
            try:
                saved = self.db.yazi_dokumani_kaydet(
                    yazi_no,
                    os.path.basename(final_dosya_yolu),
                    dosya_verisi,
                    db_yazi_turu,
                    tarih,
                )
                if saved:
                    self.logger.info(f"Yazı dokümanı kaydedildi: yazi_no={yazi_no}, type={db_yazi_turu}")
                else:
                    self.logger.warning(f"Yazı dokümanı kaydedilemedi (db returned falsy): yazi_no={yazi_no}")
            except Exception as e:
                # If saving the yazi dokümanı fails, log error and abort the bulk operation
                self.logger.error(f"Yazı dokümanı kaydı hatası: {e}", exc_info=True)
                QMessageBox.critical(self, "Hata", f"Yazı dokümanı kaydedilemedi: {e}")
                return

            # Yazı türünü belirle (gelen, onay, red)
            # Giden yazılarda onay/red ayrımı kullanıcıya sorulmalı mı?
            # Şimdilik 'giden' ise varsayılan olarak 'onay' kabul edelim veya dialogda sorulmalıydı.
            # OnayRedDialog aslında tek bir işlem için tasarlandı.
            # Basitleştirmek için: 'gelen' -> 'gelen', 'giden' -> 'onay' (varsayılan)
            # Ancak giden yazılar red de olabilir.

            # db_yazi_turu already set above; nothing to do here

            # 5b. Prepare selected projects mapping and selected codes
            selected_projects = self._get_selected_projects()
            if not selected_projects:
                QMessageBox.warning(self, "Uyarı", "Lütfen işlem için en az bir proje seçin.")
                return
            projeler_dict = self._prepare_projeler_dict_for_action(selected_projects, db_action)
            secilen_kodlar = list(projeler_dict.keys())

            # 6. İşlemi uygula
            basarili_sayisi = 0
            for kod in secilen_kodlar:
                pid = projeler_dict[kod]["id"]
                sonuc = "Hata"

                if db_yazi_turu == "gelen":
                    if self.db.son_revizyona_gelen_yazi_ekle(pid, yazi_no, tarih):
                        sonuc = "Basarili"
                elif db_yazi_turu == "onay":
                    sonuc = self.db.son_revizyonu_onayla(pid, yazi_no, tarih)
                elif db_yazi_turu == "notlu_onay":
                    sonuc = self.db.son_revizyonu_notlu_onayla(pid, yazi_no, tarih)
                elif db_yazi_turu == "red":
                    sonuc = self.db.son_revizyonu_reddet(pid, yazi_no, tarih)

                if sonuc == "Basarili":
                    basarili_sayisi += 1
                else:
                    self.logger.error(f"Toplu işlem hatası ({kod}): {sonuc}")

            # 7. Sonuç bildir - clear cache and reload projects
            self._invalidate_filter_cache_and_reload()
            QMessageBox.information(
                self,
                "İşlem Tamamlandı",
                f"{len(secilen_kodlar)} projeden {basarili_sayisi} tanesi başarıyla güncellendi.",
            )

        except Exception as e:
            self.logger.error(f"Toplu yazı işlemi hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"İşlem sırasında hata oluştu: {e}")

    def _get_selected_projects(self):
        """Return a dict of selected projects (id -> ProjeModel)."""
        selected_projects = {}
        # List view selected items
        try:
            list_items = self.proje_listesi_widget.selectedItems()
        except Exception:
            list_items = []
        for it in list_items:
            try:
                p = it.data(Qt.UserRole)
                if p:
                    selected_projects[p.id] = p
            except Exception:
                pass
        # Tree view selected items
        try:
            tree_items = self.proje_agaci_widget.selectedItems()
        except Exception:
            tree_items = []
        for it in tree_items:
            try:
                p = it.data(0, Qt.UserRole)
                if p and getattr(p, 'id', None):
                    selected_projects[p.id] = p
            except Exception:
                pass
        return selected_projects

    def _prepare_projeler_dict_for_action(self, selected_projects: dict, db_action: str) -> dict:
        projeler_dict = {}
        for pid, p in selected_projects.items():
            info = {"isim": p.proje_ismi, "id": p.id}
            try:
                revs = self.db.revizyonlari_getir(p.id)
                latest = revs[0] if revs else None
                # Map db_action to rev field to check
                if db_action == 'gelen' and latest and latest.gelen_yazi_no:
                    info['uyari'] = f"Mevcut gelen yazı: {latest.gelen_yazi_no} ({latest.revizyon_kodu})"
                if db_action == 'onay' and latest and latest.onay_yazi_no:
                    info['uyari'] = f"Mevcut onay yazı: {latest.onay_yazi_no} ({latest.revizyon_kodu})"
                if db_action == 'notlu_onay' and latest and latest.onay_yazi_no:
                    info['uyari'] = f"Mevcut notlu onay yazı: {latest.onay_yazi_no} ({latest.revizyon_kodu})"
                if db_action == 'red' and latest and latest.red_yazi_no:
                    info['uyari'] = f"Mevcut red yazı: {latest.red_yazi_no} ({latest.revizyon_kodu})"
            except Exception:
                pass
            projeler_dict[p.proje_kodu] = info
        return projeler_dict

    def guncelle_gosterge_panelini(self):
        """Gösterge panelindeki sayıları güncelle"""
        try:
            # Check if the dashboard panel exists
            if not hasattr(self, "istatistik_etiketleri"):
                return

            toplam = len(self.tum_projeler)

            # İstatistikleri hesapla
            onayli = sum(1 for p in self.tum_projeler if p.durum == Durum.ONAYLI.value)
            red = sum(1 for p in self.tum_projeler if p.durum == Durum.REDDEDILDI.value)
            notlu = sum(
                1 for p in self.tum_projeler if p.durum == Durum.ONAYLI_NOTLU.value
            )
            bekleyen = toplam - (onayli + red + notlu)

            # TSE İstatistikleri
            tse_gonderilen = sum(
                1 for p in self.tum_projeler if getattr(p, "tse_gonderildi", 0)
            )
            tse_gonderilmeyen = toplam - tse_gonderilen

            # Etiketleri güncelle - yeni label isimleriyle
            if "Toplam Görüntülenen Proje:" in self.istatistik_etiketleri:
                self.istatistik_etiketleri["Toplam Görüntülenen Proje:"].setText(
                    str(toplam)
                )
            if "Onaylı:" in self.istatistik_etiketleri:
                self.istatistik_etiketleri["Onaylı:"].setText(str(onayli))
            if "Notlu Onaylı:" in self.istatistik_etiketleri:
                self.istatistik_etiketleri["Notlu Onaylı:"].setText(str(notlu))
            if "Reddedilen:" in self.istatistik_etiketleri:
                self.istatistik_etiketleri["Reddedilen:"].setText(str(red))
            if "Beklemede (Onaysız):" in self.istatistik_etiketleri:
                self.istatistik_etiketleri["Beklemede (Onaysız):"].setText(
                    str(bekleyen)
                )

            if "TSE'ye Gönderilen:" in self.istatistik_etiketleri:
                self.istatistik_etiketleri["TSE'ye Gönderilen:"].setText(
                    str(tse_gonderilen)
                )
            if "Henüz Gönderilmeyen:" in self.istatistik_etiketleri:
                self.istatistik_etiketleri["Henüz Gönderilmeyen:"].setText(
                    str(tse_gonderilmeyen)
                )

            # Tür Dağılımı: per-type status breakdown
            try:
                self._tur_stats = {}
                for p in self.tum_projeler:
                    tur = p.proje_turu or "(Belirtilmemiş)"
                    stat = self._tur_stats.setdefault(
                        tur, {"total": 0, "onayli": 0, "notlu": 0, "red": 0}
                    )
                    stat["total"] += 1
                    if p.durum == Durum.ONAYLI.value:
                        stat["onayli"] += 1
                    elif p.durum == Durum.ONAYLI_NOTLU.value:
                        stat["notlu"] += 1
                    elif p.durum == Durum.REDDEDILDI.value:
                        stat["red"] += 1

                # Update table view if exists
                if hasattr(self, "rapor_tur_table"):
                    rows = sorted(
                        self._tur_stats.items(),
                        key=lambda kv: kv[1]["total"],
                        reverse=True,
                    )
                    self.rapor_tur_table.setRowCount(len(rows))
                    for idx, (tur, val) in enumerate(rows):
                        total = val["total"]
                        onayli = val["onayli"]
                        notlu = val["notlu"]
                        red = val["red"]
                        from PySide6.QtWidgets import QTableWidgetItem
                        from PySide6.QtGui import QColor, QBrush
                        from PySide6.QtCore import Qt as _Qt

                        # Name
                        item_name = QTableWidgetItem(str(tur))
                        item_name.setTextAlignment(_Qt.AlignLeft | _Qt.AlignVCenter)
                        self.rapor_tur_table.setItem(idx, 0, item_name)
                        # Totals and statuses, align right and colorize statuses
                        item_total = QTableWidgetItem(str(total))
                        item_total.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
                        self.rapor_tur_table.setItem(idx, 1, item_total)
                        item_onayli = QTableWidgetItem(str(onayli))
                        item_onayli.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
                        item_onayli.setForeground(QBrush(QColor("#1a9a2f")))
                        self.rapor_tur_table.setItem(idx, 2, item_onayli)
                        item_notlu = QTableWidgetItem(str(notlu))
                        item_notlu.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
                        item_notlu.setForeground(QBrush(QColor("#e8743b")))
                        self.rapor_tur_table.setItem(idx, 3, item_notlu)
                        item_red = QTableWidgetItem(str(red))
                        item_red.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
                        item_red.setForeground(QBrush(QColor("#ff4d4f")))
                        self.rapor_tur_table.setItem(idx, 4, item_red)
                    if not getattr(self, "_rapor_tur_table_sized_once", False):
                        try:
                            self.rapor_tur_table.resizeColumnsToContents()
                            self._rapor_tur_table_sized_once = True
                        except Exception:
                            pass
                else:
                    # fallback text representation for backward compatibility
                    text = ""
                    for tur, val in sorted(
                        self._tur_stats.items(),
                        key=lambda kv: kv[1]["total"],
                        reverse=True,
                    ):
                        text += f"{tur}: {val['total']} (Onaylı: {val['onayli']}, Notlu Onaylı: {val['notlu']}, Reddedilen: {val['red']})\n"
                    if hasattr(self, "rapor_tur_listesi"):
                        self.rapor_tur_listesi.setText(
                            text if text else "Proje türü bilgisi yok"
                        )
            except Exception as e:
                self.logger.warning(f"Tür dağılımı oluşturulurken hata: {e}")

        except Exception as e:
            self.logger.error(f"Gösterge paneli güncellenirken hata: {e}")

    def projeleri_filtrele(self, text=None):
        """Arama metnine göre projeleri filtrele"""
        # Bu metod arama kutusu değiştiğinde çağrılır.
        # Filtreleme UI seviyesinde uygulanır; self.tum_projeler içindeki veriler üzerinde çalışır.
        try:
            # Normalize a quick safe representation of tum_projeler
            if not isinstance(self.tum_projeler, list):
                # attempt to coerce iterable to list
                try:
                    self.tum_projeler = list(self.tum_projeler)
                except Exception:
                    self.logger.debug("projeleri_filtrele: tum_projeler non-iterable, resetting to []")
                    self.tum_projeler = []
            sorgu = (text or "").strip().lower()
            if not sorgu:
                filtered = list(self.tum_projeler)
            else:
                filtered = []
                for p in self.tum_projeler:
                    kod = (getattr(p, "proje_kodu", "") or "").lower()
                    isim = (getattr(p, "proje_ismi", "") or "").lower()
                    hiy = (getattr(p, "hiyerarsi", "") or "").lower()
                    if sorgu in kod or sorgu in isim or sorgu in hiy:
                        filtered.append(p)
            # populate UI with filtered list
            self._populate_projects_ui(filtered)
        except Exception as e:
            self.logger.error(f"projeleri_filtrele hata: {e}", exc_info=True)

    def yenile(self, keep_rev_id: Optional[int] = None, keep_project_id: Optional[int] = None):
        """Listeyi ve veritabanını yenile; isteğe bağlı olarak seçimleri korur."""
        self.db.cleanup_connections()  # Bağlantıları temizle
        # keep_project_id yoksa mevcut seçili projeyi koru; rev id verildiyse aynı rev'i seçmeyi dene
        target_project = keep_project_id if keep_project_id is not None else getattr(self, "secili_proje_id", None)
        self._invalidate_filter_cache_and_reload(keep_project_id=target_project, keep_rev_id=keep_rev_id)

    def _populate_projects_ui(self, projects: List[ProjeModel]):
        """Populate the list and tree widgets with `projects`. Safe and idempotent."""
        try:
            # Use ProjectPanel's load_projects if available
            if hasattr(self, "project_panel") and hasattr(
                self.project_panel, "load_projects"
            ):
                # Fetch and set categories
                try:
                    kategoriler = self.db.get_kategoriler()
                    if hasattr(self.project_panel, "set_categories"):
                        self.project_panel.set_categories(kategoriler)
                except Exception as e:
                    self.logger.error(f"Kategoriler yüklenirken hata: {e}")

                self.project_panel.load_projects(projects)
                return

            # Fallback to manual population
            # Clear list and tree
            try:
                self.proje_listesi_widget.clear()
            except Exception:
                pass
            try:
                self.proje_agaci_widget.clear()
            except Exception:
                pass

            # Reset category map
            self.kategori_items_map = {}
            kategorisiz_item = QTreeWidgetItem(self.proje_agaci_widget, ["Kategorisiz"])
            kategorisiz_item.setData(0, KATEGORI_ID_ROL, 0)
            kategorisiz_item.setFlags(Qt.ItemIsDropEnabled)
            self.kategori_items_map[0] = kategorisiz_item

            # Create category nodes
            try:
                kategoriler = self.db.get_kategoriler()
            except Exception:
                kategoriler = []
            for cid, isim, parent in kategoriler:
                try:
                    parent_item = (
                        self.kategori_items_map.get(parent) if parent else None
                    )
                    if parent_item:
                        item = QTreeWidgetItem(parent_item, [isim])
                    else:
                        item = QTreeWidgetItem(self.proje_agaci_widget, [isim])
                    item.setData(0, KATEGORI_ID_ROL, cid)
                    self.kategori_items_map[cid] = item
                except Exception:
                    continue

            # Append projects with colors and emojis
            for p in projects:
                try:
                    # Determine emoji and color based on status
                    emoji = "⚪"  # Default: Waiting
                    color = None

                    if p.durum == "Onayli":  # Fixed: was "Onaylandı"
                        emoji = "🟢"
                        color = QColor("#d4edda")  # Light Green
                    elif p.durum == "Notlu Onayli":  # Fixed: was "Onaylandı (Notlu)"
                        emoji = "🟠"
                        color = QColor("#fff3cd")  # Light Orange
                    elif p.durum == "Reddedildi":
                        emoji = "🔴"
                        color = QColor("#f8d7da")  # Light Red

                    text = f"{p.proje_kodu} - {p.proje_ismi}"
                    display_text = f"{emoji} {text}"

                    # List item with color
                    list_item = QListWidgetItem(display_text)
                    list_item.setData(Qt.UserRole, p)
                    if color:
                        from PySide6.QtGui import QBrush

                        list_item.setBackground(QBrush(color))
                    self.proje_listesi_widget.addItem(list_item)

                    # Tree item with color
                    kategor_id = p.kategori_id if p.kategori_id is not None else 0
                    parent_item = self.kategori_items_map.get(
                        kategor_id, kategorisiz_item
                    )

                    proj_item = QTreeWidgetItem(parent_item, [display_text])
                    proj_item.setData(0, Qt.UserRole, p)
                    if color:
                        proj_item.setBackground(0, color)
                except Exception:
                    continue

            try:
                self.proje_agaci_widget.expandAll()
            except Exception:
                pass
            # If we had a previously selected project, reselect it after reload
            try:
                spid = getattr(self, 'secili_proje_id', None)
                if spid:
                    # Try to select in list view first
                    selected = False
                    try:
                        for i in range(self.proje_listesi_widget.count()):
                            li = self.proje_listesi_widget.item(i)
                            p = li.data(Qt.UserRole)
                            if p and getattr(p, 'id', None) == spid:
                                self.proje_listesi_widget.setCurrentItem(li)
                                selected = True
                                break
                    except Exception:
                        pass
                    if not selected:
                        # Try tree view
                        try:
                            for i in range(self.proje_agaci_widget.topLevelItemCount()):
                                ti = self.proje_agaci_widget.topLevelItem(i)
                                p = ti.data(0, Qt.UserRole)
                                if p and getattr(p, 'id', None) == spid:
                                    self.proje_agaci_widget.setCurrentItem(ti)
                                    selected = True
                                    break
                        except Exception:
                            pass
                    if selected:
                        try:
                            # Update details and revisions
                            proj = self.db.proje_bul_id_ile(spid)
                            if proj:
                                self.proje_detaylarini_goster(proj)
                                self.revizyonlari_yukle(spid)
                                # Log whether a revision reselect will be attempted
                                self.logger.debug(f"_populate_projects_ui: reloaded project {spid}, attempting to reselect previous rev")
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"_populate_projects_ui hata: {e}", exc_info=True)

    def _goruntule_dokuman(self):
        """Seçili revizyonun dokümanını harici görüntüleyicide aç"""
        item = self._get_secili_revizyon_item()
        if not item:
            return

        rev: RevizyonModel = item.data(0, Qt.UserRole)
        if not rev:
            return

        try:
            self._open_revision_document(rev)
        except Exception as e:
            self.logger.error(f"Doküman görüntüleme hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Doküman açılamadı: {e}")
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Font ayarları
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    window = AnaPencere()
    window.show()
    sys.exit(app.exec())
