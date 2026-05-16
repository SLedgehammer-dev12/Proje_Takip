"""Tests for document preview rendering pipeline.

Covers revision document preview, incoming/outgoing letter preview,
error handling, and slot behavior.
"""

from types import SimpleNamespace

from main_window import AnaPencere
from services.preview_render_service import PreviewLoadResult


class _FakeItem:
    def __init__(self, revision):
        self._revision = revision

    def data(self, column, role):
        return self._revision


class _FakePreviewState:
    def __init__(self):
        self.calls = []
        self.last_pixmap = None

    def clear(self):
        self.calls.append(("clear",))

    def show_status(self, text, **kwargs):
        self.calls.append(("show_status", text, kwargs))

    def show_loading(self, revision=None):
        self.calls.append(("show_loading", revision))

    def show_revision_preview(self, revision, pixmap):
        self.calls.append(("show_revision_preview", revision))
        self.last_pixmap = pixmap

    def show_render_error(self, error_msg):
        self.calls.append(("show_render_error", error_msg))


class _FakeRenderService:
    def __init__(self, revision_result=None, letter_result=None):
        self.revision_result = revision_result or PreviewLoadResult(status="ready", document_bytes=b"%PDF-test")
        self.letter_result = letter_result or PreviewLoadResult(status="ready", document_bytes=b"%PDF-letter")
        self.revision_calls = []
        self.letter_calls = []

    def prepare_revision_preview(self, revision):
        self.revision_calls.append(revision.id)
        return self.revision_result

    def prepare_letter_preview(self, payload):
        self.letter_calls.append(payload)
        return self.letter_result


class _FakeSignal:
    def __init__(self):
        self.emits = []

    def emit(self, *args):
        self.emits.append(args)


# ============================================================================
# Revision Document Preview Tests
# ============================================================================


class TestRevisionPreviewTrigger:
    """Tests for _trigger_preview_update flow."""

    def test_preview_starts_when_revision_has_document(self):
        revision = SimpleNamespace(
            id=1, revizyon_kodu="R1", dokuman_durumu="Var"
        )
        render_service = _FakeRenderService(
            PreviewLoadResult(status="ready", document_bytes=b"%PDF-test-data-ok")
        )
        start_signal = _FakeSignal()
        preview_state = _FakePreviewState()

        window = SimpleNamespace(
            preview_state=preview_state,
            preview_render_service=render_service,
            _start_pdf_render=start_signal,
            _scheduled_letter_preview_payload=None,
            logger=SimpleNamespace(
                debug=lambda *a, **kw: None,
                error=lambda *a, **kw: None,
            ),
            zoom_factor=1.5,
            isVisible=lambda: True,
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(revision)
        window._queue_letter_preview_for_revision = lambda rev: None

        AnaPencere._trigger_preview_update(window)

        assert render_service.revision_calls == [1]
        assert len(start_signal.emits) == 1
        assert start_signal.emits[0][0] == b"%PDF-test-data-ok"
        assert start_signal.emits[0][1] == 1.5
        assert start_signal.emits[0][2] == 1
        assert preview_state.calls[-1][0] == "show_loading"

    def test_preview_clears_when_revision_missing(self):
        window = SimpleNamespace(
            _get_secili_revizyon_item=lambda: None,
            logger=SimpleNamespace(error=lambda *a, **kw: None),
        )
        cleared = []

        def fake_clear():
            cleared.append(True)

        window._clear_preview = fake_clear
        AnaPencere._trigger_preview_update(window)
        assert cleared == [True]

    def test_preview_clears_when_document_not_ready(self):
        revision = SimpleNamespace(
            id=2, revizyon_kodu="R2", dokuman_durumu="Yok"
        )
        render_service = _FakeRenderService(
            PreviewLoadResult(status="no_document_flag", message="Doküman yok")
        )
        preview_state = _FakePreviewState()

        cleared_calls = []
        window = SimpleNamespace(
            preview_state=preview_state,
            preview_render_service=render_service,
            _start_pdf_render=_FakeSignal(),
            _scheduled_letter_preview_payload=None,
            logger=SimpleNamespace(
                debug=lambda *a, **kw: None,
                error=lambda *a, **kw: None,
            ),
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(revision)
        window._queue_letter_preview_for_revision = lambda rev: None

        def fake_clear_revision(message=None, revision=None):
            cleared_calls.append((message, revision))

        window._clear_revision_preview_only = fake_clear_revision

        AnaPencere._trigger_preview_update(window)
        assert len(cleared_calls) == 1
        assert cleared_calls[0][0] == "Doküman yok"

    def test_preview_clears_when_render_service_missing(self):
        revision = SimpleNamespace(
            id=3, revizyon_kodu="R3", dokuman_durumu="Var"
        )
        cleared = []
        window = SimpleNamespace(
            preview_render_service=None,
            logger=SimpleNamespace(error=lambda *a, **kw: None),
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(revision)
        window._clear_preview = lambda: cleared.append(True)
        AnaPencere._trigger_preview_update(window)
        assert cleared == [True]

    def test_preview_clears_when_document_bytes_are_none(self):
        revision = SimpleNamespace(
            id=4, revizyon_kodu="R4", dokuman_durumu="Var"
        )
        render_service = _FakeRenderService(
            PreviewLoadResult(status="ready", document_bytes=None)
        )
        cleared_calls = []
        window = SimpleNamespace(
            preview_render_service=render_service,
            _start_pdf_render=_FakeSignal(),
            _scheduled_letter_preview_payload=None,
            logger=SimpleNamespace(
                debug=lambda *a, **kw: None,
                error=lambda *a, **kw: None,
            ),
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(revision)
        window._queue_letter_preview_for_revision = lambda rev: None

        def fake_clear_revision(message=None, revision=None):
            cleared_calls.append((message, revision))

        window._clear_revision_preview_only = fake_clear_revision
        AnaPencere._trigger_preview_update(window)
        assert len(cleared_calls) == 1
        assert "boş" in cleared_calls[0][0].lower()


# ============================================================================
# Image Ready Slot Tests
# ============================================================================


class TestOnImageReady:
    """Tests for _on_image_ready slot."""

    def test_stale_signal_is_ignored(self):
        """When current revision ID differs from rendered ID, signal is ignored."""
        from PySide6.QtGui import QImage

        current_rev = SimpleNamespace(id=10)
        image = QImage(100, 50, QImage.Format_RGB32)
        preview_state = _FakePreviewState()

        window = SimpleNamespace(
            preview_state=preview_state,
            logger=SimpleNamespace(debug=lambda *a, **kw: None),
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(current_rev)

        # Signal is for rev_id=5, but current is rev_id=10 → should be ignored
        AnaPencere._on_image_ready(window, image, 5)
        assert preview_state.calls == []

    def test_matching_signal_shows_preview(self):
        """When revision IDs match, preview is displayed."""
        from PySide6.QtGui import QImage

        current_rev = SimpleNamespace(id=10, revizyon_kodu="R10")
        image = QImage(100, 50, QImage.Format_RGB32)
        preview_state = _FakePreviewState()

        window = SimpleNamespace(
            preview_state=preview_state,
            logger=SimpleNamespace(debug=lambda *a, **kw: None),
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(current_rev)

        AnaPencere._on_image_ready(window, image, 10)
        assert len(preview_state.calls) > 0
        assert preview_state.calls[-1][0] == "show_revision_preview"
        assert preview_state.last_pixmap is not None

    def test_no_item_ignores_signal(self):
        from PySide6.QtGui import QImage

        image = QImage(100, 50, QImage.Format_RGB32)
        preview_state = _FakePreviewState()

        window = SimpleNamespace(
            preview_state=preview_state,
            logger=SimpleNamespace(debug=lambda *a, **kw: None),
        )
        window._get_secili_revizyon_item = lambda: None

        AnaPencere._on_image_ready(window, image, 5)
        assert preview_state.calls == []

    def test_fallback_without_preview_state(self):
        from PySide6.QtGui import QImage

        current_rev = SimpleNamespace(id=10, revizyon_kodu="R10")
        image = QImage(100, 50, QImage.Format_RGB32)
        pixmap_set = []

        class FakeLabel:
            def setPixmap(self, p):
                pixmap_set.append(p)

        class FakeButton:
            def setEnabled(self, e):
                pass

        window = SimpleNamespace(
            preview_state=None,
            onizleme_etiketi=FakeLabel(),
            goruntule_btn=FakeButton(),
            logger=SimpleNamespace(debug=lambda *a, **kw: None),
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(current_rev)

        AnaPencere._on_image_ready(window, image, 10)
        assert len(pixmap_set) == 1


# ============================================================================
# Image Error Slot Tests
# ============================================================================


class TestOnImageError:
    """Tests for _on_image_error slot."""

    def test_revision_error_matching_id(self):
        preview_state = _FakePreviewState()
        current_rev = SimpleNamespace(id=10)

        window = SimpleNamespace(
            preview_state=preview_state,
            logger=SimpleNamespace(
                debug=lambda *a, **kw: None,
                critical=lambda *a, **kw: None,
            ),
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(current_rev)

        AnaPencere._on_image_error(window, "PDF corrupted", 10)
        assert len(preview_state.calls) > 0
        assert preview_state.calls[-1][0] == "show_render_error"

    def test_letter_error_handled_on_lower_panel(self):
        """Letter render errors (rev_id=-1) are handled on letter preview panel."""
        current_rev = SimpleNamespace(id=10)
        messages = []

        class FakeBtn:
            def setEnabled(self, e):
                self.enabled = e

        yazi_btn = FakeBtn()

        window = SimpleNamespace(
            yazi_onizleme_etiketi=SimpleNamespace(),
            yazi_ac_btn=yazi_btn,
            preview_state=None,
            logger=SimpleNamespace(
                debug=lambda *a, **kw: None,
            ),
        )

        def fake_set_letter_preview_message(msg):
            messages.append(msg)

        def fake_update_btn(payload):
            pass

        window._get_secili_revizyon_item = lambda: _FakeItem(current_rev)
        window._set_letter_preview_message = fake_set_letter_preview_message
        window._update_letter_preview_load_button = fake_update_btn

        AnaPencere._on_image_error(window, "Letter render failed", -1)
        assert len(messages) == 1
        assert "önizlenemedi" in messages[0].lower()
        assert not yazi_btn.enabled

    def test_stale_revision_error_ignored(self):
        preview_state = _FakePreviewState()
        current_rev = SimpleNamespace(id=10)

        window = SimpleNamespace(
            preview_state=preview_state,
            logger=SimpleNamespace(
                debug=lambda *a, **kw: None,
                critical=lambda *a, **kw: None,
            ),
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(current_rev)

        # Error for rev_id=5, current is rev_id=10 → ignore
        AnaPencere._on_image_error(window, "Failed", 5)
        assert preview_state.calls == []


# ============================================================================
# Letter Preview Trigger Tests
# ============================================================================


class TestLetterPreviewTrigger:
    """Tests for _trigger_letter_preview_update flow."""

    def test_letter_preview_triggers_render(self):
        revision = SimpleNamespace(
            id=1, revizyon_kodu="R1", dokuman_durumu="Var"
        )
        letter_payload = {"kind": "letter", "yazi_no": "123", "yazi_turu": "gelen", "yazi_tarih": "2024-01-01"}
        render_service = _FakeRenderService(
            letter_result=PreviewLoadResult(status="ready", document_bytes=b"%PDF-letter-ok")
        )
        start_signal = _FakeSignal()

        window = SimpleNamespace(
            preview_render_service=render_service,
            _start_yazi_render=start_signal,
            _scheduled_letter_preview_payload=letter_payload,
            logger=SimpleNamespace(
                debug=lambda *a, **kw: None,
                error=lambda *a, **kw: None,
            ),
            zoom_factor=1.5,
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(revision)
        window.isVisible = lambda: True

        def fake_set_message(msg):
            pass

        window._set_letter_preview_message = fake_set_message

        AnaPencere._trigger_letter_preview_update(window)
        assert len(render_service.letter_calls) == 1
        assert len(start_signal.emits) == 1
        assert start_signal.emits[0][0] == b"%PDF-letter-ok"

    def test_letter_preview_clears_when_no_revision(self):
        window = SimpleNamespace(
            logger=SimpleNamespace(error=lambda *a, **kw: None),
        )
        window._get_secili_revizyon_item = lambda: None
        messages = []

        def fake_set_message(msg):
            messages.append(msg)

        window._set_letter_preview_message = fake_set_message

        AnaPencere._trigger_letter_preview_update(window)
        assert len(messages) == 1
        assert "görünür" in messages[0].lower()

    def test_letter_preview_handles_missing_payload(self):
        revision = SimpleNamespace(
            id=1, revizyon_kodu="R1", dokuman_durumu="Var"
        )
        window = SimpleNamespace(
            _scheduled_letter_preview_payload=None,
            preview_render_service=None,
            logger=SimpleNamespace(error=lambda *a, **kw: None),
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(revision)
        messages = []

        def fake_set_message(msg):
            messages.append(msg)

        window._set_letter_preview_message = fake_set_message

        AnaPencere._trigger_letter_preview_update(window)
        assert len(messages) == 1

    def test_letter_preview_handles_not_ready_status(self):
        revision = SimpleNamespace(
            id=1, revizyon_kodu="R1", dokuman_durumu="Var"
        )
        letter_payload = {"kind": "letter", "yazi_no": "123", "yazi_turu": "gelen", "yazi_tarih": "2024-01-01"}
        render_service = _FakeRenderService(
            letter_result=PreviewLoadResult(status="missing_letter_document", message="Yazı bulunamadı")
        )

        window = SimpleNamespace(
            preview_render_service=render_service,
            _scheduled_letter_preview_payload=letter_payload,
            logger=SimpleNamespace(error=lambda *a, **kw: None),
        )
        window._get_secili_revizyon_item = lambda: _FakeItem(revision)
        messages = []

        def fake_set_message(msg):
            messages.append(msg)

        window._set_letter_preview_message = fake_set_message

        AnaPencere._trigger_letter_preview_update(window)
        assert len(messages) == 1
        assert "bulunamadı" in messages[0].lower()


# ============================================================================
# Preview Render Service Tests
# ============================================================================


class TestPreviewRenderService:
    """Tests for PreviewRenderService."""

    def test_prepare_revision_preview_missing_revision(self):
        from services.preview_render_service import PreviewRenderService

        svc = PreviewRenderService(db=None)
        result = svc.prepare_revision_preview(None)
        assert result.status == "missing_revision"

    def test_prepare_revision_preview_no_document_flag(self):
        from services.preview_render_service import PreviewRenderService

        revision = SimpleNamespace(id=1, dokuman_durumu="Yok")
        svc = PreviewRenderService(db=None)
        result = svc.prepare_revision_preview(revision)
        assert result.status == "no_document_flag"

    def test_cache_reuse_avoids_db_call(self):
        from services.preview_render_service import PreviewRenderService

        class FakeDB:
            def __init__(self):
                self.calls = 0

            def dokumani_getir(self, rev_id):
                self.calls += 1
                return (1, b"%PDF-cached-doc")

        db = FakeDB()
        revision = SimpleNamespace(id=1, dokuman_durumu="Var")
        svc = PreviewRenderService(db=db, max_cache_size=5)

        first = svc.prepare_revision_preview(revision)
        assert first.status == "ready"
        assert db.calls == 1

        second = svc.prepare_revision_preview(revision)
        assert second.status == "ready"
        assert db.calls == 1  # Cache hit, no additional DB call

    def test_cache_invalidation(self):
        from services.preview_render_service import PreviewRenderService

        class FakeDB:
            def __init__(self):
                self.calls = 0

            def dokumani_getir(self, rev_id):
                self.calls += 1
                return (1, b"%PDF-doc")

        db = FakeDB()
        revision = SimpleNamespace(id=1, dokuman_durumu="Var")
        svc = PreviewRenderService(db=db)

        svc.prepare_revision_preview(revision)  # populate cache
        assert db.calls == 1
        svc.invalidate_revision(1)
        svc.prepare_revision_preview(revision)  # should reload
        assert db.calls == 2  # Cache miss after invalidation

    def test_validate_rejects_non_pdf(self):
        from services.preview_render_service import PreviewRenderService

        class FakeDB:
            def dokumani_getir(self, rev_id):
                return (1, b"NOTAPDF")

        db = FakeDB()
        revision = SimpleNamespace(id=1, dokuman_durumu="Var")
        svc = PreviewRenderService(db=db)
        result = svc.prepare_revision_preview(revision)
        assert result.status == "invalid_document"

    def test_validate_rejects_empty_bytes(self):
        from services.preview_render_service import PreviewRenderService

        class FakeDB:
            def dokumani_getir(self, rev_id):
                return (1, b"")

        db = FakeDB()
        revision = SimpleNamespace(id=1, dokuman_durumu="Var")
        svc = PreviewRenderService(db=db)
        result = svc.prepare_revision_preview(revision)
        assert result.status == "invalid_document"

    def test_letter_preview_missing_payload(self):
        from services.preview_render_service import PreviewRenderService

        svc = PreviewRenderService(db=None)
        result = svc.prepare_letter_preview(None)
        assert result.status == "missing_letter_payload"

    def test_letter_preview_wrong_kind(self):
        from services.preview_render_service import PreviewRenderService

        svc = PreviewRenderService(db=None)
        result = svc.prepare_letter_preview({"kind": "revision", "yazi_no": "1"})
        assert result.status == "missing_letter_payload"

    def test_letter_preview_missing_identity(self):
        from services.preview_render_service import PreviewRenderService

        svc = PreviewRenderService(db=None)
        result = svc.prepare_letter_preview({"kind": "letter", "yazi_no": "", "yazi_turu": ""})
        assert result.status == "missing_letter_identity"

    def test_performance_mode_reduces_cache(self):
        from services.preview_render_service import PreviewRenderService

        svc = PreviewRenderService(db=None)
        assert svc.max_cache_size == 5
        assert svc.max_letter_cache_size == 8

        svc.configure_performance_mode(True)
        assert svc.max_cache_size == 2
        assert svc.max_letter_cache_size == 2

        svc.configure_performance_mode(False)
        assert svc.max_cache_size == 5
        assert svc.max_letter_cache_size == 8

    def test_clear_cache(self):
        from services.preview_render_service import PreviewRenderService

        db_calls = []

        class FakeDB:
            def dokumani_getir(self, rev_id):
                db_calls.append(rev_id)
                return (1, b"%PDF-test")

        db = FakeDB()
        svc = PreviewRenderService(db=db)
        revision = SimpleNamespace(id=1, dokuman_durumu="Var")

        svc.prepare_revision_preview(revision)
        assert len(db_calls) == 1
        svc.clear_cache()
        svc.prepare_revision_preview(revision)
        assert len(db_calls) == 2  # Cache miss after clear
