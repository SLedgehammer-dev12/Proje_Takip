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

    def clear(self):
        self.calls.append(("clear", None))

    def show_status(self, text, **kwargs):
        self.calls.append(("show_status", text, kwargs))

    def show_loading(self, revision):
        self.calls.append(("show_loading", revision))


class _FakeRenderService:
    def __init__(self, revision_result):
        self.revision_result = revision_result
        self.revision_calls = []

    def prepare_revision_preview(self, revision):
        self.revision_calls.append(revision.id)
        return self.revision_result


class _FakeSignal:
    def __init__(self):
        self.emits = []

    def emit(self, *args):
        self.emits.append(args)


def test_revision_preview_missing_document_keeps_letter_preview_queue():
    revision = SimpleNamespace(id=42, revizyon_kodu="R1", dokuman_durumu="Yok")
    preview_state = _FakePreviewState()
    render_service = _FakeRenderService(
        PreviewLoadResult(status="no_document_flag", message="Doküman yok")
    )
    start_signal = _FakeSignal()

    queued_payloads = []
    window = SimpleNamespace(
        preview_state=preview_state,
        preview_render_service=render_service,
        _scheduled_letter_preview_payload=None,
        logger=SimpleNamespace(error=lambda *args, **kwargs: None),
        zoom_factor=1.0,
        _start_pdf_render=start_signal,
    )
    window._get_secili_revizyon_item = lambda: _FakeItem(revision)

    def queue_letter_preview(rev):
        payload = {"kind": "letter", "yazi_no": "12345", "lookup_yazi_turu": "gelen"}
        queued_payloads.append(rev.id)
        window._scheduled_letter_preview_payload = payload

    window._queue_letter_preview_for_revision = queue_letter_preview
    window._clear_preview = lambda: (_ for _ in ()).throw(
        AssertionError("_clear_preview should not run when only revision preview is missing")
    )
    window._clear_revision_preview_only = (
        lambda message=None, revision=None: AnaPencere._clear_revision_preview_only(
            window, message, revision=revision
        )
    )

    AnaPencere._trigger_preview_update(window)

    assert queued_payloads == [42]
    assert window._scheduled_letter_preview_payload["yazi_no"] == "12345"
    assert render_service.revision_calls == [42]
    assert start_signal.emits == []
    assert preview_state.calls[-1][0] == "show_status"
    assert preview_state.calls[-1][1] == "Doküman yok"
