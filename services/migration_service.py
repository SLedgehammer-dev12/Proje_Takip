import logging
import sqlite3
from typing import Optional


class MigrationService:
    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        self.cursor = self.conn.cursor()
        self.logger = logging.getLogger(__name__)
        # Ensure migration markers table exists
        try:
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS applied_migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TIMESTAMP
                )
                """
            )
            self.conn.commit()
        except Exception:
            # If creation fails, continue; migration logic will handle idempotence defensively
            pass

    def run_migrations(self):
        """Tüm migration işlemlerini çalıştır"""
        self._migrate_schema()
        self._migrate_data()

    def _migrate_schema(self):
        """Şema değişikliklerini uygula"""
        sutunlar = {
            "revizyonlar": [
                "gelen_yazi_no TEXT",
                "gelen_yazi_tarih TEXT",
                "onay_yazi_no TEXT",
                "onay_yazi_tarih TEXT",
                "red_yazi_no TEXT",
                "red_yazi_tarih TEXT",
                "proje_rev_no INTEGER",
                "tse_gonderildi INTEGER DEFAULT 0",
                "tse_yazi_no TEXT",
                "tse_yazi_tarih TEXT",
                "yazi_turu TEXT DEFAULT 'gelen'",
            ],
            "projeler": [
                "olusturma_tarihi TIMESTAMP",
                "hiyerarsi TEXT",
                "kategori_id INTEGER REFERENCES kategoriler (id) ON DELETE SET NULL",
            ],
        }
        for tablo, sutun_listesi in sutunlar.items():
            for sutun_tanimi in sutun_listesi:
                try:
                    self.cursor.execute(
                        f"ALTER TABLE {tablo} ADD COLUMN {sutun_tanimi}"
                    )
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        raise

    def _migrate_data(self):
        """Veri dönüşümlerini uygula"""
        self._migrate_yazi_turu()
        self._cleanup_noncanonical_yazi_turu()
        self._migrate_hierarchy_to_categories()
        self._migrate_revision_status_inheritance()

    def _migrate_yazi_turu(self):
        """Revizyon yazı türlerini güncelle"""
        try:
            # Gelen yazı olanlar
            self.cursor.execute(
                """
                UPDATE revizyonlar 
                SET yazi_turu = 'gelen' 
                WHERE yazi_turu IS NULL 
                AND (gelen_yazi_no IS NOT NULL OR revizyon_kodu = 'A')
            """
            )

            # Onay/Red yazısı olanlar
            self.cursor.execute(
                """
                UPDATE revizyonlar 
                SET yazi_turu = 'giden' 
                WHERE yazi_turu IS NULL 
                AND (onay_yazi_no IS NOT NULL OR red_yazi_no IS NOT NULL)
            """
            )

            # Diğerleri (yazı yok)
            self.cursor.execute(
                """
                UPDATE revizyonlar 
                SET yazi_turu = 'yok' 
                WHERE yazi_turu IS NULL
            """
            )

            self.logger.info("Mevcut revizyonlar için yazi_turu değerleri ayarlandı")
        except Exception as e:
            self.logger.warning(f"yazi_turu migration hatası (normal olabilir): {e}")

    def _cleanup_noncanonical_yazi_turu(self):
        """Fix existing rows where yazi_turu contains non-canonical values like project type names.

        We will set canonical values ('gelen', 'giden', 'yok') based on available yazı columns.
        """
        try:
            # Prefer 'giden' if onay or red exists, fallback to 'gelen' if incoming exists
            self.cursor.execute(
                """
                UPDATE revizyonlar
                SET yazi_turu = CASE
                    WHEN onay_yazi_no IS NOT NULL AND onay_yazi_no != '' THEN 'giden'
                    WHEN red_yazi_no IS NOT NULL AND red_yazi_no != '' THEN 'giden'
                    WHEN gelen_yazi_no IS NOT NULL AND gelen_yazi_no != '' THEN 'gelen'
                    ELSE 'yok'
                END
                WHERE yazi_turu NOT IN ('gelen', 'giden', 'yok') OR yazi_turu IS NULL
                """
            )
            self.conn.commit()
            self.logger.info("Non-canonical yazi_turu değerleri dönüştürüldü")
        except Exception as e:
            self.logger.warning(f"Non-canonical yazi_turu cleanup hatası: {e}")

    def _migrate_hierarchy_to_categories(self):
        """Eski hiyerarşi metinlerini kategori yapısına taşı"""
        try:
            self.cursor.execute("SELECT COUNT(id) FROM kategoriler")
            if self.cursor.fetchone()[0] > 0:
                return  # Zaten yapılmış

            self.cursor.execute(
                "SELECT COUNT(id) FROM projeler WHERE hiyerarsi IS NOT NULL AND hiyerarsi != ''"
            )
            if self.cursor.fetchone()[0] == 0:
                return  # Taşınacak veri yok

            self.logger.info(
                "Veritabanı taşıma işlemi başlıyor: 'hiyerarsi' metninden 'kategori_id'ye..."
            )
            self.cursor.execute(
                "SELECT id, hiyerarsi FROM projeler WHERE hiyerarsi IS NOT NULL AND hiyerarsi != ''"
            )
            projeler = self.cursor.fetchall()

            kategori_cache = {}
            # Transaction dışarıda yönetilmeli veya burada başlatılmalı
            # Burada çağıran tarafın transaction içinde olduğunu varsayıyoruz veya kendimiz yönetiyoruz
            # Ancak MigrationService genellikle başlatma sırasında çağrılır.

            for proje_id, hiyerarsi_str in projeler:
                if hiyerarsi_str in kategori_cache:
                    kategori_id = kategori_cache[hiyerarsi_str]
                else:
                    kategori_id = self._find_or_create_category_path(hiyerarsi_str)
                    if kategori_id:
                        kategori_cache[hiyerarsi_str] = kategori_id

                if kategori_id:
                    self.cursor.execute(
                        "UPDATE projeler SET kategori_id = ? WHERE id = ?",
                        (kategori_id, proje_id),
                    )

            self.conn.commit()
            self.logger.info(
                f"Veritabanı taşıma işlemi tamamlandı. {len(projeler)} proje işlendi."
            )

        except Exception as e:
            self.logger.critical(
                f"Veritabanı taşıma işlemi başarısız oldu: {e}", exc_info=True
            )
            self.conn.rollback()

    def _find_or_create_category_path(self, hierarchy_str: str) -> Optional[int]:
        """'Mekanik/Pompalar' gibi bir yolu kategorilere çevirir"""
        if not hierarchy_str:
            return None

        if isinstance(hierarchy_str, int):
            return hierarchy_str

        try:
            parts = str(hierarchy_str).split("/")
            current_parent_id = None

            for part in parts:
                part = part.strip()
                if not part:
                    continue

                if current_parent_id is None:
                    self.cursor.execute(
                        "SELECT id FROM kategoriler WHERE isim = ? AND parent_id IS NULL",
                        (part,),
                    )
                else:
                    self.cursor.execute(
                        "SELECT id FROM kategoriler WHERE isim = ? AND parent_id = ?",
                        (part, current_parent_id),
                    )

                result = self.cursor.fetchone()

                if result:
                    current_parent_id = result[0]
                else:
                    self.cursor.execute(
                        "INSERT INTO kategoriler (isim, parent_id) VALUES (?, ?)",
                        (part, current_parent_id),
                    )
                    current_parent_id = self.cursor.lastrowid

            return current_parent_id

        except Exception as e:
            self.logger.critical(
                f"Kategori ID'si oluşturulurken hata: '{hierarchy_str}' - {e}"
            )
            return None

    def _migrate_revision_status_inheritance(self):
        """
        Apply status inheritance rules to existing revisions retroactively.
        
        For each project, iterate through revisions in chronological order
        and update their status based on the previous revision's status,
        following the same inheritance logic as new revisions.
        """
        migration_name = "revizyon_durum_inheritance_v1"
        try:
            # Skip if this migration has already been applied
            self.cursor.execute(
                "SELECT 1 FROM applied_migrations WHERE name = ?",
                (migration_name,),
            )
            if self.cursor.fetchone():
                self.logger.info(
                    "Revizyon durum devralma migration zaten uygulanmış - atlanıyor"
                )
                return
            # Check if migration already ran
            self.cursor.execute(
                """SELECT COUNT(*) FROM revizyonlar 
                   WHERE durum IN ('Onayli', 'Notlu Onayli')"""
            )
            approved_count = self.cursor.fetchone()[0]
            
            if approved_count == 0:
                # No approved revisions, skip migration
                return
            
            # Get all projects
            self.cursor.execute("SELECT id FROM projeler ORDER BY id")
            projeler = self.cursor.fetchall()
            
            updated_count = 0
            
            for (proje_id,) in projeler:
                # Get all revisions for this project in chronological order
                self.cursor.execute(
                    """SELECT id, durum, proje_rev_no 
                       FROM revizyonlar 
                       WHERE proje_id = ? 
                       ORDER BY proje_rev_no ASC, id ASC""",
                    (proje_id,)
                )
                revizyonlar = self.cursor.fetchall()
                
                if len(revizyonlar) <= 1:
                    continue  # Skip if only one or no revisions
                
                # Process revisions starting from the second one
                for i in range(1, len(revizyonlar)):
                    current_id, current_durum, current_rev_no = revizyonlar[i]
                    prev_id, prev_durum, prev_rev_no = revizyonlar[i-1]
                    
                    # Apply inheritance logic
                    if prev_durum in ['Onayli', 'Notlu Onayli']:
                        # Previous was approved -> inherit
                        if current_durum != prev_durum:
                            self.cursor.execute(
                                "UPDATE revizyonlar SET durum = ? WHERE id = ?",
                                (prev_durum, current_id)
                            )
                            updated_count += 1
                    # If previous was rejected or pending, current stays as-is
            
            self.conn.commit()
            
            if updated_count > 0:
                self.logger.info(
                    f"Revizyon durum devralma migration tamamlandı: {updated_count} revizyon güncellendi"
                )
            # Mark migration as applied (idempotent)
            try:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO applied_migrations (name, applied_at) VALUES (?, datetime('now'))",
                    (migration_name,),
                )
                self.conn.commit()
            except Exception:
                pass
            else:
                self.logger.info(
                    "Revizyon durum devralma migration: Güncellenecek revizyon bulunamadı"
                )
                
        except Exception as e:
            self.logger.warning(
                f"Revizyon durum devralma migration hatası (normal olabilir): {e}"
            )
            self.conn.rollback()
