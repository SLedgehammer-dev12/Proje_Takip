"""
Main controller placeholder for `AnaPencere` business logic

This file will be expanded later: we'll move DB interactions, worker setup, and
data-loading methods from `main_window.py` into this controller.
"""

from typing import Any
from PySide6.QtCore import QThread
from widgets import PdfRenderWorker


class MainController:
    def __init__(self, window: Any):
        self.window = window
        # controller has quick access to DB object and filter manager
        # Keep a dynamic reference via property to avoid stale DB references when the window switches DB
        # (Controller will always read self.window.db)
        # self.db intentionally not stored to avoid stale pointer
        self.filter_manager = getattr(window, "filter_manager", None)

    @property
    def db(self):
        # Always retrieve the DB instance directly from the window to avoid stale references
        return getattr(self.window, "db", None)

    def initialize(self):
        """Initialize controller resources when called from main window."""
        # Placeholder: start any background processes or workers if needed
        return

    def get_projects(self):
        """Return list of projects based on filters (abstracted DB call)."""
        if self.filter_manager and self.filter_manager.active_filters:
            return self.filter_manager.get_filtered_projects()
        if self.db:
            return self.db.projeleri_listele()
        return []

    def get_revisions(self, proje_id: int):
        """Return list of revisions for a project (DB abstraction)."""
        if not self.db:
            return []
        return self.db.revizyonlari_getir(proje_id)

    def setup_pdf_worker(self):
        """Create and start a PDF render worker thread, connect to window handlers."""
        try:
            self.render_thread = QThread()
            try:
                self.render_thread.setObjectName("MainControllerPdfThread")
                self.render_thread.setParent(self.window)
            except Exception:
                pass
            self.pdf_worker = PdfRenderWorker(
                performance_mode=bool(
                    getattr(self.window, "is_performance_mode_enabled", lambda: False)()
                )
            )
            self.pdf_worker.moveToThread(self.render_thread)
            # Connect signals from window to worker and worker to window
            # window._start_pdf_render was introduced in AnaPencere
            self.window._start_pdf_render.connect(self.pdf_worker.render_page)
            # Connect the new yazi preview signal to worker's render_yazi slot
            try:
                self.window._start_yazi_render.connect(self.pdf_worker.render_yazi)
            except Exception:
                pass
            self.pdf_worker.image_ready.connect(self.window._on_image_ready)
            # New: yazi render results
            try:
                self.pdf_worker.yazi_image_ready.connect(self.window._on_yazi_image_ready)
            except Exception:
                pass
            self.pdf_worker.error.connect(self.window._on_image_error)
            self._render_connections = [
                (self.window._start_pdf_render, self.pdf_worker.render_page),
                (self.pdf_worker.image_ready, self.window._on_image_ready),
                (self.pdf_worker.error, self.window._on_image_error),
            ]
            self.render_thread.start()
        except Exception:
            pass

    def configure_pdf_worker_profile(self, performance_mode: bool):
        try:
            worker = getattr(self, "pdf_worker", None)
            if worker is not None and hasattr(worker, "configure_performance_mode"):
                worker.configure_performance_mode(performance_mode)
        except Exception:
            pass

    def cleanup_pdf_worker(self):
        """PERFORMANCE: Improved thread cleanup with timeout to prevent hanging."""
        try:
            if hasattr(self, "render_thread") and self.render_thread:
                try:
                    if self.render_thread.isRunning():
                        # SAFETY: Try graceful shutdown first (max 3 seconds)
                        self.render_thread.quit()
                        if not self.render_thread.wait(3000):  # 3 second timeout
                            # SAFETY: Force terminate if not responding
                            try:
                                self.render_thread.terminate()
                                self.render_thread.wait(1000)  # 1 second for terminate
                            except Exception:
                                pass
                except Exception:
                    pass
                try:
                    self.render_thread.deleteLater()
                except Exception:
                    pass
            # Attempt to disconnect signals safely
            if hasattr(self, "_render_connections"):
                import warnings

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    for sig, slot in self._render_connections:
                        try:
                            sig.disconnect(slot)
                        except Exception:
                            pass
        except Exception:
            pass
