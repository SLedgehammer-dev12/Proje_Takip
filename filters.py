# filters.py
from PySide6.QtCore import QObject, Signal
from typing import Dict, List, Any
from enum import Enum

# ProjeModel importu eklendi
from models import ProjeModel
from project_types import (
    PROJECT_TYPE_FILTER_OPTIONS,
    get_project_type_aliases,
    normalize_project_type,
)


class FilterType(Enum):
    TEXT = "text"
    DATE_RANGE = "date_range"
    # STATUS kaldırıldı, kullanılmıyordu
    MULTI_SELECT = "multi_select"
    BOOLEAN = "boolean"


class FilterCondition:
    def __init__(
        self, field: str, operator: str, value: Any, filter_type: FilterType, all_revisions: bool = False
    ):
        self.field = field
        self.operator = operator
        self.value = value
        # If true, apply to all revizyonlar via EXISTS (for ya? fields)
        self.all_revisions = all_revisions
        self.filter_type = filter_type


class AdvancedFilterManager(QObject):
    """Manages filters with memory optimization and caching"""

    filter_changed = Signal()

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.active_filters: List[FilterCondition] = []
        self.available_filters = self._initialize_available_filters()
        self._populate_dynamic_options()

        # Cache for filtered results
        self._filtered_cache = None
        self._last_filter_hash = None

        # Memory optimization settings
        self.CACHE_LIMIT = 1000  # Max items to cache
        self._cache_enabled = True  # Can be disabled for large datasets
        self._notification_suspend_count = 0
        self._pending_filter_change = False

    def _initialize_available_filters(self) -> Dict[str, Dict]:
        # --- TÜM TİPLER BURADA KONTROL EDİLDİ VE DÜZELTİLDİ ---
        return {
            "proje_kodu": {
                "label": "Proje Kodu",
                "type": FilterType.TEXT,  # Doğru
                "operators": ["içerir", "eşittir", "ile başlar", "ile biter"],
            },
            "proje_ismi": {
                "label": "Proje İsmi",
                "type": FilterType.TEXT,  # Düzeltildi (veya doğrulandı)
                "operators": ["içerir", "eşittir", "ile başlar"],
            },
            "proje_turu": {
                "label": "Proje Türü",
                "type": FilterType.MULTI_SELECT,  # Düzeltildi (veya doğrulandı)
                "operators": ["eşittir"],
                "options": PROJECT_TYPE_FILTER_OPTIONS,
            },
            "durum": {
                "label": "Revizyon Durumu",
                "type": FilterType.MULTI_SELECT,  # Doğru
                "operators": ["eşittir"],
                "options": ["Onayli", "Onaysiz", "Reddedildi", "Notlu Onayli"],
            },
            "tse_gonderildi": {
                "label": "TSE'ye Gönderildi",
                "type": FilterType.BOOLEAN,  # Doğru
                "operators": ["eşittir"],
                "options": ["Evet", "Hayır"],
            },
            "olusturma_tarihi": {
                "label": "Oluşturma Tarihi",
                "type": FilterType.DATE_RANGE,  # Doğru
                "operators": ["arasında", "büyük", "küçük", "eşittir"],
            },
            "hiyerarsi": {
                "label": "Kategori Yolu",
                "type": FilterType.TEXT,  # Düzeltildi (veya doğrulandı)
                "operators": ["içerir", "eşittir"],
            },
            "gelen_yazi_no": {
                "label": "Gelen Yazı No",
                "type": FilterType.TEXT,  # Düzeltildi (veya doğrulandı)
                "operators": ["içerir", "eşittir"],
            },
            "onay_yazi_no": {
                "label": "Onay Yazı No",
                "type": FilterType.TEXT,  # Düzeltildi (veya doğrulandı)
                "operators": ["içerir", "eşittir"],
            },
            "giden_yazi_no": {
                "label": "Giden Yazı No",
                "type": FilterType.TEXT,
                "operators": ["içerir", "eşittir", "ile başlar", "ile biter"],
            },
            "red_yazi_no": {
                "label": "Red Yazı No",
                "type": FilterType.TEXT,  # Düzeltildi (veya doğrulandı)
                "operators": ["içerir", "eşittir"],
            },
            "son_gelen_yazi_tarihi": {
                "label": "Son Gelen Yazı Tarihi",
                "type": FilterType.DATE_RANGE,  # Düzeltildi (veya doğrulandı)
                "operators": ["arasında", "büyük", "küçük", "eşittir"],
            },
            "yazi_yili": {
                "label": "Yazı Yılı",
                "type": FilterType.MULTI_SELECT,
                "operators": ["eşittir"],
                "options": [],  # Dinamik olarak DB'den yuklenir
            },
            "takip_notu": {
                "label": "Takip Notu",
                "type": FilterType.TEXT,
                "operators": ["içerir", "eşittir", "ile başlar", "ile biter"],
            },
            "takip_durumu": {
                "label": "Takip Durumu",
                "type": FilterType.MULTI_SELECT,
                "operators": ["eşittir"],
                "options": ["Takipte", "Takipten Çıkarıldı", "Takipsiz"],
            },
        }

    def _populate_dynamic_options(self):
        """Dinamik filtre seceneklerini veritabanindan yukle."""
        try:
            yazi_yili_config = self.available_filters.get("yazi_yili")
            if yazi_yili_config and hasattr(self.db, "get_distinct_yazi_yillari"):
                years = self.db.get_distinct_yazi_yillari()
                yazi_yili_config["options"] = years if years else []
        except Exception:
            pass

    def add_filter(self, field: str, operator: str, value: Any):
        filter_config = self.available_filters.get(field)
        if not filter_config:
            return False

        # value may be a dict like {'value': <val>, 'all_revisions': True} from AdvancedFilterDialog
        all_revs = False
        if isinstance(value, dict) and "all_revisions" in value:
            all_revs = bool(value.get("all_revisions", False))
            value = value.get("value")

        condition = FilterCondition(field, operator, value, filter_config["type"], all_revs)
        self.active_filters.append(condition)
        self._emit_filter_changed()
        return True

    def remove_filter(self, index: int):
        if 0 <= index < len(self.active_filters):
            self.active_filters.pop(index)
            self._emit_filter_changed()

    def clear_filters(self):
        self.active_filters.clear()
        self._emit_filter_changed()

    def begin_batch_update(self):
        self._notification_suspend_count += 1

    def end_batch_update(self, emit: bool = True):
        if self._notification_suspend_count > 0:
            self._notification_suspend_count -= 1
        if (
            emit
            and self._notification_suspend_count == 0
            and self._pending_filter_change
        ):
            self._pending_filter_change = False
            self.filter_changed.emit()
        elif self._notification_suspend_count == 0:
            self._pending_filter_change = False

    def _emit_filter_changed(self):
        if self._notification_suspend_count > 0:
            self._pending_filter_change = True
            return
        self.filter_changed.emit()

    def build_sql_where_clause(self) -> tuple[str, list]:
        if not self.active_filters:
            return "", []

        where_parts = []
        params = []

        for condition in self.active_filters:
            sql_condition, sql_params = self._build_sql_condition(condition)
            if sql_condition:
                where_parts.append(sql_condition)
                params.extend(sql_params)

        if where_parts:
            return "WHERE " + " AND ".join(where_parts), params
        return "", []

    def _build_sql_condition(self, condition: FilterCondition) -> tuple[str, list]:
        field = condition.field
        operator = condition.operator
        value = condition.value
        all_revs = getattr(condition, "all_revisions", False)

        # SQL field mapping - r alias kullanımına dikkat!
        field_mapping = {
            "proje_kodu": "p.proje_kodu",
            "proje_ismi": "p.proje_ismi",
            "proje_turu": "p.proje_turu",
            "durum": "r.durum",
            "tse_gonderildi": "r.tse_gonderildi",
            "olusturma_tarihi": "p.olusturma_tarihi",
            "hiyerarsi": "p.hiyerarsi",  # TEXT alanı için
            "gelen_yazi_no": "r.gelen_yazi_no",
            "onay_yazi_no": "r.onay_yazi_no",
            "red_yazi_no": "r.red_yazi_no",
            "son_gelen_yazi_tarihi": "r.gelen_yazi_tarih",  # Dikkat: tarih alanı
        }

        sql_field = field_mapping.get(field, field)

        # Takip notu ve takip durumu filtreleri projeye bağlı tüm revizyonlarda aranır.
        if field == "takip_notu":
            return self._build_takip_notu_condition(operator, value)
        if field == "takip_durumu":
            return self._build_takip_durumu_condition(value)

        if condition.filter_type == FilterType.TEXT:
            # Special-case: yazı numarası filters
            if field in ("gelen_yazi_no", "onay_yazi_no", "red_yazi_no", "giden_yazi_no"):
                col = field  # same column name in revizyonlar
                if all_revs:
                    # Build an EXISTS subquery that inspects all revizyonlar rows for that project.
                    # NOTE: giden_yazi_no is virtual (onay_yazi_no OR red_yazi_no), no direct DB column exists.
                    if field == "giden_yazi_no":
                        return self._build_all_revisions_giden_condition(operator, value)
                    return self._build_all_revisions_single_yazi_condition(col, operator, value)
                # If not all_revs, compare against the last non-null yazı value for the project
                # Use a subquery that picks the last revizyon where the yazı value is not null
                # ORDER BY proje_rev_no DESC, id DESC ensures last revision ordering
                if operator == "eşittir":
                    if field == "giden_yazi_no":
                        # Compare last non-null of onay or red
                        return (
                            "(((SELECT rev.onay_yazi_no FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.onay_yazi_no IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) IS NOT NULL AND (SELECT rev.onay_yazi_no FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.onay_yazi_no IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) = ?) OR ((SELECT rev.red_yazi_no FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.red_yazi_no IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) IS NOT NULL AND (SELECT rev.red_yazi_no FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.red_yazi_no IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) = ?))",
                            [value, value],
                        )
                    else:
                        return (
                            f"((SELECT rev.{field} FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.{field} IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) = ?)",
                            [value],
                        )
                elif operator == "içerir":
                    if field == "giden_yazi_no":
                        return (
                            "(((SELECT rev.onay_yazi_no FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.onay_yazi_no IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) LIKE ?) OR ((SELECT rev.red_yazi_no FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.red_yazi_no IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) LIKE ?))",
                            [f"%{value}%", f"%{value}%"],
                        )
                    else:
                        return (
                            f"((SELECT rev.{field} FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.{field} IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) LIKE ?)",
                            [f"%{value}%"],
                        )
                elif operator == "ile başlar":
                    if field == "giden_yazi_no":
                        return (
                            "(((SELECT rev.onay_yazi_no FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.onay_yazi_no IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) LIKE ?) OR ((SELECT rev.red_yazi_no FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.red_yazi_no IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) LIKE ?))",
                            [f"{value}%", f"{value}%"],
                        )
                    else:
                        return (
                            f"((SELECT rev.{field} FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.{field} IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) LIKE ?)",
                            [f"{value}%"],
                        )
                elif operator == "ile biter":
                    if field == "giden_yazi_no":
                        return (
                            "(((SELECT rev.onay_yazi_no FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.onay_yazi_no IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) LIKE ?) OR ((SELECT rev.red_yazi_no FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.red_yazi_no IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) LIKE ?))",
                            [f"%{value}", f"%{value}"],
                        )
                    else:
                        return (
                            f"((SELECT rev.{field} FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.{field} IS NOT NULL ORDER BY rev.proje_rev_no DESC, rev.id DESC LIMIT 1) LIKE ?)",
                            [f"%{value}"],
                        )
                return "", []
            return self._build_text_condition(sql_field, operator, value)
        elif condition.filter_type == FilterType.MULTI_SELECT:
            # Yazi yili ozel filtresi
            if field == "yazi_yili":
                return self._build_yazi_yili_condition(value)
            if field == "proje_turu":
                return self._build_project_type_multi_select_condition(value)
            return self._build_multi_select_condition(sql_field, value)
        elif condition.filter_type == FilterType.BOOLEAN:
            return self._build_boolean_condition(sql_field, value)
        elif condition.filter_type == FilterType.DATE_RANGE:
            return self._build_date_condition(sql_field, operator, value)

        return "", []

    def _build_all_revisions_single_yazi_condition(
        self, column: str, operator: str, value: str
    ) -> tuple[str, list]:
        if operator == "eşittir":
            return (
                f"(EXISTS (SELECT 1 FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.{column} = ?))",
                [value],
            )
        if operator == "içerir":
            return (
                f"(EXISTS (SELECT 1 FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.{column} LIKE ?))",
                [f"%{value}%"],
            )
        if operator == "ile başlar":
            return (
                f"(EXISTS (SELECT 1 FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.{column} LIKE ?))",
                [f"{value}%"],
            )
        if operator == "ile biter":
            return (
                f"(EXISTS (SELECT 1 FROM revizyonlar rev WHERE rev.proje_id = p.id AND rev.{column} LIKE ?))",
                [f"%{value}"],
            )
        return "", []

    def _build_all_revisions_giden_condition(
        self, operator: str, value: str
    ) -> tuple[str, list]:
        if operator == "eşittir":
            return (
                "(EXISTS (SELECT 1 FROM revizyonlar rev WHERE rev.proje_id = p.id AND (rev.onay_yazi_no = ? OR rev.red_yazi_no = ?)))",
                [value, value],
            )
        if operator == "içerir":
            return (
                "(EXISTS (SELECT 1 FROM revizyonlar rev WHERE rev.proje_id = p.id AND (rev.onay_yazi_no LIKE ? OR rev.red_yazi_no LIKE ?)))",
                [f"%{value}%", f"%{value}%"],
            )
        if operator == "ile başlar":
            return (
                "(EXISTS (SELECT 1 FROM revizyonlar rev WHERE rev.proje_id = p.id AND (rev.onay_yazi_no LIKE ? OR rev.red_yazi_no LIKE ?)))",
                [f"{value}%", f"{value}%"],
            )
        if operator == "ile biter":
            return (
                "(EXISTS (SELECT 1 FROM revizyonlar rev WHERE rev.proje_id = p.id AND (rev.onay_yazi_no LIKE ? OR rev.red_yazi_no LIKE ?)))",
                [f"%{value}", f"%{value}"],
            )
        return "", []

    def _build_text_condition(
        self, field: str, operator: str, value: str
    ) -> tuple[str, list]:
        """TEXT filtreleme - NULL kontrollü"""
        if not value:  # Boş değer kontrolü
            return "", []

        if operator == "içerir":
            # NULL değerleri de kontrol et
            return f"({field} IS NOT NULL AND {field} LIKE ?)", [f"%{value}%"]
        elif operator == "eşittir":
            return f"{field} = ?", [value]
        elif operator == "ile başlar":
            return f"({field} IS NOT NULL AND {field} LIKE ?)", [f"{value}%"]
        elif operator == "ile biter":
            return f"({field} IS NOT NULL AND {field} LIKE ?)", [f"%{value}"]
        return "", []

    def _build_multi_select_condition(
        self, field: str, values: list
    ) -> tuple[str, list]:
        """MULTI_SELECT filtreleme - boş liste ve NULL kontrollü"""
        if not values or not isinstance(values, list):
            return "", []

        # Liste elemanlarını temizle
        clean_values = [v for v in values if v]
        if not clean_values:
            return "", []

        # Özel durum: 'Belirtilmemiş' seçeneği, alanın NULL veya boş string olduğu kayıtları
        # temsil eder. Eğer seçildiyse, onu IN listeden çıkarıp SQL sorgusuna özel koşul ekle.
        special_marker = "Belirtilmemiş"
        include_null_empty = False
        if special_marker in clean_values:
            include_null_empty = True
            clean_values = [v for v in clean_values if v != special_marker]

        parts = []
        params = []

        if clean_values:
            placeholders = ",".join("?" * len(clean_values))
            # Field must be non-null to match values in IN
            parts.append(f"({field} IS NOT NULL AND {field} IN ({placeholders}))")
            params.extend(clean_values)

        if include_null_empty:
            parts.append(f"({field} IS NULL OR TRIM({field}) = '')")

        # Birden fazla koşul varsa OR ile birleştir
        if parts:
            return "(" + " OR ".join(parts) + ")", params
        return "", []

    def _build_project_type_multi_select_condition(self, values: list) -> tuple[str, list]:
        if not values or not isinstance(values, list):
            return "", []

        include_null_empty = False
        canonical_values = []
        seen = set()

        for raw_value in values:
            if not raw_value:
                continue
            if raw_value == "Belirtilmemiş":
                include_null_empty = True
                continue
            normalized_value = normalize_project_type(raw_value)
            if normalized_value and normalized_value not in seen:
                canonical_values.append(normalized_value)
                seen.add(normalized_value)

        parts = []
        params = []

        for canonical_value in canonical_values:
            aliases = list(get_project_type_aliases(canonical_value))
            if not aliases:
                continue
            placeholders = ",".join("?" * len(aliases))
            parts.append(
                f"(p.proje_turu IS NOT NULL AND TRIM(p.proje_turu) != '' AND p.proje_turu IN ({placeholders}))"
            )
            params.extend(aliases)

        if include_null_empty:
            parts.append("(p.proje_turu IS NULL OR TRIM(p.proje_turu) = '')")

        if parts:
            return "(" + " OR ".join(parts) + ")", params
        return "", []

    def _build_boolean_condition(self, field: str, value: str) -> tuple[str, list]:
        bool_value = 1 if value == "Evet" else 0
        return f"{field} = ?", [bool_value]

    def _build_date_condition(
        self, field: str, operator: str, value: dict
    ) -> tuple[str, list]:
        """DATE_RANGE filtreleme - YYYY-MM-DD normalize edilerek karşılaştırılır."""
        if not isinstance(value, dict):
            return "", []

        start = self._normalize_date_value(value.get("start"))
        end = self._normalize_date_value(value.get("end"))
        sql_date_expr = self._build_sql_date_expr(field)

        if operator == "arasında" and "start" in value and "end" in value:
            if not start or not end:
                return "", []
            return f"({sql_date_expr} IS NOT NULL AND {sql_date_expr} BETWEEN ? AND ?)", [
                start,
                end,
            ]
        elif operator == "büyük" and start:
            return f"({sql_date_expr} IS NOT NULL AND {sql_date_expr} > ?)", [start]
        elif operator == "küçük" and end:
            return f"({sql_date_expr} IS NOT NULL AND {sql_date_expr} < ?)", [end]
        elif operator == "eşittir" and start:
            return f"{sql_date_expr} = ?", [start]
        return "", []

    def _build_sql_date_expr(self, field: str) -> str:
        # Yazı tarihleri DD.MM.YYYY olarak saklanıyor; ISO formata normalize ediyoruz.
        if field in ("r.gelen_yazi_tarih", "r.onay_yazi_tarih", "r.red_yazi_tarih"):
            return (
                f"(CASE "
                f"WHEN {field} IS NULL OR TRIM({field}) = '' THEN NULL "
                f"WHEN length({field}) >= 10 AND substr({field}, 3, 1) = '.' AND substr({field}, 6, 1) = '.' "
                f"THEN substr({field}, 7, 4) || '-' || substr({field}, 4, 2) || '-' || substr({field}, 1, 2) "
                f"ELSE substr({field}, 1, 10) END)"
            )
        return f"date({field})"

    def _normalize_date_value(self, raw: Any) -> str:
        if raw is None:
            return ""
        text = str(raw).strip()
        if len(text) >= 10 and text[2:3] == "." and text[5:6] == ".":
            return f"{text[6:10]}-{text[3:5]}-{text[0:2]}"
        return text[:10]

    def _build_yazi_yili_condition(self, years: list) -> tuple[str, list]:
        """Yazi yili filtresi -- revizyondaki herhangi bir yazi tarihinin yili secilen yillardan biri olmali."""
        if not years or not isinstance(years, list):
            return "", []

        clean_years = [y for y in years if y and len(y) == 4 and y.isdigit()]
        if not clean_years:
            return "", []

        placeholders = ",".join("?" * len(clean_years))

        condition = f"""(EXISTS (
            SELECT 1 FROM revizyonlar rev
            WHERE rev.proje_id = p.id
            AND (
                (rev.gelen_yazi_tarih IS NOT NULL AND length(rev.gelen_yazi_tarih) >= 10
                 AND substr(rev.gelen_yazi_tarih, 7, 4) IN ({placeholders}))
                OR (rev.onay_yazi_tarih IS NOT NULL AND length(rev.onay_yazi_tarih) >= 10
                    AND substr(rev.onay_yazi_tarih, 7, 4) IN ({placeholders}))
                OR (rev.red_yazi_tarih IS NOT NULL AND length(rev.red_yazi_tarih) >= 10
                    AND substr(rev.red_yazi_tarih, 7, 4) IN ({placeholders}))
            )
        ))"""

        params = clean_years * 3  # 3 tarih alani icin
        return condition, params

    def _build_takip_notu_condition(self, operator: str, value: str) -> tuple[str, list]:
        if not value:
            return "", []
        base = (
            "EXISTS ("
            "SELECT 1 FROM revizyon_takipleri t "
            "JOIN revizyonlar rev ON rev.id = t.revizyon_id "
            "WHERE rev.proje_id = p.id AND t.takip_notu IS NOT NULL AND TRIM(t.takip_notu) != '' "
        )
        if operator == "eşittir":
            return base + "AND t.takip_notu = ?)", [value]
        if operator == "içerir":
            return base + "AND t.takip_notu LIKE ?)", [f"%{value}%"]
        if operator == "ile başlar":
            return base + "AND t.takip_notu LIKE ?)", [f"{value}%"]
        if operator == "ile biter":
            return base + "AND t.takip_notu LIKE ?)", [f"%{value}"]
        return "", []

    def _build_takip_durumu_condition(self, values: list) -> tuple[str, list]:
        if not values or not isinstance(values, list):
            return "", []
        clean_values = [v for v in values if v]
        if not clean_values:
            return "", []

        parts = []
        if "Takipte" in clean_values:
            parts.append(
                "EXISTS ("
                "SELECT 1 FROM revizyon_takipleri t "
                "JOIN revizyonlar rev ON rev.id = t.revizyon_id "
                "WHERE rev.proje_id = p.id AND t.aktif = 1)"
            )
        if "Takipten Çıkarıldı" in clean_values:
            parts.append(
                "EXISTS ("
                "SELECT 1 FROM revizyon_takipleri t "
                "JOIN revizyonlar rev ON rev.id = t.revizyon_id "
                "WHERE rev.proje_id = p.id AND t.aktif = 0)"
            )
        if "Takipsiz" in clean_values:
            parts.append(
                "NOT EXISTS ("
                "SELECT 1 FROM revizyon_takipleri t "
                "JOIN revizyonlar rev ON rev.id = t.revizyon_id "
                "WHERE rev.proje_id = p.id)"
            )

        if not parts:
            return "", []
        return "(" + " OR ".join(parts) + ")", []

    def get_filtered_projects(self) -> List[ProjeModel]:
        """
        Filtrelenmiş projeleri döndürür - optimize edilmiş sorgu
        Cache mekanizması ile performans iyileştirmesi
        """
        # Cache kontrolü
        filter_hash = hash(
            str(
                [
                    (
                        f.field,
                        f.operator,
                        str(f.value),
                        bool(getattr(f, "all_revisions", False)),
                    )
                    for f in self.active_filters
                ]
            )
        )

        if (
            self._cache_enabled
            and self._last_filter_hash == filter_hash
            and self._filtered_cache
        ):
            return self._filtered_cache

        where_clause, params = self.build_sql_where_clause()

        # Optimize edilmiş sorgu - ROW_NUMBER() CTE ile
        sorgu = f"""
        WITH SonRevizyon AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY proje_id ORDER BY proje_rev_no DESC, id DESC) AS rn
            FROM revizyonlar
        )
        SELECT
            p.id,
            p.proje_kodu,
            p.proje_ismi,
            p.proje_turu,
            r.gelen_yazi_no,
            r.gelen_yazi_tarih,
            CASE
                WHEN r.durum = 'Onayli' THEN 'yesil'
                WHEN r.durum = 'Notlu Onayli' THEN 'yesil'
                WHEN r.durum = 'Reddedildi' THEN 'kirmizi'
                WHEN r.durum = 'Onaysiz' THEN 'mavi'
                ELSE 'gri'
            END as durum_renk,
            p.hiyerarsi,
            r.durum,
            r.tse_gonderildi,
            r.onay_yazi_no,
            r.red_yazi_no,
            p.kategori_id
        FROM projeler p
        LEFT JOIN SonRevizyon r ON p.id = r.proje_id AND r.rn = 1
        {where_clause}
        ORDER BY p.id DESC
        """

        self.db.cursor.execute(sorgu, params)
        results = [ProjeModel(*row) for row in self.db.cursor.fetchall()]

        # Cache'e kaydet (boyut limiti ile)
        if self._cache_enabled and len(results) <= self.CACHE_LIMIT:
            self._filtered_cache = results
            self._last_filter_hash = filter_hash

        return results

    def clear_cache(self):
        """Cache'i manuel olarak temizle"""
        self._filtered_cache = None
        self._last_filter_hash = None
