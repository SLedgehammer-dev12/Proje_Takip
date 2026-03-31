import logging
import datetime
import os
import shutil
import sqlite3
import time
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from utils import get_class_logger


class BackupService:
    def __init__(self, db_path: str, backup_folder: str = "veritabani_yedekleri"):
        self.db_path = db_path
        self.backup_root = backup_folder
        self.backup_folder = self._resolve_backup_folder(backup_folder)
        self.logger = get_class_logger(self)
        self._ensure_backup_folder()

    def _resolve_backup_folder(self, backup_folder: str) -> str:
        normalized_path = str(Path(self.db_path).resolve())
        db_name = Path(self.db_path).stem or "varsayilan"
        safe_db_name = "".join(
            ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in db_name
        ).strip("_") or "varsayilan"
        path_hash = hashlib.sha1(normalized_path.encode("utf-8")).hexdigest()[:10]
        return str(Path(backup_folder) / f"{safe_db_name}_{path_hash}")

    def _ensure_backup_folder(self):
        """Yedek klasörünü oluştur"""
        try:
            Path(self.backup_folder).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Yedek klasörü hazır: {self.backup_folder}")
        except Exception as e:
            self.logger.error(f"Yedek klasörü oluşturulamadı: {e}")

    def create_backup(
        self, connection: sqlite3.Connection, description: str = "Otomatik"
    ) -> Optional[str]:
        """
        Veritabanının yedeğini al
        """
        # Use sqlite3's backup API to produce a consistent copy of the DB.
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{self.backup_folder}/yedek_{description}_{timestamp}.db"

        max_retries = 5
        delay_s = 0.1
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                # Ensure current connection is in a consistent state
                try:
                    connection.commit()
                except Exception:
                    # If commit fails, continue to backup attempt (best-effort)
                    pass

                # Create destination connection (this creates the file)
                dest_conn = sqlite3.connect(backup_file)
                try:
                    # Perform backup from the given connection
                    connection.backup(dest_conn)
                finally:
                    dest_conn.close()

                # File should now exist; log details
                size_kb = os.path.getsize(backup_file) / 1024
                self.logger.info(f"Yedek alındı: {backup_file} ({size_kb:.2f} KB)")
                # Cleanup old backups
                self._cleanup_old_backups()
                return backup_file

            except sqlite3.OperationalError as e:
                # Database locked or other operational error — retry with backoff
                msg = str(e).lower()
                if "locked" in msg or "database is locked" in msg:
                    self.logger.warning(
                        f"Yedek alma denemesi {attempt} başarısız: {e}. Geri deneyeceğim ({delay_s}s)."
                    )
                    time.sleep(delay_s)
                    delay_s *= 2
                    continue
                else:
                    self.logger.error(
                        f"Yedek alma hatası (OperationalError): {e}", exc_info=True
                    )
                    return None
            except Exception as e:
                self.logger.error(f"Yedek alma hatası: {e}", exc_info=True)
                # Cleanup any partial file
                try:
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                except Exception:
                    pass
                return None

        # If we exhausted retries
        self.logger.error(
            f"Yedek alma başarısız (tüm denemeler başarısız): {backup_file}"
        )
        return None

    def _cleanup_old_backups(self, max_backups: int = 2):
        """Eski yedekleri temizle"""
        try:
            backup_path = Path(self.backup_folder)
            if not backup_path.exists():
                return

            # Tüm .db yedeklerini listele ve tarihe göre sırala
            backups = sorted(
                backup_path.glob("yedek_*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,  # En yeni en başta
            )

            # Fazla yedekleri sil
            for backup in backups[max_backups:]:
                try:
                    backup.unlink()
                    self.logger.info(f"Eski yedek silindi: {backup.name}")
                except Exception as e:
                    self.logger.warning(f"Yedek silinirken hata: {backup.name} - {e}")

        except Exception as e:
            self.logger.warning(f"Eski yedek temizliği hatası: {e}")

    def has_recent_backup(
        self, max_age_hours: float = 24, description_prefix: Optional[str] = None
    ) -> bool:
        """Return True if a matching backup exists within the given age window."""
        try:
            backup_path = Path(self.backup_folder)
            if not backup_path.exists():
                return False

            cutoff_ts = time.time() - (max_age_hours * 3600)
            pattern = (
                f"yedek_{description_prefix}_*.db"
                if description_prefix
                else "yedek_*.db"
            )

            for backup in backup_path.glob(pattern):
                try:
                    if backup.stat().st_mtime >= cutoff_ts:
                        return True
                except FileNotFoundError:
                    continue
        except Exception as e:
            self.logger.warning(f"Güncel yedek kontrolü yapılamadı: {e}")
        return False

    def restore_backup(self, backup_file: str, connection_pool: dict = None) -> bool:
        """Yedekten geri yükle"""
        try:
            if not os.path.exists(backup_file):
                self.logger.error(f"Yedek dosyası bulunamadı: {backup_file}")
                return False

            # Mevcut veritabanının son yedeğini al (güvenlik)
            safety_backup = f"{self.db_path}.pre_restore.bak"
            shutil.copy2(self.db_path, safety_backup)

            # Yedekten geri yükle - Bu işlem için dışarıdaki bağlantıların kapalı olması gerekir
            # Ancak burada sadece dosya kopyalıyoruz, bağlantı yönetimi çağıran tarafta olmalı
            shutil.copy2(backup_file, self.db_path)

            self.logger.info(f"Veritabanı başarıyla geri yüklendi: {backup_file}")
            return True

        except Exception as e:
            self.logger.error(f"Geri yükleme hatası: {e}", exc_info=True)
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """Mevcut yedekleri listele"""
        try:
            backups = []
            backup_path = Path(self.backup_folder)

            if not backup_path.exists():
                return backups

            for backup in sorted(
                backup_path.glob("yedek_*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            ):
                stat = backup.stat()
                backups.append(
                    {
                        "dosya": str(backup),
                        "ad": backup.name,
                        "boyut_kb": stat.st_size / 1024,
                        "tarih": datetime.datetime.fromtimestamp(stat.st_mtime),
                        "tarih_str": datetime.datetime.fromtimestamp(
                            stat.st_mtime
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

            return backups

        except Exception as e:
            self.logger.error(f"Yedek listeleme hatası: {e}")
            return []
