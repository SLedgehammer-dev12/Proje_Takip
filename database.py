import sqlite3
import logging
import datetime
import os
from typing import Optional, Dict, List, Tuple, Any

# Authentication imports
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "bcrypt not available - user authentication will not work. Install with: pip install bcrypt"
    )

from models import Durum, DatabaseError, ProjeModel, RevizyonModel
from services.backup_service import BackupService
from project_types import normalize_project_type
from utils import get_class_logger
# CLEANUP: migration_service removed - migrations completed


class ProjeTakipDB:
    def __init__(self, db_adi="projeler.db"):
        self.db_adi = db_adi
        self.logger = get_class_logger(self)
        self._is_closed = False

        # Connection pool for concurrent access
        self.conn = self._open_connection()
        self.cursor = self.conn.cursor()
        self._connection_pool = {}

        # Initialize Services
        self.backup_service = BackupService(self.db_adi)
        # CLEANUP: migration_service removed - migrations completed

        # Değişiklik takibi
        self._degisiklik_sayisi = 0
        
        # PERFORMANCE: Query result cache
        self._query_cache: Dict[str, Any] = {}
        self._query_cache_max_size = 50  # Store up to 50 cached queries
        self._cache_enabled = True

        # Setup database
        self.tablolari_olustur()
        self._ensure_yazi_dokumanlari_schema()
        self._indeksleri_olustur()

        # CLEANUP: migration run removed - migrations completed
        # Note: If you need to migrate an old database, restore migration_service.py
        # from Archive/migration/ and uncomment the following lines:
        # from services.migration_service import MigrationService
        # self.migration_service = MigrationService(self.conn)
        # self.migration_service.run_migrations()

        # Create initial users if needed
        try:
            if BCRYPT_AVAILABLE:
                self.create_initial_users()
        except Exception as e:
            self.logger.warning(f"Failed to create initial users: {e}")

    def _get_connection(self):
        """Get the main database connection"""
        return self.conn

    def _open_connection(self, db_path: Optional[str] = None) -> sqlite3.Connection:
        conn = sqlite3.connect(db_path or self.db_adi, isolation_level="DEFERRED")
        self._configure_connection(conn)
        return conn

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        pragma_statements = (
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA foreign_keys = ON",
            "PRAGMA busy_timeout = 10000",
            "PRAGMA wal_autocheckpoint = 1000",
            "PRAGMA journal_size_limit = 67108864",
            "PRAGMA cache_size = -64000",
            "PRAGMA mmap_size = 64000000",
            "PRAGMA temp_store = MEMORY",
            "PRAGMA page_size = 4096",
        )
        for statement in pragma_statements:
            try:
                conn.execute(statement)
            except sqlite3.DatabaseError as e:
                self.logger.warning("PRAGMA uygulanamadı (%s): %s", statement, e)

    def create_independent_connection(
        self, db_path: Optional[str] = None
    ) -> sqlite3.Connection:
        """Thread-safe kullanım için aynı ayarlarla yeni bağlantı aç."""
        return self._open_connection(db_path)

    def transaction(self, track_change: bool = True):
        """Context manager for transactions"""
        from contextlib import contextmanager

        @contextmanager
        def _transaction():
            conn = self._get_connection()
            try:
                yield
                conn.commit()
                if track_change:
                    self.degisiklik_kaydet()
                    # Ensure read paths don't serve stale data right after writes.
                    self._clear_query_cache()
            except Exception as e:
                conn.rollback()
                self.logger.critical(f"Transaction failed: {e}", exc_info=True)
                raise

        return _transaction()

    def cleanup_connections(self):
        """Close all pooled connections"""
        for conn in self._connection_pool.values():
            try:
                conn.close()
            except Exception:
                pass
        self._connection_pool.clear()
        self.logger.info("Database connection pool temizlendi")

    # =============================================================================
    # DELEGATED METHODS (BACKUP)
    # =============================================================================

    def otomatik_yedek_al(self, aciklama: str = "Otomatik") -> Optional[str]:
        return self.backup_service.create_backup(self.conn, aciklama)

    def yedekten_geri_yukle(self, yedek_dosya: str) -> bool:
        # Close connections before restore
        self._close_main_connection()
        self.cleanup_connections()

        success = self.backup_service.restore_backup(yedek_dosya)

        # Re-open connection
        self.conn = self._open_connection()
        self.cursor = self.conn.cursor()
        self._is_closed = False
        self.tablolari_olustur()
        self._ensure_yazi_dokumanlari_schema()
        self._indeksleri_olustur()
        return success

    def yedekleri_listele(self) -> List[Dict[str, Any]]:
        return self.backup_service.list_backups()

    # =============================================================================
    # CORE DATABASE METHODS
    # =============================================================================

    def tablolari_olustur(self):
        with self.transaction(track_change=False):
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS kategoriler (
                    id INTEGER PRIMARY KEY,
                    isim TEXT NOT NULL,
                    parent_id INTEGER,
                    UNIQUE(isim, parent_id),
                    FOREIGN KEY (parent_id) REFERENCES kategoriler (id) ON DELETE CASCADE
                )"""
            )
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS projeler (
                    id INTEGER PRIMARY KEY, proje_kodu TEXT NOT NULL UNIQUE,
                    proje_ismi TEXT NOT NULL, proje_turu TEXT, 
                    olusturma_tarihi TIMESTAMP, 
                    hiyerarsi TEXT,
                    kategori_id INTEGER,
                    FOREIGN KEY (kategori_id) REFERENCES kategoriler (id) ON DELETE SET NULL
                )"""
            )
            self.cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS revizyonlar (
                    id INTEGER PRIMARY KEY, proje_id INTEGER NOT NULL, revizyon_kodu TEXT NOT NULL,
                    aciklama TEXT, durum TEXT DEFAULT '{Durum.ONAYSIZ.value}', tarih TIMESTAMP,
                    gelen_yazi_no TEXT, gelen_yazi_tarih TEXT, onay_yazi_no TEXT, onay_yazi_tarih TEXT,
                    red_yazi_no TEXT, red_yazi_tarih TEXT, proje_rev_no INTEGER,
                    tse_gonderildi INTEGER DEFAULT 0, tse_yazi_no TEXT, tse_yazi_tarih TEXT,
                    yazi_turu TEXT DEFAULT 'gelen',
                    FOREIGN KEY (proje_id) REFERENCES projeler (id) ON DELETE CASCADE
                )"""
            )
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS dokumanlar (
                    id INTEGER PRIMARY KEY, revizyon_id INTEGER NOT NULL UNIQUE,
                    dosya_adi TEXT NOT NULL, dosya_verisi BLOB NOT NULL,
                    FOREIGN KEY (revizyon_id) REFERENCES revizyonlar (id) ON DELETE CASCADE
                )"""
            )
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS yazi_dokumanlari (
                    id INTEGER PRIMARY KEY, yazi_no TEXT NOT NULL,
                    yazi_tarih TEXT NOT NULL DEFAULT '',
                    dosya_adi TEXT NOT NULL,
                    dosya_verisi BLOB NOT NULL,
                    yazi_turu TEXT NOT NULL,
                    UNIQUE(yazi_no, yazi_tarih, yazi_turu)
                )"""
            )
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS revizyon_takipleri (
                    id INTEGER PRIMARY KEY,
                    revizyon_id INTEGER NOT NULL UNIQUE,
                    takip_notu TEXT,
                    aktif INTEGER DEFAULT 1,
                    olusturma_tarihi TIMESTAMP,
                    guncelleme_tarihi TIMESTAMP,
                    kapatma_tarihi TIMESTAMP,
                    FOREIGN KEY (revizyon_id) REFERENCES revizyonlar (id) ON DELETE CASCADE
                )"""
            )
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'admin',
                    created_at TIMESTAMP,
                    last_login TIMESTAMP
                )"""
            )
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP
                )"""
            )

    def _indeksleri_olustur(self):
        with self.transaction(track_change=False):
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_projeler_kod ON projeler(proje_kodu)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revizyonlar_proje_id ON revizyonlar(proje_id)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revizyonlar_durum ON revizyonlar(durum)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_yazi_dokumanlari_yazi_no ON yazi_dokumanlari(yazi_no)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_yazi_dokumanlari_lookup ON yazi_dokumanlari(yazi_no, yazi_tarih, yazi_turu)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_kategoriler_parent_id ON kategoriler(parent_id)"
            )
            try:
                self.cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_projeler_kategori_id ON projeler(kategori_id)"
                )
            except sqlite3.OperationalError:
                pass
            # Composite index: son revizyon subquery'sini hizlandirir
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revizyonlar_proje_revno ON revizyonlar(proje_id, proje_rev_no DESC, id DESC)"
            )
            # Tarih alanlari icin indexler (filtreleme ve raporlama)
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revizyonlar_gelen_tarih ON revizyonlar(gelen_yazi_tarih)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revizyonlar_onay_tarih ON revizyonlar(onay_yazi_tarih)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revizyonlar_red_tarih ON revizyonlar(red_yazi_tarih)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revizyon_takipleri_aktif ON revizyon_takipleri(aktif)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revizyon_takipleri_guncelleme ON revizyon_takipleri(guncelleme_tarihi)"
            )

    def degisiklik_kaydet(self):
        self._degisiklik_sayisi += 1

    def degisiklik_var_mi(self) -> bool:
        return self._degisiklik_sayisi > 0

    def degisiklikleri_sifirla(self):
        self._degisiklik_sayisi = 0

    def otomatik_kaydet(self) -> int:
        """Otomatik kaydetme helper: veritabanında değişiklik varsa commit ile disk'e yaz ve sayaçı sıfırla.

        Returns number of changes saved (0 if none).
        """
        if not self.degisiklik_var_mi():
            return 0
        try:
            # commit main connection
            try:
                self.conn.commit()
            except Exception:
                pass

            # commit any pooled connections
            for conn in getattr(self, "_connection_pool", {}).values():
                try:
                    conn.commit()
                except Exception:
                    pass

            saved = self._degisiklik_sayisi
            self.degisiklikleri_sifirla()
            
            # PERFORMANCE: Clear query cache after commit
            self._clear_query_cache()
            
            self.logger.info(f"Database otomatik kaydedildi: {saved} değişiklik")
            return saved
        except Exception as e:
            self.logger.error(f"Database otomatik kaydetme başarısız: {e}", exc_info=True)
            return 0
    
    def _clear_query_cache(self):
        """Clear the query result cache."""
        try:
            if hasattr(self, '_query_cache'):
                self._query_cache.clear()
        except Exception:
            pass

    def _ensure_yazi_dokumanlari_schema(self):
        """Migrate legacy yazi_dokumanlari schema to include tarih + composite uniqueness."""
        try:
            columns = {
                row[1]
                for row in self.cursor.execute("PRAGMA table_info(yazi_dokumanlari)").fetchall()
            }
            if "yazi_tarih" in columns:
                return

            with self.transaction(track_change=False):
                self.cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS yazi_dokumanlari_v2 (
                        id INTEGER PRIMARY KEY,
                        yazi_no TEXT NOT NULL,
                        yazi_tarih TEXT NOT NULL DEFAULT '',
                        dosya_adi TEXT NOT NULL,
                        dosya_verisi BLOB NOT NULL,
                        yazi_turu TEXT NOT NULL,
                        UNIQUE(yazi_no, yazi_tarih, yazi_turu)
                    )
                    """
                )
                self.cursor.execute(
                    """
                    INSERT INTO yazi_dokumanlari_v2 (id, yazi_no, yazi_tarih, dosya_adi, dosya_verisi, yazi_turu)
                    SELECT id, yazi_no, '', dosya_adi, dosya_verisi, yazi_turu
                    FROM yazi_dokumanlari
                    """
                )
                self.cursor.execute("DROP TABLE yazi_dokumanlari")
                self.cursor.execute(
                    "ALTER TABLE yazi_dokumanlari_v2 RENAME TO yazi_dokumanlari"
                )
            self.logger.info("yazi_dokumanlari schema migrated to composite key.")
        except Exception as e:
            self.logger.error(f"yazi_dokumanlari schema migration failed: {e}", exc_info=True)
            raise

    def _normalize_yazi_tarih_key(self, yazi_tarih: Optional[str]) -> str:
        if yazi_tarih is None:
            return ""
        return str(yazi_tarih).strip()

    def _expand_yazi_dokumani_turleri(self, yazi_turu: Optional[str]) -> List[str]:
        if not yazi_turu:
            return []
        if yazi_turu in {"onay", "notlu_onay"}:
            return ["onay", "notlu_onay"]
        if yazi_turu == "giden":
            return ["giden", "onay", "notlu_onay", "red"]
        return [yazi_turu]

    def _get_meta(self, key: str) -> Optional[str]:
        try:
            row = self.cursor.execute(
                "SELECT value FROM app_meta WHERE key = ?",
                (key,),
            ).fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def _set_meta(self, key: str, value: str):
        with self.transaction(track_change=False):
            self.cursor.execute(
                """
                INSERT INTO app_meta(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, datetime.datetime.now().isoformat()),
            )

    def _normalize_project_types(self):
        """Normalize legacy project type values to the canonical list."""
        try:
            meta_key = "project_type_normalization_v2_done"
            if self._get_meta(meta_key) == "1":
                return
            self.cursor.execute("SELECT id, proje_turu FROM projeler")
            rows = self.cursor.fetchall()
            updates = []
            for proje_id, proje_turu in rows:
                normalized = normalize_project_type(proje_turu)
                if normalized != proje_turu:
                    updates.append((normalized, proje_id))
            if not updates:
                self._set_meta(meta_key, "1")
                return
            with self.transaction(track_change=False):
                self.cursor.executemany(
                    "UPDATE projeler SET proje_turu = ? WHERE id = ?",
                    updates,
                )
            self._set_meta(meta_key, "1")
            self._clear_query_cache()
            self.logger.info(
                "Project type normalization applied to %s record(s).",
                len(updates),
            )
        except Exception as e:
            self.logger.warning(f"Project type normalization skipped: {e}")

    def run_quick_check(self) -> Tuple[bool, str]:
        """SQLite quick_check sonucu döndür."""
        try:
            row = self.cursor.execute("PRAGMA quick_check").fetchone()
            result = (row[0] if row else "unknown") or "unknown"
            return result.lower() == "ok", result
        except Exception as e:
            return False, str(e)

    def _run_startup_health_check(self):
        if not self._should_run_startup_health_check():
            return
        ok, detail = self.run_quick_check()
        if ok:
            self._set_meta("last_quick_check_at", datetime.datetime.now().isoformat())
            self.logger.info("Database quick_check OK")
        else:
            self.logger.error("Database quick_check failed: %s", detail)

    def _should_run_startup_health_check(self) -> bool:
        if self._is_network_database():
            self.logger.info("Database quick_check skipped for network database.")
            return False
        last_check = self._get_meta("last_quick_check_at")
        if not last_check:
            return True
        try:
            last_dt = datetime.datetime.fromisoformat(last_check)
        except ValueError:
            return True
        if (datetime.datetime.now() - last_dt) < datetime.timedelta(days=7):
            self.logger.info("Database quick_check skipped (recently completed).")
            return False
        return True

    def _is_network_database(self) -> bool:
        return self.db_adi.startswith("\\\\") or self.db_adi.startswith("//")

    def optimize_database(self):
        try:
            self.conn.execute("PRAGMA optimize")
        except Exception as e:
            self.logger.warning(f"Database optimize başarısız: {e}")

    def checkpoint_wal(self, mode: str = "PASSIVE"):
        safe_mode = (mode or "PASSIVE").upper()
        if safe_mode not in {"PASSIVE", "FULL", "RESTART", "TRUNCATE"}:
            safe_mode = "PASSIVE"
        try:
            return self.cursor.execute(f"PRAGMA wal_checkpoint({safe_mode})").fetchall()
        except Exception as e:
            self.logger.warning(f"WAL checkpoint başarısız ({safe_mode}): {e}")
            return []

    def prepare_for_shutdown(self):
        if self._is_closed:
            return
        try:
            self.otomatik_kaydet()
        except Exception:
            pass

    def _close_main_connection(self):
        if self._is_closed:
            return
        try:
            self.conn.close()
        except Exception:
            pass
        self._is_closed = True

    def close(self):
        if self._is_closed:
            return
        try:
            self.prepare_for_shutdown()
        finally:
            self.cleanup_connections()
            self._close_main_connection()

    # =============================================================================
    # CRUD OPERATIONS
    # =============================================================================

    def proje_ekle(
        self,
        kod: str,
        isim: str,
        proje_turu: Optional[str] = None,
        kategori_id: Optional[int] = None,
    ) -> Optional[int]:
        try:
            with self.transaction():
                tarih = datetime.datetime.now()
                hiyerarsi_metni = self.get_kategori_yolu(kategori_id)
                proje_turu = normalize_project_type(proje_turu)

                self.cursor.execute(
                    "INSERT INTO projeler (proje_kodu, proje_ismi, proje_turu, olusturma_tarihi, hiyerarsi, kategori_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        kod,
                        isim,
                        proje_turu,
                        tarih,
                        hiyerarsi_metni or None,
                        kategori_id,
                    ),
                )
                proje_id = self.cursor.lastrowid
                self.logger.info(f"Yeni proje eklendi: {kod} - {isim}")
                return proje_id
        except sqlite3.IntegrityError:
            self.logger.critical(f"Proje zaten mevcut: {kod}")
            return None

    def dosyadan_proje_ve_revizyon_ekle(
        self,
        kod: str,
        isim: str,
        dosya_yolu: str,
        yazi_turu: str = "gelen",
        proje_turu: Optional[str] = None,
        kategori_id: Optional[int] = None,
        gelen_yazi_no: Optional[str] = None,
        gelen_yazi_tarih: Optional[str] = None,
    ) -> Optional[Tuple]:
        try:
            with open(dosya_yolu, "rb") as f:
                dosya_verisi = f.read()
            dosya_adi = os.path.basename(dosya_yolu)
            proje_turu = normalize_project_type(proje_turu)

            tarih = datetime.datetime.now()

            # Transaction manually handled here for atomicity across multiple inserts
            with self.transaction():
                self.cursor.execute(
                    "INSERT INTO projeler (proje_kodu, proje_ismi, proje_turu, olusturma_tarihi, hiyerarsi, kategori_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (kod, isim, proje_turu, tarih, None, kategori_id),
                )
                proje_id = self.cursor.lastrowid

                self.cursor.execute(
                    "INSERT INTO revizyonlar (proje_id, proje_rev_no, revizyon_kodu, aciklama, durum, tarih, yazi_turu, gelen_yazi_no, gelen_yazi_tarih) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        proje_id,
                        0,
                        "A",
                        "İlk revizyon - dosyadan otomatik oluşturuldu",
                        Durum.ONAYSIZ.value,
                        tarih,
                        yazi_turu,
                        gelen_yazi_no,
                        gelen_yazi_tarih,
                    ),
                )
                revizyon_id = self.cursor.lastrowid

                self.cursor.execute(
                    "INSERT INTO dokumanlar (revizyon_id, dosya_adi, dosya_verisi) VALUES (?, ?, ?)",
                    (revizyon_id, dosya_adi, dosya_verisi),
                )

            self.logger.info(f"Dosyadan proje ve RevA eklendi: {kod}")
            return (proje_id, kod, isim)

        except Exception as e:
            self.logger.critical(f"Dosyadan proje ekleme hatası: {e}")
            raise

    def proje_var_mi(self, proje_kodu: str) -> Optional[int]:
        try:
            sonuc = self.cursor.execute(
                "SELECT id FROM projeler WHERE proje_kodu = ?", (proje_kodu,)
            ).fetchone()
            return sonuc[0] if sonuc else None
        except Exception:
            return None

    def _revizyon_siralama_degeri(self, rev_kodu: str) -> tuple:
        if rev_kodu.isalpha() and len(rev_kodu) == 1:
            if rev_kodu.upper() in ["A", "B"]:
                return (0, ord(rev_kodu.upper()))
            else:
                return (1, ord(rev_kodu.upper()) + 1000)
        elif rev_kodu.isdigit():
            return (1, int(rev_kodu))
        else:
            return (2, rev_kodu)

    def mevcut_revizyonlari_getir(self, proje_id: int, yazi_turu: str = None) -> list:
        try:
            if yazi_turu:
                sonuclar = self.cursor.execute(
                    "SELECT DISTINCT revizyon_kodu FROM revizyonlar WHERE proje_id = ? AND yazi_turu = ?",
                    (proje_id, yazi_turu),
                ).fetchall()
            else:
                sonuclar = self.cursor.execute(
                    "SELECT DISTINCT revizyon_kodu FROM revizyonlar WHERE proje_id = ?",
                    (proje_id,),
                ).fetchall()

            rev_kodlari = [row[0] for row in sonuclar]
            return sorted(rev_kodlari, key=self._revizyon_siralama_degeri)
        except Exception:
            return []

    def son_revizyon_kodu_getir(self, proje_id: int, yazi_turu: str) -> Optional[str]:
        revizyonlar = self.mevcut_revizyonlari_getir(proje_id, yazi_turu)
        return revizyonlar[-1] if revizyonlar else None

    def sonraki_revizyon_kodu_onerisi(self, proje_id: int, yazi_turu: str) -> str:
        # Determine the last revision for the given project and yazi_turu
        try:
            if yazi_turu:
                row = self.cursor.execute(
                    "SELECT revizyon_kodu, durum FROM revizyonlar WHERE proje_id = ? AND yazi_turu = ? ORDER BY proje_rev_no DESC, id DESC LIMIT 1",
                    (proje_id, yazi_turu),
                ).fetchone()
            else:
                row = self.cursor.execute(
                    "SELECT revizyon_kodu, durum FROM revizyonlar WHERE proje_id = ? ORDER BY proje_rev_no DESC, id DESC LIMIT 1",
                    (proje_id,),
                ).fetchone()
        except Exception:
            row = None

        if not row or not row[0]:
            return "A"

        son_kod, son_durum = row[0], row[1]

        # If last revision code is alphabetic (A/B/C..), and it has not been approved,
        # continue alphabetic sequence (A->B->C...). If the last revision is approved,
        # switch to numeric sequence starting at 0.
        if son_kod.isalpha() and len(son_kod) == 1:
            if son_durum == Durum.ONAYLI.value:
                return "0"
            # Continue alphabetic sequence
            next_ord = ord(son_kod.upper()) + 1
            if next_ord <= ord("Z"):
                return chr(next_ord)
            else:
                # If alphabet overflows, fallback to numeric sequence
                return "0"
        elif son_kod.isdigit():
            return str(int(son_kod) + 1)
        return "A"

    def son_revizyon_durumu_getir(self, proje_id: int) -> Optional[str]:
        """Get the status (durum) of the most recent revision for a project.
        
        Returns the durum string (e.g., 'Onayli', 'Onaysiz', 'Reddedildi', 'Notlu Onayli')
        of the latest revision, or None if no revisions exist.
        
        Args:
            proje_id: Project ID to get the last revision status for
            
        Returns:
            Status string of the last revision, or None if no revisions
        """
        try:
            row = self.cursor.execute(
                """SELECT durum FROM revizyonlar 
                   WHERE proje_id = ? 
                   ORDER BY proje_rev_no DESC, id DESC 
                   LIMIT 1""",
                (proje_id,),
            ).fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def mevcut_projeye_revizyon_ekle(
        self,
        proje_id: int,
        revizyon_kodu: str,
        dosya_yolu: str,
        aciklama: str = "",
        yazi_turu: str = "yok",
        durum: str = None,
        dosya_verisi: Optional[bytes] = None,
        gelen_yazi_no: Optional[str] = None,
        gelen_yazi_tarih: Optional[str] = None,
    ) -> Optional[int]:
        try:
            if dosya_verisi is None:
                with open(dosya_yolu, "rb") as f:
                    dosya_verisi = f.read()
            dosya_adi = os.path.basename(dosya_yolu) if dosya_yolu else "unknown"

            tarih = datetime.datetime.now()
            
            # Smart status inheritance logic
            if durum is None:
                # Get the previous revision's status
                onceki_durum = self.son_revizyon_durumu_getir(proje_id)
                
                if onceki_durum in [Durum.ONAYLI.value, Durum.ONAYLI_NOTLU.value]:
                    # Inherit approved/noted-approved status
                    durum = onceki_durum
                    self.logger.info(
                        f"Yeni revizyon önceki durumu devraldı: {onceki_durum}"
                    )
                else:
                    # Rejected or pending status -> reset to pending
                    durum = Durum.ONAYSIZ.value

            with self.transaction():
                row = self.cursor.execute(
                    "SELECT MAX(proje_rev_no) FROM revizyonlar WHERE proje_id = ?",
                    (proje_id,),
                ).fetchone()
                max_rev = row[0] if row else None
                yeni_rev_no = (max_rev + 1) if max_rev is not None else 0

                if not aciklama:
                    aciklama = f"Revizyon {revizyon_kodu} - dosyadan eklendi"

                self.cursor.execute(
                    "INSERT INTO revizyonlar (proje_id, proje_rev_no, revizyon_kodu, aciklama, durum, tarih, yazi_turu, gelen_yazi_no, gelen_yazi_tarih) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        proje_id,
                        yeni_rev_no,
                        revizyon_kodu,
                        aciklama,
                        durum,
                        tarih,
                        yazi_turu,
                        gelen_yazi_no,
                        gelen_yazi_tarih,
                    ),
                )
                revizyon_id = self.cursor.lastrowid

                self.cursor.execute(
                    "INSERT INTO dokumanlar (revizyon_id, dosya_adi, dosya_verisi) VALUES (?, ?, ?)",
                    (revizyon_id, dosya_adi, dosya_verisi),
                )

            self.logger.info(
                f"Yeni revizyon eklendi: Proje ID {proje_id}, Rev {revizyon_kodu}, Durum: {durum}"
            )
            return revizyon_id
        except Exception as e:
            self.logger.critical(f"Revizyon ekleme hatası: {e}")
            raise

    def projeleri_listele(self) -> List[ProjeModel]:
        # PERFORMANCE: Check cache first
        cache_key = "projeleri_listele"
        if self._cache_enabled and cache_key in self._query_cache:
            cached_data, cached_time = self._query_cache[cache_key]
            # Cache valid for 120 seconds
            import time
            if time.time() - cached_time < 120:
                self.logger.debug("projeleri_listele: returning cached result")
                return cached_data
        
        sorgu = f"""
        WITH SonRevizyon AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY proje_id ORDER BY proje_rev_no DESC, id DESC) AS rn
            FROM revizyonlar
        )
        SELECT
            p.id, p.proje_kodu, p.proje_ismi, p.proje_turu,
            r.gelen_yazi_no, r.gelen_yazi_tarih,
            CASE
                WHEN r.durum = '{Durum.ONAYLI.value}' THEN 'yesil'
                WHEN r.durum = '{Durum.ONAYLI_NOTLU.value}' THEN 'yesil'
                WHEN r.durum = '{Durum.REDDEDILDI.value}' THEN 'kirmizi'
                WHEN r.durum = '{Durum.ONAYSIZ.value}' THEN 'mavi'
                ELSE 'gri'
            END as durum_renk,
            p.hiyerarsi, r.durum, r.tse_gonderildi, r.onay_yazi_no, r.red_yazi_no, p.kategori_id
        FROM projeler p
        LEFT JOIN SonRevizyon r ON p.id = r.proje_id AND r.rn = 1
        ORDER BY p.id DESC
        """
        self.cursor.execute(sorgu)
        result = [ProjeModel(*row) for row in self.cursor.fetchall()]
        
        # PERFORMANCE: Cache the result
        if self._cache_enabled:
            import time
            # Limit cache size
            if len(self._query_cache) >= self._query_cache_max_size:
                # Remove oldest entry (simple FIFO)
                try:
                    self._query_cache.pop(next(iter(self._query_cache)))
                except Exception:
                    pass
            self._query_cache[cache_key] = (result, time.time())
        
        return result

    def revizyonlari_getir(
        self, proje_id: int, include_document_diagnostics: bool = False
    ) -> List[RevizyonModel]:
        yazi_doc_exists_case = """
               CASE
                   WHEN NULLIF(r.gelen_yazi_no, '') IS NOT NULL THEN
                       CASE WHEN EXISTS (
                           SELECT 1
                           FROM yazi_dokumanlari y
                           WHERE y.yazi_no = r.gelen_yazi_no
                             AND y.yazi_turu = 'gelen'
                             AND (y.yazi_tarih = COALESCE(r.gelen_yazi_tarih, '') OR y.yazi_tarih = '')
                       ) THEN 'Yüklü' ELSE 'Eksik' END
                   WHEN NULLIF(r.onay_yazi_no, '') IS NOT NULL THEN
                       CASE WHEN EXISTS (
                           SELECT 1
                           FROM yazi_dokumanlari y
                           WHERE y.yazi_no = r.onay_yazi_no
                             AND y.yazi_turu IN ('onay', 'notlu_onay')
                             AND (y.yazi_tarih = COALESCE(r.onay_yazi_tarih, '') OR y.yazi_tarih = '')
                       ) THEN 'Yüklü' ELSE 'Eksik' END
                   WHEN NULLIF(r.red_yazi_no, '') IS NOT NULL THEN
                       CASE WHEN EXISTS (
                           SELECT 1
                           FROM yazi_dokumanlari y
                           WHERE y.yazi_no = r.red_yazi_no
                             AND y.yazi_turu = 'red'
                             AND (y.yazi_tarih = COALESCE(r.red_yazi_tarih, '') OR y.yazi_tarih = '')
                       ) THEN 'Yüklü' ELSE 'Eksik' END
                   ELSE '-'
               END
        """
        suspicious_case = (
            """
               CASE
                   WHEN NULLIF(r.onay_yazi_no, '') IS NOT NULL THEN
                       CASE WHEN EXISTS (
                           SELECT 1
                           FROM dokumanlar d
                           JOIN yazi_dokumanlari y
                             ON y.yazi_no = r.onay_yazi_no
                            AND y.yazi_turu IN ('onay', 'notlu_onay')
                            AND (y.yazi_tarih = COALESCE(r.onay_yazi_tarih, '') OR y.yazi_tarih = '')
                           WHERE d.revizyon_id = r.id
                             AND d.dosya_verisi = y.dosya_verisi
                       ) THEN 1 ELSE 0 END
                   WHEN NULLIF(r.red_yazi_no, '') IS NOT NULL THEN
                       CASE WHEN EXISTS (
                           SELECT 1
                           FROM dokumanlar d
                           JOIN yazi_dokumanlari y
                             ON y.yazi_no = r.red_yazi_no
                            AND y.yazi_turu = 'red'
                            AND (y.yazi_tarih = COALESCE(r.red_yazi_tarih, '') OR y.yazi_tarih = '')
                           WHERE d.revizyon_id = r.id
                             AND d.dosya_verisi = y.dosya_verisi
                       ) THEN 1 ELSE 0 END
                   ELSE 0
               END
            """
            if include_document_diagnostics
            else "0"
        )
        sorgu = """
        SELECT r.id, r.proje_rev_no, r.revizyon_kodu, r.durum, r.tarih, r.aciklama,
               CASE WHEN EXISTS (SELECT 1 FROM dokumanlar d WHERE d.revizyon_id = r.id) 
                    THEN 'Var' ELSE 'Yok' END,
               r.onay_yazi_no, r.onay_yazi_tarih, r.red_yazi_no, r.red_yazi_tarih,
               r.gelen_yazi_no, r.gelen_yazi_tarih, r.tse_gonderildi, r.yazi_turu,
               (SELECT d.dosya_adi FROM dokumanlar d WHERE d.revizyon_id = r.id) as dosya_adi,
               {yazi_doc_exists_case} as yazi_dokuman_durumu,
               {suspicious_case} as supheli_yazi_dokumani,
               CASE
                   WHEN EXISTS (
                       SELECT 1
                       FROM revizyon_takipleri t
                       WHERE t.revizyon_id = r.id AND t.aktif = 1
                   ) THEN 1
                   ELSE 0
               END as takipte_mi,
               (SELECT t.takip_notu FROM revizyon_takipleri t WHERE t.revizyon_id = r.id LIMIT 1) as takip_notu
        FROM revizyonlar r
        WHERE r.proje_id = ? 
        ORDER BY r.proje_rev_no DESC, r.id DESC
        """
        self.cursor.execute(
            sorgu.format(
                suspicious_case=suspicious_case,
                yazi_doc_exists_case=yazi_doc_exists_case,
            ),
            (proje_id,),
        )
        return [RevizyonModel(*row) for row in self.cursor.fetchall()]

    def yeni_revizyon_ve_dokuman_ekle(
        self,
        proje_id: int,
        rev_kodu: str,
        aciklama: str,
        dosya_adi: str,
        dosya_verisi: bytes,
        gelen_yazi_no: Optional[str] = None,
        gelen_yazi_tarih: Optional[str] = None,
    ) -> bool:
        try:
            with self.transaction():
                self.cursor.execute(
                    "SELECT MAX(proje_rev_no) FROM revizyonlar WHERE proje_id = ?",
                    (proje_id,),
                )
                sonuc = self.cursor.fetchone()
                son_rev_no = sonuc[0] if sonuc and sonuc[0] is not None else -1
                self.cursor.execute(
                    "INSERT INTO revizyonlar (proje_id, proje_rev_no, revizyon_kodu, aciklama, durum, tarih, gelen_yazi_no, gelen_yazi_tarih) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        proje_id,
                        son_rev_no + 1,
                        rev_kodu,
                        aciklama,
                        Durum.ONAYSIZ.value,
                        datetime.datetime.now(),
                        gelen_yazi_no,
                        gelen_yazi_tarih,
                    ),
                )
                yeni_revizyon_id = self.cursor.lastrowid
                self.cursor.execute(
                    "INSERT INTO dokumanlar (revizyon_id, dosya_adi, dosya_verisi) VALUES (?, ?, ?)",
                    (yeni_revizyon_id, dosya_adi, dosya_verisi),
                )
                self.logger.info(
                    f"Yeni revizyon eklendi: Proje ID {proje_id}, Revizyon {rev_kodu}"
                )
                return True
        except sqlite3.Error as e:
            self.logger.critical(
                f"Database error in yeni_revizyon_ve_dokuman_ekle: {e}"
            )
            raise DatabaseError(f"Revizyon eklenemedi: {e}")

    def revizyon_bul_id_ile(self, revizyon_id: int) -> Optional[Tuple]:
        self.cursor.execute(
            """
            SELECT id, proje_id, revizyon_kodu, aciklama, durum, tarih, 
                   gelen_yazi_no, gelen_yazi_tarih, onay_yazi_no, onay_yazi_tarih, 
                   red_yazi_no, red_yazi_tarih, proje_rev_no,
                   tse_gonderildi, tse_yazi_no, tse_yazi_tarih
            FROM revizyonlar 
            WHERE id = ?
            """,
            (revizyon_id,),
        )
        return self.cursor.fetchone()

    def revizyonu_guncelle(
        self,
        revizyon_id: int,
        aciklama: str,
        gelen_yazi_no: Optional[str],
        gelen_yazi_tarih: Optional[str],
        onay_yazi_no: Optional[str],
        onay_yazi_tarih: Optional[str],
        red_yazi_no: Optional[str],
        red_yazi_tarih: Optional[str],
        tse_gonderildi: int,
        tse_yazi_no: Optional[str],
        tse_yazi_tarih: Optional[str],
    ) -> bool:
        try:
            # Determine yazi_turu to set (prioritize giden if onay/red provided)
            yazi_turu = None
            if onay_yazi_no or red_yazi_no:
                yazi_turu = "giden"
            elif gelen_yazi_no:
                yazi_turu = "gelen"

            with self.transaction():
                if yazi_turu:
                    self.cursor.execute(
                        """
                        UPDATE revizyonlar 
                        SET aciklama = ?, gelen_yazi_no = ?, gelen_yazi_tarih = ?,
                            onay_yazi_no = ?, onay_yazi_tarih = ?,
                            red_yazi_no = ?, red_yazi_tarih = ?,
                            tse_gonderildi = ?, tse_yazi_no = ?, tse_yazi_tarih = ?,
                            yazi_turu = ?
                        WHERE id = ?
                    """,
                        (
                            aciklama,
                            gelen_yazi_no,
                            gelen_yazi_tarih,
                            onay_yazi_no,
                            onay_yazi_tarih,
                            red_yazi_no,
                            red_yazi_tarih,
                            tse_gonderildi,
                            tse_yazi_no,
                            tse_yazi_tarih,
                            yazi_turu,
                            revizyon_id,
                        ),
                    )
                else:
                    self.cursor.execute(
                        """
                        UPDATE revizyonlar 
                        SET aciklama = ?, gelen_yazi_no = ?, gelen_yazi_tarih = ?,
                            onay_yazi_no = ?, onay_yazi_tarih = ?,
                            red_yazi_no = ?, red_yazi_tarih = ?,
                            tse_gonderildi = ?, tse_yazi_no = ?, tse_yazi_tarih = ?
                        WHERE id = ?
                    """,
                        (
                            aciklama,
                            gelen_yazi_no,
                            gelen_yazi_tarih,
                            onay_yazi_no,
                            onay_yazi_tarih,
                            red_yazi_no,
                            red_yazi_tarih,
                            tse_gonderildi,
                            tse_yazi_no,
                            tse_yazi_tarih,
                            revizyon_id,
                        ),
                    )
                return self.cursor.rowcount > 0
        except Exception as e:
            self.logger.critical(f"Revizyon güncelleme hatası: {e}")
            raise

    def dokumani_guncelle(
        self, revizyon_id: int, dosya_adi: str, dosya_verisi: bytes
    ) -> bool:
        try:
            self.logger.debug(f"Updating dokuman for revizyon_id={revizyon_id}, dosya_adi={dosya_adi}, size={len(dosya_verisi) if dosya_verisi else 0}")
            with self.transaction():
                self.cursor.execute(
                    "UPDATE dokumanlar SET dosya_adi = ?, dosya_verisi = ? WHERE revizyon_id = ?",
                    (dosya_adi, dosya_verisi, revizyon_id),
                )
                if self.cursor.rowcount == 0:
                    # Row didn't exist -> insert instead. This handles older DB entries that may not have dokuman row.
                    self.logger.debug(f"dokumani_guncelle: no existing dokuman row for revizyon_id={revizyon_id}, inserting new one")
                    self.cursor.execute(
                        "INSERT INTO dokumanlar (revizyon_id, dosya_adi, dosya_verisi) VALUES (?, ?, ?)",
                        (revizyon_id, dosya_adi, dosya_verisi),
                    )
                return True
        except Exception as e:
            self.logger.critical(f"Doküman güncelleme hatası: {e}")
            raise

    def sonraki_revizyon_kodunu_getir(self, proje_id: int) -> str:
        self.cursor.execute(
            "SELECT revizyon_kodu, durum FROM revizyonlar WHERE proje_id = ?",
            (proje_id,),
        )
        revizyonlar = self.cursor.fetchall()
        if not revizyonlar:
            return "A"

        onayli_ana_rev_var_mi = any(r[1] == Durum.ONAYLI.value for r in revizyonlar)
        if onayli_ana_rev_var_mi:
            sayisal_revler = [int(r[0]) for r in revizyonlar if r[0].isdigit()]
            return str(max(sayisal_revler) + 1) if sayisal_revler else "1"
        else:
            alfabetik_revler = [
                r[0] for r in revizyonlar if r[0].isalpha() and len(r[0]) == 1
            ]
            if not alfabetik_revler:
                return "A"
            return chr(ord(max(alfabetik_revler)) + 1)

    def _mevcut_yazi_kayitlarini_getir(
        self, no_column: str, tarih_column: str
    ) -> List[Tuple[str, str]]:
        self.cursor.execute(
            f"""
            SELECT DISTINCT {no_column}, COALESCE({tarih_column}, '')
            FROM revizyonlar
            WHERE {no_column} IS NOT NULL AND TRIM({no_column}) != ''
            ORDER BY {no_column} ASC, COALESCE({tarih_column}, '') DESC
            """
        )
        return [(row[0], row[1]) for row in self.cursor.fetchall()]

    def mevcut_gelen_yazilari_getir(self) -> List[Tuple[str, str]]:
        return self._mevcut_yazi_kayitlarini_getir(
            "gelen_yazi_no", "gelen_yazi_tarih"
        )

    def mevcut_onay_yazilarini_getir(self) -> List[Tuple[str, str]]:
        return self._mevcut_yazi_kayitlarini_getir(
            "onay_yazi_no", "onay_yazi_tarih"
        )

    def mevcut_red_yazilarini_getir(self) -> List[Tuple[str, str]]:
        return self._mevcut_yazi_kayitlarini_getir(
            "red_yazi_no", "red_yazi_tarih"
        )

    def revizyonu_onayla_ve_guncelle(
        self, revizyon_id: int, onay_yazi_no: str, onay_yazi_tarih: str
    ) -> str:
        with self.transaction():
            self.cursor.execute(
                "SELECT proje_id, revizyon_kodu FROM revizyonlar WHERE id = ?",
                (revizyon_id,),
            )
            sonuc = self.cursor.fetchone()
            if not sonuc:
                return "Hata: Revizyon bulunamadı."

            proje_id, mevcut_rev_kodu = sonuc
            if mevcut_rev_kodu.isalpha():
                self.cursor.execute(
                    "SELECT COUNT(*) FROM revizyonlar WHERE proje_id = ? AND revizyon_kodu = '0'",
                    (proje_id,),
                )
                count_row = self.cursor.fetchone()
                if count_row and count_row[0] > 0:
                    return "Hata: Bu projede zaten onaylanmış bir ana revizyon (Rev-0) bulunmaktadır."

                self.cursor.execute(
                    "UPDATE revizyonlar SET durum = ?, revizyon_kodu = ?, onay_yazi_no = ?, onay_yazi_tarih = ?, yazi_turu = 'giden' WHERE id = ?",
                    (
                        Durum.ONAYLI.value,
                        "0",
                        onay_yazi_no,
                        onay_yazi_tarih,
                        revizyon_id,
                    ),
                )
            elif mevcut_rev_kodu.isdigit():
                self.cursor.execute(
                    "UPDATE revizyonlar SET durum = ?, onay_yazi_no = ?, onay_yazi_tarih = ?, yazi_turu = 'giden' WHERE id = ?",
                    (Durum.ONAYLI.value, onay_yazi_no, onay_yazi_tarih, revizyon_id),
                )
            else:
                return f"Hata: Geçersiz revizyon kodu formatı ('{mevcut_rev_kodu}')."
            return "Basarili" if self.cursor.rowcount > 0 else "Hata"

    def revizyonu_notlu_onayla_ve_guncelle(
        self, revizyon_id: int, onay_yazi_no: str, onay_yazi_tarih: str
    ) -> str:
        with self.transaction():
            self.cursor.execute(
                "UPDATE revizyonlar SET durum = ?, onay_yazi_no = ?, onay_yazi_tarih = ?, yazi_turu = 'giden' WHERE id = ?",
                (Durum.ONAYLI_NOTLU.value, onay_yazi_no, onay_yazi_tarih, revizyon_id),
            )
            return "Basarili" if self.cursor.rowcount > 0 else "Hata"

    def revizyonu_reddet_ve_guncelle(
        self, revizyon_id: int, red_yazi_no: str, red_yazi_tarih: str
    ) -> str:
        with self.transaction():
            self.cursor.execute(
                "UPDATE revizyonlar SET durum = ?, red_yazi_no = ?, red_yazi_tarih = ?, yazi_turu = 'giden' WHERE id = ?",
                (Durum.REDDEDILDI.value, red_yazi_no, red_yazi_tarih, revizyon_id),
            )
            return "Basarili" if self.cursor.rowcount > 0 else "Hata"

    def en_son_revizyon_bilgisi_getir(self, proje_id: int) -> Optional[RevizyonModel]:
        try:
            sorgu = """
            SELECT r.id, r.proje_rev_no, r.revizyon_kodu, r.durum, r.tarih, r.aciklama,
                   CASE WHEN EXISTS (SELECT 1 FROM dokumanlar d WHERE d.revizyon_id = r.id)
                        THEN 'Var' ELSE 'Yok' END,
                   r.onay_yazi_no, r.onay_yazi_tarih, r.red_yazi_no, r.red_yazi_tarih,
                   r.gelen_yazi_no, r.gelen_yazi_tarih, r.tse_gonderildi, r.yazi_turu,
                   (SELECT d.dosya_adi FROM dokumanlar d WHERE d.revizyon_id = r.id) as dosya_adi,
                   CASE
                       WHEN NULLIF(r.gelen_yazi_no, '') IS NOT NULL THEN
                           CASE WHEN EXISTS (
                               SELECT 1
                               FROM yazi_dokumanlari y
                               WHERE y.yazi_no = r.gelen_yazi_no
                                 AND y.yazi_turu = 'gelen'
                                 AND (y.yazi_tarih = COALESCE(r.gelen_yazi_tarih, '') OR y.yazi_tarih = '')
                           ) THEN 'Yüklü' ELSE 'Eksik' END
                       WHEN NULLIF(r.onay_yazi_no, '') IS NOT NULL THEN
                           CASE WHEN EXISTS (
                               SELECT 1
                               FROM yazi_dokumanlari y
                               WHERE y.yazi_no = r.onay_yazi_no
                                 AND y.yazi_turu IN ('onay', 'notlu_onay')
                                 AND (y.yazi_tarih = COALESCE(r.onay_yazi_tarih, '') OR y.yazi_tarih = '')
                           ) THEN 'Yüklü' ELSE 'Eksik' END
                       WHEN NULLIF(r.red_yazi_no, '') IS NOT NULL THEN
                           CASE WHEN EXISTS (
                               SELECT 1
                               FROM yazi_dokumanlari y
                               WHERE y.yazi_no = r.red_yazi_no
                                 AND y.yazi_turu = 'red'
                                 AND (y.yazi_tarih = COALESCE(r.red_yazi_tarih, '') OR y.yazi_tarih = '')
                           ) THEN 'Yüklü' ELSE 'Eksik' END
                       ELSE '-'
                   END as yazi_dokuman_durumu,
                   CASE
                       WHEN NULLIF(r.onay_yazi_no, '') IS NOT NULL
                            AND EXISTS (
                                SELECT 1
                                FROM dokumanlar d
                                JOIN yazi_dokumanlari y
                                  ON y.yazi_no = r.onay_yazi_no
                                 AND y.yazi_turu IN ('onay', 'notlu_onay')
                                 AND (y.yazi_tarih = COALESCE(r.onay_yazi_tarih, '') OR y.yazi_tarih = '')
                                WHERE d.revizyon_id = r.id
                                  AND d.dosya_verisi = y.dosya_verisi
                            )
                       THEN 1
                       WHEN NULLIF(r.red_yazi_no, '') IS NOT NULL
                            AND EXISTS (
                                SELECT 1
                                FROM dokumanlar d
                                JOIN yazi_dokumanlari y
                                  ON y.yazi_no = r.red_yazi_no
                                 AND y.yazi_turu = 'red'
                                 AND (y.yazi_tarih = COALESCE(r.red_yazi_tarih, '') OR y.yazi_tarih = '')
                                WHERE d.revizyon_id = r.id
                                  AND d.dosya_verisi = y.dosya_verisi
                            )
                       THEN 1
                       ELSE 0
                   END as supheli_yazi_dokumani,
                   CASE
                       WHEN EXISTS (
                           SELECT 1
                           FROM revizyon_takipleri t
                           WHERE t.revizyon_id = r.id AND t.aktif = 1
                       ) THEN 1
                       ELSE 0
                   END as takipte_mi,
                   (SELECT t.takip_notu FROM revizyon_takipleri t WHERE t.revizyon_id = r.id LIMIT 1) as takip_notu
            FROM revizyonlar r
            WHERE r.proje_id = ?
            ORDER BY r.proje_rev_no DESC
            LIMIT 1
            """
            self.cursor.execute(sorgu, (proje_id,))
            row = self.cursor.fetchone()
            return RevizyonModel(*row) if row else None
        except sqlite3.Error:
            return None

    def revizyon_durum_ve_kod_guncelle(
        self, revizyon_id: int, yeni_durum: str, yeni_kod: str
    ) -> bool:
        """Update the status (durum) and revision code (revizyon_kodu) of a revision.

        This function intentionally preserves any existing yazı (onay/red/gelen) fields
        instead of clearing them. Older behaviour cleared 'onay_yazi_no', 'red_yazi_no',
        and their tarih fields when changing the status/kod; this change keeps them
        intact and only updates the durum/kod.
        """
        try:
            with self.transaction():
                # Only update durum and revizyon_kodu; keep any yazı numbers intact
                self.cursor.execute(
                    """
                    UPDATE revizyonlar 
                    SET durum = ?, revizyon_kodu = ?
                    WHERE id = ?
                    """,
                    (yeni_durum, yeni_kod, revizyon_id),
                )
                return self.cursor.rowcount > 0
        except Exception:
            return False

    def son_revizyon_id_getir(self, proje_id: int) -> Optional[int]:
        self.cursor.execute(
            "SELECT id FROM revizyonlar WHERE proje_id = ? ORDER BY proje_rev_no DESC LIMIT 1",
            (proje_id,),
        )
        sonuc = self.cursor.fetchone()
        return sonuc[0] if sonuc else None

    def son_revizyona_gelen_yazi_ekle(
        self, proje_id: int, yazi_no: str, yazi_tarih: str
    ) -> bool:
        rev_id = self.son_revizyon_id_getir(proje_id)
        if not rev_id:
            return False
        try:
            with self.transaction():
                self.cursor.execute(
                    "UPDATE revizyonlar SET gelen_yazi_no = ?, gelen_yazi_tarih = ?, yazi_turu = 'gelen' WHERE id = ?",
                    (yazi_no, yazi_tarih, rev_id),
                )
                return self.cursor.rowcount > 0
        except Exception:
            return False

    def son_revizyonu_onayla(self, proje_id: int, yazi_no: str, yazi_tarih: str) -> str:
        rev_id = self.son_revizyon_id_getir(proje_id)
        if not rev_id:
            return f"Hata: Proje ID {proje_id} için güncellenecek revizyon bulunamadı."
        return self.revizyonu_onayla_ve_guncelle(rev_id, yazi_no, yazi_tarih)

    def son_revizyonu_notlu_onayla(
        self, proje_id: int, yazi_no: str, yazi_tarih: str
    ) -> str:
        rev_id = self.son_revizyon_id_getir(proje_id)
        if not rev_id:
            return f"Hata: Proje ID {proje_id} için güncellenecek revizyon bulunamadı."
        return self.revizyonu_notlu_onayla_ve_guncelle(rev_id, yazi_no, yazi_tarih)

    def son_revizyonu_reddet(self, proje_id: int, yazi_no: str, yazi_tarih: str) -> str:
        rev_id = self.son_revizyon_id_getir(proje_id)
        if not rev_id:
            return f"Hata: Proje ID {proje_id} için güncellenecek revizyon bulunamadı."
        return self.revizyonu_reddet_ve_guncelle(rev_id, yazi_no, yazi_tarih)

    def yazi_dokumani_kaydet(
        self,
        yazi_no: str,
        dosya_adi: str,
        dosya_verisi: bytes,
        yazi_turu: str,
        yazi_tarih: Optional[str] = None,
    ) -> bool:
        try:
            yazi_tarih_key = self._normalize_yazi_tarih_key(yazi_tarih)
            self.logger.debug(
                "Saving yazi dokumani: yazi_no=%s, yazi_tarih=%s, dosya_adi=%s, size=%s, type=%s",
                yazi_no,
                yazi_tarih_key,
                dosya_adi,
                len(dosya_verisi) if dosya_verisi else 0,
                yazi_turu,
            )
            with self.transaction():
                self.cursor.execute(
                    """
                    INSERT INTO yazi_dokumanlari (yazi_no, yazi_tarih, dosya_adi, dosya_verisi, yazi_turu)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(yazi_no, yazi_tarih, yazi_turu) DO UPDATE SET
                        dosya_adi = excluded.dosya_adi,
                        dosya_verisi = excluded.dosya_verisi
                    """,
                    (yazi_no, yazi_tarih_key, dosya_adi, dosya_verisi, yazi_turu),
                )
                return True
        except Exception:
            raise

    def yazi_dokumani_getir(
        self,
        yazi_no: str,
        yazi_tarih: Optional[str] = None,
        yazi_turu: Optional[str] = None,
    ) -> Optional[Tuple]:
        yazi_tarih_key = self._normalize_yazi_tarih_key(yazi_tarih)
        turler = self._expand_yazi_dokumani_turleri(yazi_turu)

        params: List[Any] = [yazi_no]
        where_parts = ["yazi_no = ?"]
        if turler:
            placeholders = ",".join("?" * len(turler))
            where_parts.append(f"yazi_turu IN ({placeholders})")
            params.extend(turler)

        order_by = "CASE WHEN yazi_tarih != '' THEN 1 ELSE 0 END DESC, id DESC"
        if yazi_tarih is not None:
            params.extend([yazi_tarih_key, yazi_tarih_key])
            order_by = (
                "CASE "
                "WHEN yazi_tarih = ? THEN 2 "
                "WHEN yazi_tarih = '' THEN 1 "
                "ELSE 0 END DESC, "
                "CASE WHEN yazi_tarih = ? THEN 1 ELSE 0 END DESC, id DESC"
            )

        sorgu = (
            f"SELECT dosya_adi, dosya_verisi FROM yazi_dokumanlari "
            f"WHERE {' AND '.join(where_parts)} "
            f"ORDER BY {order_by} LIMIT 1"
        )
        self.cursor.execute(sorgu, params)
        return self.cursor.fetchone()

    def revizyon_takip_bilgisi_getir(self, revizyon_id: int) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            """
            SELECT revizyon_id, takip_notu, aktif, olusturma_tarihi, guncelleme_tarihi, kapatma_tarihi
            FROM revizyon_takipleri
            WHERE revizyon_id = ?
            """,
            (revizyon_id,),
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        return {
            "revizyon_id": row[0],
            "takip_notu": row[1],
            "aktif": row[2],
            "olusturma_tarihi": row[3],
            "guncelleme_tarihi": row[4],
            "kapatma_tarihi": row[5],
        }

    def revizyonu_takibe_al(self, revizyon_id: int, takip_notu: str) -> bool:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction():
            mevcut = self.cursor.execute(
                "SELECT id FROM revizyon_takipleri WHERE revizyon_id = ?",
                (revizyon_id,),
            ).fetchone()
            if mevcut:
                self.cursor.execute(
                    """
                    UPDATE revizyon_takipleri
                    SET takip_notu = ?, aktif = 1, guncelleme_tarihi = ?, kapatma_tarihi = NULL
                    WHERE revizyon_id = ?
                    """,
                    (takip_notu, now, revizyon_id),
                )
            else:
                self.cursor.execute(
                    """
                    INSERT INTO revizyon_takipleri
                    (revizyon_id, takip_notu, aktif, olusturma_tarihi, guncelleme_tarihi)
                    VALUES (?, ?, 1, ?, ?)
                    """,
                    (revizyon_id, takip_notu, now, now),
                )
            return True

    def revizyonu_takipten_cikar(self, revizyon_id: int) -> bool:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction():
            self.cursor.execute(
                """
                UPDATE revizyon_takipleri
                SET aktif = 0, guncelleme_tarihi = ?, kapatma_tarihi = ?
                WHERE revizyon_id = ?
                """,
                (now, now, revizyon_id),
            )
            return self.cursor.rowcount > 0

    def takip_listesi_excel_verisi_getir(self, sadece_aktif: bool = True) -> List[Tuple]:
        """Revizyon takip işaretlerinin Excel export verisini döndür."""
        where_clause = "WHERE t.aktif = 1" if sadece_aktif else ""
        sorgu = """
        SELECT
            p.proje_kodu,
            p.proje_ismi,
            p.proje_turu,
            r.revizyon_kodu,
            r.durum,
            COALESCE(NULLIF(r.onay_yazi_no, ''), NULLIF(r.red_yazi_no, ''), NULLIF(r.gelen_yazi_no, '')) as yazi_no,
            COALESCE(NULLIF(r.onay_yazi_tarih, ''), NULLIF(r.red_yazi_tarih, ''), NULLIF(r.gelen_yazi_tarih, '')) as yazi_tarihi,
            t.takip_notu,
            CASE WHEN t.aktif = 1 THEN 'Takipte' ELSE 'Takipten Çıkarıldı' END as takip_durumu,
            t.olusturma_tarihi,
            t.guncelleme_tarihi,
            t.kapatma_tarihi
        FROM revizyon_takipleri t
        JOIN revizyonlar r ON r.id = t.revizyon_id
        JOIN projeler p ON p.id = r.proje_id
        {where_clause}
        ORDER BY t.aktif DESC, COALESCE(t.guncelleme_tarihi, t.olusturma_tarihi) DESC, p.proje_kodu
        """
        self.cursor.execute(sorgu.format(where_clause=where_clause))
        return self.cursor.fetchall()

    def revizyonu_sil(self, revizyon_id: int) -> bool:
        """Delete a revision and its document from the database.

        Returns True if deletion happened, False otherwise.
        """
        try:
            with self.transaction():
                # remove dokuman first (if exists)
                self.cursor.execute(
                    "DELETE FROM dokumanlar WHERE revizyon_id = ?", (revizyon_id,)
                )
                # then remove the revision row
                self.cursor.execute("DELETE FROM revizyonlar WHERE id = ?", (revizyon_id,))
                return self.cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Revizyon silme hatası: {e}", exc_info=True)
            return False

    def proje_bul_id_ile(self, proje_id: int) -> Optional[Tuple]:
        self.cursor.execute(
            "SELECT id, proje_kodu, proje_ismi, proje_turu, olusturma_tarihi, hiyerarsi, kategori_id FROM projeler WHERE id = ?",
            (proje_id,),
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        row = list(row)
        row[3] = normalize_project_type(row[3])
        return tuple(row)

    def projeyi_guncelle(
        self,
        proje_id: int,
        yeni_kod: str,
        yeni_isim: str,
        yeni_tur: Optional[str],
        yeni_kategori_id: Optional[int],
    ) -> bool:
        try:
            with self.transaction():
                self.invalidate_kategori_cache()
                yeni_hiyerarsi_metni = self.get_kategori_yolu(yeni_kategori_id)
                yeni_tur = normalize_project_type(yeni_tur)
                self.cursor.execute(
                    "UPDATE projeler SET proje_kodu = ?, proje_ismi = ?, proje_turu = ?, hiyerarsi = ?, kategori_id = ? WHERE id = ?",
                    (
                        yeni_kod,
                        yeni_isim,
                        yeni_tur,
                        yeni_hiyerarsi_metni or None,
                        yeni_kategori_id,
                        proje_id,
                    ),
                )
                return True
        except sqlite3.IntegrityError:
            return False

    def projeyi_kategoriye_tasi(
        self, proje_id: int, yeni_kategori_id: Optional[int]
    ) -> bool:
        try:
            with self.transaction():
                self.invalidate_kategori_cache()
                yeni_hiyerarsi_metni = self.get_kategori_yolu(yeni_kategori_id)
                self.cursor.execute(
                    "UPDATE projeler SET kategori_id = ?, hiyerarsi = ? WHERE id = ?",
                    (yeni_kategori_id, yeni_hiyerarsi_metni or None, proje_id),
                )
                return True
        except Exception:
            return False

    def projeyi_sil(self, proje_id: int) -> bool:
        with self.transaction():
            self.cursor.execute("DELETE FROM projeler WHERE id = ?", (proje_id,))
            return self.cursor.rowcount > 0

    def dokumani_getir(self, revizyon_id: int) -> Optional[Tuple]:
        self.cursor.execute(
            "SELECT dosya_adi, dosya_verisi FROM dokumanlar WHERE revizyon_id = ?",
            (revizyon_id,),
        )
        return self.cursor.fetchone()

    def get_kategoriler(self) -> List[Tuple[int, str, Optional[int]]]:
        try:
            self.cursor.execute(
                "SELECT id, isim, parent_id FROM kategoriler ORDER BY isim"
            )
            return self.cursor.fetchall()
        except Exception:
            return []

    def kategoriyi_sil(self, kategori_id: int) -> bool:
        """Delete a category and reassign projects to its parent (or NULL) before deletion.

        Steps:
        - Find parent_id of the category to be deleted
        - Collect all descendant categories (including given)
        - Update projects with kategori_id in descendant list to be parent_id (or NULL)
        - Delete the categories (the DB has ON DELETE CASCADE for children; remove explicitly here)
        """
        try:
            with self.transaction():
                self.invalidate_kategori_cache()
                # Get parent for this category
                self.cursor.execute(
                    "SELECT parent_id FROM kategoriler WHERE id = ?",
                    (kategori_id,),
                )
                result = self.cursor.fetchone()
                parent_id = result[0] if result else None

                # Build list of descendant category ids via CTE
                self.cursor.execute(
                    "WITH RECURSIVE descendants(id) AS (SELECT id FROM kategoriler WHERE id = ? UNION ALL SELECT k.id FROM kategoriler k JOIN descendants d ON k.parent_id = d.id) SELECT id FROM descendants",
                    (kategori_id,),
                )
                rows = self.cursor.fetchall()
                cat_ids = [r[0] for r in rows] if rows else []

                if cat_ids:
                    placeholders = ",".join("?" * len(cat_ids))
                    # Update projects assigned to any of these categories to the parent (or NULL)
                    if parent_id:
                        yeni_hiyerarsi = self.get_kategori_yolu(parent_id)
                        self.cursor.execute(
                            f"UPDATE projeler SET kategori_id = ?, hiyerarsi = ? WHERE kategori_id IN ({placeholders})",
                            (parent_id, yeni_hiyerarsi, *cat_ids),
                        )
                    else:
                        # No parent: set kategori_id NULL and hiyerarsi NULL
                        self.cursor.execute(
                            f"UPDATE projeler SET kategori_id = NULL, hiyerarsi = NULL WHERE kategori_id IN ({placeholders})",
                            (*cat_ids,),
                        )

                    # Delete the categories by id (cascade will handle child categories if any)
                    self.cursor.execute(
                        f"DELETE FROM kategoriler WHERE id IN ({placeholders})",
                        (*cat_ids,),
                    )
                return True
        except Exception as e:
            self.logger.error(f"Kategori silme hatası: {e}", exc_info=True)
            return False

    def add_kategori(self, isim: str, parent_id: Optional[int] = None) -> Optional[int]:
        if not isim or not isim.strip():
            return None
        try:
            with self.transaction():
                self.invalidate_kategori_cache()
                self.cursor.execute(
                    "INSERT INTO kategoriler (isim, parent_id) VALUES (?, ?)",
                    (isim.strip(), parent_id),
                )
                return self.cursor.lastrowid
        except Exception:
            return None

    def get_tum_kategori_yollari(self) -> Dict[int, str]:
        """Tum kategori yollarini tek sorguda recursive CTE ile getir."""
        try:
            sorgu = """
            WITH RECURSIVE kategori_yol AS (
                SELECT id, isim, parent_id, isim AS yol
                FROM kategoriler
                WHERE parent_id IS NULL
                UNION ALL
                SELECT k.id, k.isim, k.parent_id, ky.yol || '/' || k.isim
                FROM kategoriler k
                INNER JOIN kategori_yol ky ON k.parent_id = ky.id
            )
            SELECT id, yol FROM kategori_yol
            """
            self.cursor.execute(sorgu)
            return {row[0]: row[1] for row in self.cursor.fetchall()}
        except Exception:
            return {}

    def get_kategori_yolu(self, kategori_id: Optional[int]) -> str:
        if kategori_id is None:
            return ""
        try:
            # Toplu cache'den oku, yoksa olustur
            if not hasattr(self, '_kategori_yolu_toplu_cache') or not self._kategori_yolu_toplu_cache:
                self._kategori_yolu_toplu_cache = self.get_tum_kategori_yollari()
            yol = self._kategori_yolu_toplu_cache.get(kategori_id)
            if yol is not None:
                return yol
            # Cache'de yoksa tekil sorgu ile dene (yeni eklenmis kategori olabilir)
            yol_parcalari = []
            current_id = kategori_id
            while current_id is not None:
                self.cursor.execute(
                    "SELECT isim, parent_id FROM kategoriler WHERE id = ?",
                    (current_id,),
                )
                sonuc = self.cursor.fetchone()
                if not sonuc:
                    break
                yol_parcalari.insert(0, sonuc[0])
                current_id = sonuc[1]
            result = "/".join(yol_parcalari)
            # Cache'e ekle
            self._kategori_yolu_toplu_cache[kategori_id] = result
            return result
        except Exception:
            return "[Hata]"

    def invalidate_kategori_cache(self):
        """Kategori cache'ini temizle (kategori ekle/sil/guncelle sonrasi cagrilmali)."""
        if hasattr(self, '_kategori_yolu_toplu_cache'):
            self._kategori_yolu_toplu_cache = {}

    def get_distinct_yazi_yillari(self) -> List[str]:
        """Revizyonlardaki tum yazi tarihlerinden benzersiz yillari cek (DD.MM.YYYY formatindan)."""
        try:
            sorgu = """
            SELECT DISTINCT yil FROM (
                SELECT substr(gelen_yazi_tarih, 7, 4) AS yil FROM revizyonlar
                    WHERE gelen_yazi_tarih IS NOT NULL AND length(gelen_yazi_tarih) >= 10
                UNION
                SELECT substr(onay_yazi_tarih, 7, 4) AS yil FROM revizyonlar
                    WHERE onay_yazi_tarih IS NOT NULL AND length(onay_yazi_tarih) >= 10
                UNION
                SELECT substr(red_yazi_tarih, 7, 4) AS yil FROM revizyonlar
                    WHERE red_yazi_tarih IS NOT NULL AND length(red_yazi_tarih) >= 10
            )
            WHERE yil IS NOT NULL AND yil != ''
            ORDER BY yil DESC
            """
            self.cursor.execute(sorgu)
            return [row[0] for row in self.cursor.fetchall()]
        except Exception:
            return []

    def get_approval_trend_data(self) -> List[Tuple]:
        """Aylık onay istatistiklerini döndür (son 12 ay)."""
        sorgu = f"""
        WITH normalized AS (
            SELECT
                CASE
                    WHEN onay_yazi_tarih IS NOT NULL AND TRIM(onay_yazi_tarih) != '' THEN
                        CASE
                            WHEN length(onay_yazi_tarih) >= 10
                                 AND substr(onay_yazi_tarih, 3, 1) = '.'
                                 AND substr(onay_yazi_tarih, 6, 1) = '.'
                            THEN substr(onay_yazi_tarih, 7, 4) || '-' || substr(onay_yazi_tarih, 4, 2) || '-' || substr(onay_yazi_tarih, 1, 2)
                            ELSE substr(onay_yazi_tarih, 1, 10)
                        END
                    WHEN red_yazi_tarih IS NOT NULL AND TRIM(red_yazi_tarih) != '' THEN
                        CASE
                            WHEN length(red_yazi_tarih) >= 10
                                 AND substr(red_yazi_tarih, 3, 1) = '.'
                                 AND substr(red_yazi_tarih, 6, 1) = '.'
                            THEN substr(red_yazi_tarih, 7, 4) || '-' || substr(red_yazi_tarih, 4, 2) || '-' || substr(red_yazi_tarih, 1, 2)
                            ELSE substr(red_yazi_tarih, 1, 10)
                        END
                    WHEN tarih IS NOT NULL AND TRIM(CAST(tarih AS TEXT)) != '' THEN
                        substr(CAST(tarih AS TEXT), 1, 10)
                    ELSE NULL
                END AS normalized_date,
                durum
            FROM revizyonlar
        ),
        monthly AS (
            SELECT
                substr(normalized_date, 1, 7) as ay,
                SUM(CASE WHEN durum = '{Durum.ONAYLI.value}' THEN 1 ELSE 0 END) as onayli,
                SUM(CASE WHEN durum = '{Durum.ONAYLI_NOTLU.value}' THEN 1 ELSE 0 END) as notlu,
                SUM(CASE WHEN durum = '{Durum.REDDEDILDI.value}' THEN 1 ELSE 0 END) as red,
                COUNT(*) as toplam
            FROM normalized
            WHERE normalized_date IS NOT NULL AND length(normalized_date) >= 7
            GROUP BY substr(normalized_date, 1, 7)
        )
        SELECT ay, onayli, notlu, red, toplam
        FROM (
            SELECT * FROM monthly
            ORDER BY ay DESC
            LIMIT 12
        )
        ORDER BY ay ASC
        """
        try:
            self.cursor.execute(sorgu)
            return self.cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Trend verisi alınamadı: {e}")
            return []

    def get_project_type_statistics(self) -> List[Tuple]:
        """Proje türlerine göre istatistikleri döndür."""
        sorgu = f"""
        SELECT 
            COALESCE(p.proje_turu, 'Belirtilmemiş') as tur,
            COUNT(*) as toplam,
            SUM(CASE WHEN r.durum = '{Durum.ONAYLI.value}' THEN 1 ELSE 0 END) as onayli,
            SUM(CASE WHEN r.durum = '{Durum.ONAYLI_NOTLU.value}' THEN 1 ELSE 0 END) as notlu,
            SUM(CASE WHEN r.durum = '{Durum.REDDEDILDI.value}' THEN 1 ELSE 0 END) as red,
            SUM(CASE WHEN r.durum = '{Durum.ONAYSIZ.value}' OR r.durum IS NULL THEN 1 ELSE 0 END) as bekleyen
        FROM projeler p
        LEFT JOIN revizyonlar r ON p.id = r.proje_id 
            AND r.id = (
                SELECT id FROM revizyonlar WHERE proje_id = p.id 
                ORDER BY proje_rev_no DESC, id DESC LIMIT 1
            )
        GROUP BY COALESCE(p.proje_turu, 'Belirtilmemiş')
        ORDER BY toplam DESC
        """
        try:
            self.cursor.execute(sorgu)
            merged_rows: Dict[str, List[int]] = {}
            for row in self.cursor.fetchall():
                raw_type = row[0]
                normalized_type = normalize_project_type(raw_type)
                display_type = normalized_type or "Belirtilmemiş"
                stats = merged_rows.setdefault(display_type, [0, 0, 0, 0, 0])
                for index, value in enumerate(row[1:]):
                    stats[index] += value or 0
            return sorted(
                [(project_type, *stats) for project_type, stats in merged_rows.items()],
                key=lambda item: item[1],
                reverse=True,
            )
        except Exception as e:
            self.logger.error(f"Proje türü istatistikleri alınamadı: {e}")
            return []

    def excel_verisi_getir(self) -> List[Tuple]:
        """Excel export için proje verilerini getir.
        
        Sütunlar:
        - Proje Kodu, Proje İsmi, Proje Türü, Hiyerarşi
        - Son Gelen Yazı No, Son Gelen Yazı Tarihi, Gelen Yazı Rev Kodu
        - Son Giden Yazı No, Son Giden Yazı Tarihi, Giden Yazı Rev Kodu
        - Son Revizyon Kodu, Revizyon Durumu
        - Açılan Onaylı Doküman Revizyonu (Evet/Hayır)
        """
        sorgu = """
        WITH SonRevizyon AS (
            SELECT *, ROW_NUMBER() OVER(PARTITION BY proje_id ORDER BY proje_rev_no DESC) as rn 
            FROM revizyonlar
        ),
        SonGelenYazi AS (
            SELECT proje_id, gelen_yazi_no, gelen_yazi_tarih, durum, revizyon_kodu, proje_rev_no,
                   ROW_NUMBER() OVER(PARTITION BY proje_id ORDER BY proje_rev_no DESC) as rn
            FROM revizyonlar 
            WHERE gelen_yazi_no IS NOT NULL AND gelen_yazi_no != ''
        ),
        SonGidenYazi AS (
            SELECT proje_id, 
                   COALESCE(NULLIF(onay_yazi_no, ''), NULLIF(red_yazi_no, '')) as giden_yazi_no,
                   COALESCE(NULLIF(onay_yazi_tarih, ''), NULLIF(red_yazi_tarih, '')) as giden_yazi_tarih,
                   durum,
                   revizyon_kodu,
                   proje_rev_no,
                   ROW_NUMBER() OVER(PARTITION BY proje_id ORDER BY proje_rev_no DESC) as rn
            FROM revizyonlar 
            WHERE (onay_yazi_no IS NOT NULL AND onay_yazi_no != '') 
               OR (red_yazi_no IS NOT NULL AND red_yazi_no != '')
        )
        SELECT p.proje_kodu, p.proje_ismi, p.proje_turu, p.hiyerarsi, 
               sgy.gelen_yazi_no,
               CASE WHEN sgy.gelen_yazi_tarih IS NOT NULL 
                    THEN sgy.gelen_yazi_tarih || ' (' || sgy.durum || ')' 
                    ELSE NULL END as gelen_yazi_tarih,
               sgy.revizyon_kodu as gelen_yazi_rev_kodu,
               sgdy.giden_yazi_no,
               CASE WHEN sgdy.giden_yazi_tarih IS NOT NULL 
                    THEN sgdy.giden_yazi_tarih || ' (' || sgdy.durum || ')' 
                    ELSE NULL END as giden_yazi_tarih,
               sgdy.revizyon_kodu as giden_yazi_rev_kodu,
               sr.revizyon_kodu, sr.durum,
               -- İşlem Beklenen: Son tarihli işlem gelen yazı ise Botaş, giden yazı ise Yüklenici
               -- Tarihler DD.MM.YYYY formatında, karşılaştırma için YYYY-MM-DD'ye çeviriyoruz
               CASE 
                   WHEN sgy.gelen_yazi_tarih IS NULL AND sgdy.giden_yazi_tarih IS NULL THEN NULL
                   WHEN sgy.gelen_yazi_tarih IS NULL THEN 'Yüklenici'
                   WHEN sgdy.giden_yazi_tarih IS NULL THEN 'Botaş'
                   WHEN (substr(sgy.gelen_yazi_tarih, 7, 4) || '-' || substr(sgy.gelen_yazi_tarih, 4, 2) || '-' || substr(sgy.gelen_yazi_tarih, 1, 2)) 
                        > (substr(sgdy.giden_yazi_tarih, 7, 4) || '-' || substr(sgdy.giden_yazi_tarih, 4, 2) || '-' || substr(sgdy.giden_yazi_tarih, 1, 2)) 
                   THEN 'Botaş'
                   WHEN (substr(sgdy.giden_yazi_tarih, 7, 4) || '-' || substr(sgdy.giden_yazi_tarih, 4, 2) || '-' || substr(sgdy.giden_yazi_tarih, 1, 2))
                        > (substr(sgy.gelen_yazi_tarih, 7, 4) || '-' || substr(sgy.gelen_yazi_tarih, 4, 2) || '-' || substr(sgy.gelen_yazi_tarih, 1, 2))
                   THEN 'Yüklenici'
                   ELSE NULL
               END as islem_beklenen,
               -- Onaylı Doküman: Eğer son giden yazıda proje onaylıysa ve sonradan yeni gelen yazı geldiyse 'Evet'
               CASE 
                   WHEN sgdy.durum = 'Onayli' 
                        AND sgy.proje_rev_no IS NOT NULL 
                        AND sgy.proje_rev_no > sgdy.proje_rev_no 
                   THEN 'Evet' 
                   ELSE 'Hayır' 
               END as onayli_dokuman
        FROM projeler p 
        LEFT JOIN SonRevizyon sr ON p.id = sr.proje_id AND sr.rn = 1
        LEFT JOIN SonGelenYazi sgy ON p.id = sgy.proje_id AND sgy.rn = 1
        LEFT JOIN SonGidenYazi sgdy ON p.id = sgdy.proje_id AND sgdy.rn = 1
        ORDER BY p.proje_kodu;
        """
        self.cursor.execute(sorgu)
        rows = []
        for row in self.cursor.fetchall():
            row = list(row)
            row[2] = normalize_project_type(row[2])
            rows.append(tuple(row))
        return rows

    # =============================================================================
    # USER AUTHENTICATION METHODS
    # =============================================================================

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        if not BCRYPT_AVAILABLE:
            raise RuntimeError("bcrypt is not installed")
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        if not BCRYPT_AVAILABLE:
            return False
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False

    def create_initial_users(self):
        """Create initial users if users table is empty."""
        try:
            # Check if users table is empty
            row = self.cursor.execute("SELECT COUNT(*) FROM users").fetchone()
            count = row[0] if row else 0
            if count > 0:
                self.logger.info("Users already exist, skipping initial user creation")
                return

            # Create initial users
            initial_users = [
                {
                    "username": "alperb.yilmaz",
                    "password": "Botas.2025",
                    "full_name": "Alper Berkan Yılmaz",
                    "role": "admin"
                },
                {
                    "username": "omer.erbas",
                    "password": "Botas.2025",
                    "full_name": "Ömer Erbaş",
                    "role": "admin"
                }
            ]

            with self.transaction():
                for user_data in initial_users:
                    password_hash = self._hash_password(user_data["password"])
                    self.cursor.execute(
                        """INSERT INTO users (username, password_hash, full_name, role, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            user_data["username"],
                            password_hash,
                            user_data["full_name"],
                            user_data["role"],
                            datetime.datetime.now()
                        )
                    )

            self.logger.info(f"Created {len(initial_users)} initial users")
        except Exception as e:
            self.logger.error(f"Failed to create initial users: {e}", exc_info=True)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information by username."""
        try:
            self.cursor.execute(
                """SELECT id, username, password_hash, full_name, role, created_at, last_login
                   FROM users WHERE username = ?""",
                (username,)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "username": row[1],
                    "password_hash": row[2],
                    "full_name": row[3],
                    "role": row[4],
                    "created_at": row[5],
                    "last_login": row[6]
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get user: {e}", exc_info=True)
            return None

    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials and return user info if valid."""
        user = self.get_user_by_username(username)
        if user and self._verify_password(password, user["password_hash"]):
            return user
        return None

    def update_last_login(self, user_id: int):
        """Update the last_login timestamp for a user."""
        try:
            with self.transaction():
                self.cursor.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.datetime.now(), user_id)
                )
        except Exception as e:
            self.logger.error(f"Failed to update last login: {e}", exc_info=True)

    def __del__(self):
        if hasattr(self, "conn"):
            self._close_main_connection()
