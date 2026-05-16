"""Arka plan veri yükleyici (projeler ve revizyonlar).

UI thread'i bloklamamak için her istekte ayrı bir QThread içinde çalışır.
Read connection pool kullanarak bağlantı açma/kapama overhead'ini azaltır.
"""

from typing import Optional, List
import os
from PySide6.QtCore import QObject, Signal, Slot


class DataLoadWorker(QObject):
    projects_loaded = Signal(int, list)          # token, projects
    revisions_loaded = Signal(int, int, list)    # token, proje_id, revisions
    error = Signal(int, str)                     # token, message
    finished = Signal(int)                       # token

    def __init__(self, db_path: str, mode: str, token: int, proje_id: Optional[int] = None, sort_by: str = "id_desc"):
        super().__init__()
        self.db_path = db_path
        self.mode = mode
        self.token = token
        self.proje_id = proje_id
        self.sort_by = sort_by

    @Slot()
    def run(self):
        db = None
        conn = None
        try:
            from database import ProjeTakipDB

            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Veritabanı bulunamadı: {self.db_path}")

            db = ProjeTakipDB(self.db_path, allow_create=False)
            conn = db.acquire_read_connection()
            db.cursor = conn.cursor()
            
            if self.mode == "projects":
                projects: List = db.projeleri_listele(sort_by=self.sort_by)
                self.projects_loaded.emit(self.token, projects)
            elif self.mode == "revisions" and self.proje_id is not None:
                revisions: List = db.revizyonlari_getir(self.proje_id)
                self.revisions_loaded.emit(self.token, self.proje_id, revisions)
        except Exception as e:
            try:
                self.error.emit(self.token, str(e))
            except Exception:
                pass
        finally:
            try:
                if conn and db:
                    db.release_read_connection(conn)
                if db:
                    db.close()
            except Exception:
                pass
            try:
                self.finished.emit(self.token)
            except Exception:
                pass
