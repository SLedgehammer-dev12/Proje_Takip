"""
Project Export Dialog for exporting projects to folder structure.

Provides a user interface for selecting target folder and showing
export progress.
"""

import os
import logging
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QFileDialog,
    QMessageBox,
    QGroupBox,
)
from PySide6.QtCore import Qt

from services.project_export_service import ProjectExportWorker


class ProjectExportDialog(QDialog):
    """
    Dialog for exporting projects to folder structure.
    
    Features:
    - Folder selection
    - Progress bar
    - Status display
    - Cancel button
    - Result summary
    """
    
    def __init__(self, db_path: str, parent=None):
        """
        Initialize the export dialog.
        
        Args:
            db_path: Path to the database file
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_path = db_path
        self.target_folder = ""
        self.worker: Optional[ProjectExportWorker] = None
        self.logger = logging.getLogger(__name__)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("📁 Projeleri Klasöre Çıkar")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # --- Folder Selection ---
        folder_group = QGroupBox("Hedef Klasör")
        folder_layout = QHBoxLayout(folder_group)
        
        self.folder_label = QLabel("Klasör seçilmedi")
        self.folder_label.setStyleSheet("color: #666;")
        folder_layout.addWidget(self.folder_label, 1)
        
        self.select_folder_btn = QPushButton("📂 Klasör Seç...")
        self.select_folder_btn.clicked.connect(self._select_folder)
        folder_layout.addWidget(self.select_folder_btn)
        
        layout.addWidget(folder_group)
        
        # --- Progress Section ---
        progress_group = QGroupBox("İlerleme")
        progress_layout = QVBoxLayout(progress_group)
        
        self.status_label = QLabel("Bekliyor...")
        self.status_label.setWordWrap(True)
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        self.detail_label = QLabel("")
        self.detail_label.setStyleSheet("color: #888; font-size: 10pt;")
        progress_layout.addWidget(self.detail_label)
        
        layout.addWidget(progress_group)
        
        # --- Info Section ---
        info_label = QLabel(
            "ℹ️ Tüm projeler seçilen klasöre aşağıdaki yapıda çıkarılacak:\n"
            "   Adapazarı Projeler / [Proje Türü] / [Proje Kodu]_[İsim] / Revizyonlar, Gelen/Giden Yazılar"
        )
        info_label.setStyleSheet("color: #555; background: #f5f5f5; padding: 10px; border-radius: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # --- Buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_btn = QPushButton("▶️ Başlat")
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("font-weight: bold; padding: 8px 20px;")
        self.start_btn.clicked.connect(self._start_export)
        button_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("İptal")
        self.cancel_btn.clicked.connect(self._cancel_or_close)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _select_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Hedef Klasörü Seçin",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.target_folder = folder
            self.folder_label.setText(folder)
            self.folder_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
            self.start_btn.setEnabled(True)
            self.status_label.setText("Başlatmak için 'Başlat' butonuna tıklayın.")
    
    def _start_export(self):
        """Start the export process."""
        if not self.target_folder:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce hedef klasörü seçin.")
            return
        
        # Confirm
        reply = QMessageBox.question(
            self,
            "Export Onayı",
            f"Tüm projeler şu klasöre çıkarılacak:\n\n{self.target_folder}\n\nDevam edilsin mi?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Disable UI
        self.start_btn.setEnabled(False)
        self.select_folder_btn.setEnabled(False)
        self.cancel_btn.setText("İptal Et")
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # Create and start worker
        self.worker = ProjectExportWorker(self.db_path, self.target_folder)
        self.worker.progress.connect(self._on_progress)
        self.worker.status.connect(self._on_status)
        self.worker.completed.connect(self._on_completed)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_progress(self, current: int, total: int):
        """Handle progress update."""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
            self.detail_label.setText(f"Proje: {current} / {total}")
    
    def _on_status(self, message: str):
        """Handle status update."""
        self.status_label.setText(message)
    
    def _on_completed(self, success: int, errors: int, total_files: int):
        """Handle export completion."""
        self.progress_bar.setValue(100)
        
        # Show result
        result_msg = (
            f"✅ Export tamamlandı!\n\n"
            f"📄 Toplam dosya: {total_files}\n"
            f"✓ Başarılı: {success}\n"
        )
        
        if errors > 0:
            result_msg += f"✗ Hatalı: {errors}\n"
        
        result_msg += f"\n📁 Hedef: {self.target_folder}/Adapazarı Projeler"
        
        self.status_label.setText("✅ Tamamlandı!")
        self.status_label.setStyleSheet("color: #2e7d32; font-weight: bold; font-size: 12pt;")
        
        QMessageBox.information(self, "Export Tamamlandı", result_msg)
        
        # Update UI
        self.cancel_btn.setText("Kapat")
        self.start_btn.setEnabled(True)
        self.select_folder_btn.setEnabled(True)
    
    def _on_error(self, message: str):
        """Handle export error."""
        self.status_label.setText(f"❌ Hata: {message}")
        self.status_label.setStyleSheet("color: #c62828;")
        
        QMessageBox.critical(self, "Export Hatası", message)
        
        # Update UI
        self.cancel_btn.setText("Kapat")
        self.start_btn.setEnabled(True)
        self.select_folder_btn.setEnabled(True)
    
    def _cancel_or_close(self):
        """Cancel export or close dialog."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "İptal Et",
                "Export işlemi devam ediyor. İptal edilsin mi?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker.cancel()
                self.worker.wait()
                self.status_label.setText("İptal edildi")
                self.cancel_btn.setText("Kapat")
        else:
            self.accept()
    
    def closeEvent(self, event):
        """Handle dialog close."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        event.accept()
