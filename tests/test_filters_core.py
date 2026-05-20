"""
Test suite for advanced filtering functionality.
"""

import pytest
from filters import AdvancedFilterManager, FilterType


class FakeCursor:
    """Minimal cursor stub for filter manager testing."""
    def __init__(self):
        self.last_query = None
        self.last_params = None

    def execute(self, query, params=None):
        self.last_query = query
        self.last_params = params or []
        return self

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeDB:
    def __init__(self):
        self.cursor = FakeCursor()
        self.db_adi = ":memory:"


@pytest.fixture
def filter_manager():
    db = FakeDB()
    mgr = AdvancedFilterManager(db)
    mgr._cache_enabled = False  # Disable cache for clean tests
    return mgr


class TestFilterHashCalculation:
    """Verify that filter hash computation works without type errors."""

    def test_hash_with_no_filters(self, filter_manager):
        """Hash should compute cleanly with empty filter list. No exceptions raised."""
        result = filter_manager.get_filtered_projects(sort_by="id_desc")
        assert isinstance(result, list)

    def test_hash_with_text_filter(self, filter_manager):
        """Hash should work when a TEXT filter is added."""
        filter_manager._cache_enabled = True
        filter_manager.add_filter("proje_kodu", "içerir", "test")
        result = filter_manager.get_filtered_projects(sort_by="kod_asc")
        assert isinstance(result, list)
        assert filter_manager._last_filter_hash is not None

    def test_hash_with_boolean_filter(self, filter_manager):
        """Hash should work when a BOOLEAN filter is added."""
        filter_manager.add_filter("tse_gonderildi", "eşittir", "Evet")
        result = filter_manager.get_filtered_projects(sort_by="id_desc")
        assert isinstance(result, list)

    def test_hash_with_multi_select_filter(self, filter_manager):
        """Hash should work when a MULTI_SELECT filter is added."""
        filter_manager.add_filter("durum", "eşittir", ["Onayli", "Onaysiz"])
        result = filter_manager.get_filtered_projects(sort_by="id_desc")
        assert isinstance(result, list)

    def test_hash_with_red_flag_filter(self, filter_manager):
        """Hash should work when the kirmizi_bayrak filter is added."""
        filter_manager.add_filter("kirmizi_bayrak", "eşittir", "Evet")
        result = filter_manager.get_filtered_projects(sort_by="id_desc")
        assert isinstance(result, list)

    def test_hash_with_multiple_filters(self, filter_manager):
        """Hash should work with multiple filters combined."""
        filter_manager.add_filter("proje_kodu", "içerir", "test")
        filter_manager.add_filter("durum", "eşittir", ["Onayli"])
        filter_manager.add_filter("kirmizi_bayrak", "eşittir", "Hayır")
        result = filter_manager.get_filtered_projects(sort_by="isim_asc")
        assert isinstance(result, list)

    def test_hash_with_date_range_filter(self, filter_manager):
        """Hash should work when a DATE_RANGE filter with dict value is added."""
        filter_manager.add_filter(
            "olusturma_tarihi",
            "arasında",
            {"start": "2026-01-01", "end": "2026-12-31"},
        )
        result = filter_manager.get_filtered_projects(sort_by="id_desc")
        assert isinstance(result, list)

    def test_hash_multiple_sort_options(self, filter_manager):
        """Hash should handle all sort options."""
        for sort_key in ["id_desc", "id_asc", "kod_asc", "kod_desc", "isim_asc", "isim_desc"]:
            filter_manager.add_filter("proje_ismi", "eşittir", "test")
            result = filter_manager.get_filtered_projects(sort_by=sort_key)
            assert isinstance(result, list)
            filter_manager.active_filters.clear()
            filter_manager.clear_cache()

    def test_hash_consistency(self, filter_manager):
        """Same filters + sort should produce same hash result."""
        filter_manager.add_filter("proje_kodu", "içerir", "PRJ")
        result1 = filter_manager.get_filtered_projects(sort_by="kod_asc")
        hash1 = filter_manager._last_filter_hash
        filter_manager.clear_cache()
        result2 = filter_manager.get_filtered_projects(sort_by="kod_asc")
        hash2 = filter_manager._last_filter_hash
        assert hash1 == hash2, "Same filter+sort should produce identical hash"
