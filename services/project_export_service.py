"""
Project Export Service for exporting projects to folder structure.

This service exports all projects from the database to a hierarchical
folder structure based on project types.
"""

import os
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from PySide6.QtCore import QThread, Signal

from database import ProjeTakipDB


class ProjectExportWorker(QThread):
    """
    Worker thread for exporting projects to folder structure.
    
    Signals:
        progress(int, int): Current progress (current, total)
        status(str): Current status message
        completed(int, int, int): Export completed (success_count, error_count, total_files)
        error(str): Error message
    """
    
    progress = Signal(int, int)
    status = Signal(str)
    completed = Signal(int, int, int)
    error = Signal(str)
    
    # Main folder name
    MAIN_FOLDER_NAME = "Adapazarı Projeler"
    
    def __init__(self, db_path: str, target_folder: str):
        """
        Initialize the export worker.
        
        Args:
            db_path: Path to the database file
            target_folder: Target folder to export projects to
        """
        super().__init__()
        self.db_path = db_path
        self.target_folder = target_folder
        self.logger = logging.getLogger(__name__)
        self._cancelled = False
        
        # Counters
        self.success_count = 0
        self.error_count = 0
        self.total_files = 0
    
    def cancel(self):
        """Request cancellation of the export."""
        self._cancelled = True
    
    def run(self):
        """Main export logic."""
        db = None
        try:
            # Create database connection
            db = ProjeTakipDB(self.db_path)
        except Exception as e:
            self.error.emit(f"Veritabanı bağlantısı kurulamadı: {e}")
            return
        
        try:
            # Create main folder
            main_folder = Path(self.target_folder) / self.MAIN_FOLDER_NAME
            main_folder.mkdir(parents=True, exist_ok=True)
            
            # Get all projects
            projeler = db.projeleri_listele()
            toplam = len(projeler)
            
            if toplam == 0:
                self.completed.emit(0, 0, 0)
                return
            
            self.status.emit(f"Toplam {toplam} proje bulundu...")
            
            for i, proje in enumerate(projeler, 1):
                if self._cancelled:
                    self.status.emit("İptal edildi")
                    break
                
                self.progress.emit(i, toplam)
                self.status.emit(f"İşleniyor: {proje.proje_kodu} - {proje.proje_ismi}")
                
                try:
                    self._export_project(db, proje, main_folder)
                except Exception as e:
                    self.logger.error(f"Proje export hatası ({proje.proje_kodu}): {e}")
                    self.error_count += 1
            
            self.completed.emit(self.success_count, self.error_count, self.total_files)
            
        except Exception as e:
            self.logger.error(f"Export hatası: {e}", exc_info=True)
            self.error.emit(f"Export hatası: {e}")
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    try:
                        db.cleanup_connections()
                    except Exception:
                        pass
    
    def _export_project(self, db: ProjeTakipDB, proje, main_folder: Path):
        """Export a single project."""
        # Determine project type folder
        proje_turu = proje.proje_turu or "Diğer"
        proje_turu = self._clean_folder_name(proje_turu)
        
        # Create project folder: [ProjectType]/[ProjectCode]_[ProjectName]
        proje_klasor_adi = f"{proje.proje_kodu}_{proje.proje_ismi}"
        proje_klasor_adi = self._clean_folder_name(proje_klasor_adi)
        
        proje_folder = main_folder / proje_turu / proje_klasor_adi
        proje_folder.mkdir(parents=True, exist_ok=True)
        
        # Create subfolders
        revizyonlar_folder = proje_folder / "Revizyonlar"
        gelen_yazilar_folder = proje_folder / "Gelen Yazılar"
        giden_yazilar_folder = proje_folder / "Giden Yazılar"
        
        revizyonlar_folder.mkdir(exist_ok=True)
        gelen_yazilar_folder.mkdir(exist_ok=True)
        giden_yazilar_folder.mkdir(exist_ok=True)
        
        # Get revisions for this project
        revizyonlar = db.revizyonlari_getir(proje.id)
        
        for rev in revizyonlar:
            if self._cancelled:
                return
            
            # Export revision document
            self._export_revision_document(db, rev, revizyonlar_folder)
            
            # Export incoming letter document if exists
            if rev.gelen_yazi_no:
                self._export_letter_document(
                    db, rev.gelen_yazi_no, gelen_yazilar_folder, rev.gelen_yazi_tarih, "gelen"
                )
            
            # Export outgoing letter documents if exists
            if rev.onay_yazi_no:
                self._export_letter_document(
                    db, rev.onay_yazi_no, giden_yazilar_folder, rev.onay_yazi_tarih, "onay"
                )
            if rev.red_yazi_no:
                self._export_letter_document(
                    db, rev.red_yazi_no, giden_yazilar_folder, rev.red_yazi_tarih, "red"
                )
    
    def _export_revision_document(self, db: ProjeTakipDB, rev, folder: Path):
        """Export revision document to folder."""
        try:
            doc_data = db.dokumani_getir(rev.id)
            if not doc_data:
                return
            
            dosya_adi, dosya_verisi = doc_data
            
            # Create filename: RevXX_[OriginalName]
            rev_prefix = f"{rev.revizyon_kodu}_"
            safe_name = self._clean_folder_name(dosya_adi)
            final_name = f"{rev_prefix}{safe_name}"
            
            file_path = self._get_unique_path(folder, final_name)
            
            with open(file_path, "wb") as f:
                f.write(dosya_verisi)
            
            self.success_count += 1
            self.total_files += 1
            
        except Exception as e:
            self.logger.error(f"Revizyon dokümanı kaydedilemedi (ID: {rev.id}): {e}")
            self.error_count += 1
    
    def _export_letter_document(
        self,
        db: ProjeTakipDB,
        yazi_no: str,
        folder: Path,
        yazi_tarih: Optional[str] = None,
        yazi_turu: Optional[str] = None,
    ):
        """Export letter document to folder."""
        try:
            doc_data = db.yazi_dokumani_getir(yazi_no, yazi_tarih, yazi_turu)
            if not doc_data:
                return
            
            dosya_adi, dosya_verisi = doc_data
            
            # Create filename: [YazıNo]_[OriginalName]
            safe_yazi_no = self._clean_folder_name(yazi_no)
            safe_name = self._clean_folder_name(dosya_adi)
            final_name = f"{safe_yazi_no}_{safe_name}"
            
            file_path = self._get_unique_path(folder, final_name)
            
            with open(file_path, "wb") as f:
                f.write(dosya_verisi)
            
            self.success_count += 1
            self.total_files += 1
            
        except Exception as e:
            self.logger.error(f"Yazı dokümanı kaydedilemedi ({yazi_no}): {e}")
            self.error_count += 1
    
    def _clean_folder_name(self, name: str) -> str:
        """Clean a string to be used as folder/file name."""
        if not name:
            return "Bilinmeyen"
        
        # Characters not allowed in file/folder names
        forbidden_chars = '<>:"/\\|?*'
        result = name
        for char in forbidden_chars:
            result = result.replace(char, "_")
        
        # Remove leading/trailing spaces and dots
        result = result.strip(" .")
        
        # Limit length
        if len(result) > 100:
            result = result[:100]
        
        return result or "Bilinmeyen"
    
    def _get_unique_path(self, folder: Path, filename: str) -> Path:
        """Get a unique file path, appending number if file exists."""
        file_path = folder / filename
        
        if not file_path.exists():
            return file_path
        
        # Split name and extension
        name, ext = os.path.splitext(filename)
        counter = 1
        
        while True:
            new_name = f"{name}_{counter}{ext}"
            file_path = folder / new_name
            if not file_path.exists():
                return file_path
            counter += 1
