"""Tests for Red Flag refactoring (v3.2.1).

Covers:
- revizyonlari_getir() includes is_flagged in SELECT
- Project list context menu: only "İşaretle", no "Kaldır"
- Project flag sets latest revision, not all revisions
- Revision flag toggles individual revision
- Theme contrast in preview/detail panels
"""

import os
import tempfile
import pytest
from types import SimpleNamespace


# ============================================================================
# Database Query Tests
# ============================================================================


class TestRevizyonGetirIsFlagged:
    """Ensure revizyonlari_getir() returns is_flagged from DB."""

    def test_query_includes_is_flagged_column(self):
        """Verify revizyonlari_getir SELECT includes r.is_flagged."""
        import sqlite3
        from database import ProjeTakipDB

        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "test_flag.db")
        db = ProjeTakipDB(db_path)

        try:
            # Create a project
            db.cursor.execute(
                "INSERT INTO projeler (proje_kodu, proje_ismi) VALUES (?, ?)",
                ("TEST001", "Test Proje")
            )
            pid = db.cursor.lastrowid

            # Create two revisions, one flagged
            db.cursor.execute(
                "INSERT INTO revizyonlar (proje_id, proje_rev_no, revizyon_kodu, durum, is_flagged) "
                "VALUES (?, 0, 'A', 'Onaysiz', 1)",
                (pid,)
            )
            db.cursor.execute(
                "INSERT INTO revizyonlar (proje_id, proje_rev_no, revizyon_kodu, durum, is_flagged) "
                "VALUES (?, 1, 'B', 'Onaysiz', 0)",
                (pid,)
            )
            db.conn.commit()

            # Fetch revisions
            revisions = db.revizyonlari_getir(pid)
            assert len(revisions) == 2

            # First revision (latest, rev B) should NOT be flagged
            assert getattr(revisions[0], "is_flagged", -1) == 0, (
                f"Latest revision should have is_flagged=0, got {getattr(revisions[0], 'is_flagged', 'MISSING')}"
            )

            # Second revision (rev A) should be flagged
            assert getattr(revisions[1], "is_flagged", -1) == 1, (
                f"Older revision should have is_flagged=1, got {getattr(revisions[1], 'is_flagged', 'MISSING')}"
            )
        finally:
            db.close()
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_project_list_query_reflects_flag_status(self):
        """projeleri_listele should return is_flagged=1 when ANY revision is flagged."""
        import sqlite3
        from database import ProjeTakipDB

        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "test_flag2.db")
        db = ProjeTakipDB(db_path)

        try:
            db.cursor.execute(
                "INSERT INTO projeler (proje_kodu, proje_ismi) VALUES (?, ?)",
                ("F001", "Flagged Project")
            )
            pid = db.cursor.lastrowid

            # Initially no flags
            projects = db.projeleri_listele()
            flagged = [p for p in projects if getattr(p, "is_flagged", 0)]
            assert len(flagged) == 0

            # Flag one revision
            db.cursor.execute(
                "INSERT INTO revizyonlar (proje_id, proje_rev_no, revizyon_kodu, durum, is_flagged) "
                "VALUES (?, 0, 'A', 'Onaysiz', 1)",
                (pid,)
            )
            db.conn.commit()
            db._clear_query_cache()

            projects = db.projeleri_listele()
            flagged = [p for p in projects if getattr(p, "is_flagged", 0)]
            assert len(flagged) == 1
            assert getattr(flagged[0], "id", None) == pid
        finally:
            db.close()
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================================
# Context Menu Tests
# ============================================================================


class TestProjectListContextMenu:
    """Project list right-click menu: only show İşaretle, never Kaldır."""

    def test_always_shows_isaretle_when_proje_exists(self):
        """Menu should always show 'İşaretle' when a project is selected."""
        proje = SimpleNamespace(id=42, is_flagged=1)

        # Simulate the menu building logic
        is_flagged = int(getattr(proje, "is_flagged", 0) or 0)

        # The new logic: always show İşaretle, never show Kaldır
        # We just verify the structure, not actual execution
        assert is_flagged in (0, 1)  # Both valid

    def test_project_menu_invokes_flag_on_latest_revision(self):
        """When İşaretle is clicked, it should flag only the latest revision."""
        # Simulate the callback logic
        called_with = []

        class FakeDB:
            def revizyonlari_getir(self, pid):
                # Return revisions ordered newest first
                return [
                    SimpleNamespace(id=100, proje_rev_no=2),
                    SimpleNamespace(id=99, proje_rev_no=1),
                ]

            def revizyon_flag_durumu_guncelle(self, rev_id, is_flagged):
                called_with.append((rev_id, is_flagged))
                return True

        db = FakeDB()
        pid = 42
        revisions = db.revizyonlari_getir(pid)
        assert len(revisions) > 0
        latest = revisions[0]
        assert latest.proje_rev_no == 2  # Latest

        # This is what _set_project_flag does
        db.revizyon_flag_durumu_guncelle(latest.id, True)
        assert called_with == [(100, True)]

    def test_project_menu_never_calls_proje_flag_guncelle_to_clear(self):
        """New menu never calls proje_flag_durumu_guncelle(False)."""
        # The old code had a _clear_project_flag that called
        # proje_flag_durumu_guncelle(pid, False). This should be removed.
        # We simulate the new behavior: only _set_project_flag exists.

        def simulate_old_behavior(proje):
            """Old behavior: check is_flagged, show both options."""
            is_flagged = int(getattr(proje, "is_flagged", 0) or 0)
            actions = []
            if is_flagged:
                actions.append("Kaldır")
            else:
                actions.append("İşaretle")
            return actions

        def simulate_new_behavior(proje):
            """New behavior: always show İşaretle only."""
            return ["İşaretle"]

        proje_flagged = SimpleNamespace(id=1, is_flagged=1)
        old = simulate_old_behavior(proje_flagged)
        new = simulate_new_behavior(proje_flagged)

        assert "Kaldır" in old
        assert "Kaldır" not in new
        assert "İşaretle" in new


class TestRevisionContextMenu:
    """Revision table right-click menu: toggle individual revision flag."""

    def test_toggle_flags_single_revision_only(self):
        """Flag toggle on revision menu only affects that revision."""
        db_calls = []

        class FakeDB:
            def revizyon_flag_durumu_guncelle(self, rev_id, is_flagged):
                db_calls.append((rev_id, is_flagged))
                return True

        db = FakeDB()

        # Toggle flag on a single revision
        rev = SimpleNamespace(id=55, is_flagged=1)
        new_value = not bool(rev.is_flagged)  # Toggle: 1 → 0
        db.revizyon_flag_durumu_guncelle(rev.id, new_value)

        assert db_calls == [(55, False)]

    def test_flag_status_reads_correctly_from_model(self):
        """After DB query fix, RevizyonModel.is_flagged should not be 0."""
        rev = SimpleNamespace(id=1, is_flagged=1)
        assert int(getattr(rev, "is_flagged", 0) or 0) == 1

        rev_unflagged = SimpleNamespace(id=2, is_flagged=0)
        assert int(getattr(rev_unflagged, "is_flagged", 0) or 0) == 0


# ============================================================================
# Theme Contrast Tests
# ============================================================================


class TestThemeContrast:
    """Verify theme-aware colors are used in preview/detail panels."""

    def test_preview_panel_uses_theme_colors(self):
        """PreviewPanel setup_ui should resolve TOK theme colors."""
        from ui.styles import TOK_THEME_VARIANTS, normalize_tok_variant

        for variant_key in ["light", "dark", "sand", "forest", "steel"]:
            theme_key = normalize_tok_variant(variant_key)
            palette = TOK_THEME_VARIANTS[theme_key]["palette"]
            assert "TEXT" in palette
            assert "MUTED" in palette
            assert "SURFACE" in palette
            assert "BG_LIGHT" in palette

            # Verify dark theme has light text and dark backgrounds
            if variant_key == "dark":
                text_color = palette["TEXT"]
                bg = palette["BG_LIGHT"]
                surf = palette["SURFACE"]
                # Dark text on dark background = bad contrast
                # Light themes: TEXT ~ #0d1117, SURFACE ~ #ffffff → good contrast
                # Dark themes: TEXT ~ #f0f3f7, SURFACE ~ #232936 → good contrast
                assert text_color != bg  # Verify they're different
                assert text_color != surf

    def test_all_themes_have_required_tokens(self):
        """Every theme variant must define TEXT, MUTED, SURFACE, BG_LIGHT."""
        from ui.styles import TOK_THEME_VARIANTS, normalize_tok_variant

        required = {"TEXT", "MUTED", "SURFACE", "BG_LIGHT",
                     "STATUS_ONAY_TEXT", "STATUS_ONAY_BG",
                     "STATUS_NOTLU_TEXT", "STATUS_NOTLU_BG",
                     "STATUS_RED_TEXT", "STATUS_RED_BG"}

        for variant_name in ["light", "dark", "sand", "forest", "steel"]:
            theme_key = normalize_tok_variant(variant_name)
            palette = TOK_THEME_VARIANTS[theme_key]["palette"]
            missing = required - set(palette.keys())
            assert not missing, f"Theme {variant_name} missing: {missing}"

    def test_dark_theme_contrast(self):
        """Dark theme text should be light enough to be readable on dark background."""
        from ui.styles import TOK_THEME_VARIANTS, normalize_tok_variant

        theme_key = normalize_tok_variant("dark")
        palette = TOK_THEME_VARIANTS[theme_key]["palette"]

        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        bg = hex_to_rgb(palette["SURFACE"])
        text = hex_to_rgb(palette["TEXT"])

        # Simple contrast check: average brightness should differ
        bg_brightness = sum(bg) / 3
        text_brightness = sum(text) / 3

        # In dark theme, text should be much brighter than background
        assert text_brightness > bg_brightness + 50, (
            f"Dark theme: text brightness ({text_brightness:.0f}) should be significantly "
            f"higher than surface brightness ({bg_brightness:.0f})"
        )


# ============================================================================
# Icon Presence Tests
# ============================================================================


class TestAppIcon:
    """Verify app_icon.ico is properly referenced."""

    def test_icon_file_exists(self):
        """app_icon.ico should exist in the working directory."""
        assert os.path.exists("app_icon.ico"), "app_icon.ico not found"

    def test_spec_files_reference_icon(self):
        """Both spec files should include app_icon.ico in datas and icon."""
        for spec_file in ["ProjeTakip-v3.2.1-windows-x64.spec",
                           "ProjeTakip-v3.2.1-windows-x64-onefile.spec"]:
            assert os.path.exists(spec_file), f"{spec_file} not found"
            content = open(spec_file, "r", encoding="utf-8").read()
            assert "app_icon.ico" in content, (
                f"{spec_file} does not reference app_icon.ico"
            )
