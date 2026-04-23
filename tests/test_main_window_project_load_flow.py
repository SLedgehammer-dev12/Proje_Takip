from types import SimpleNamespace

from main_window import AnaPencere


class _FakeThread:
    def __init__(self, running):
        self._running = running

    def isRunning(self):
        return self._running


def test_ensure_projects_loaded_logs_info_when_async_thread_is_still_running():
    infos = []
    warnings = []
    loaded = []
    window = SimpleNamespace(
        _project_load_token=3,
        tum_projeler=[],
        _project_load_threads={3: _FakeThread(True)},
        logger=SimpleNamespace(
            info=lambda message, *args: infos.append(message % args if args else message),
            warning=lambda message, *args: warnings.append(message % args if args else message),
            error=lambda *args, **kwargs: None,
        ),
        db=SimpleNamespace(projeleri_listele=lambda: [1, 2, 3]),
        _on_projects_loaded=lambda token, projects: loaded.append((token, projects)),
    )

    AnaPencere._ensure_projects_loaded(window, 3)

    assert infos == ["Projeler async yükleme süresi aştı; senkron fallback çalışıyor."]
    assert warnings == []
    assert loaded == [(3, [1, 2, 3])]


def test_ensure_projects_loaded_logs_warning_when_async_thread_is_not_running():
    infos = []
    warnings = []
    loaded = []
    window = SimpleNamespace(
        _project_load_token=5,
        tum_projeler=[],
        _project_load_threads={5: _FakeThread(False)},
        logger=SimpleNamespace(
            info=lambda message, *args: infos.append(message % args if args else message),
            warning=lambda message, *args: warnings.append(message % args if args else message),
            error=lambda *args, **kwargs: None,
        ),
        db=SimpleNamespace(projeleri_listele=lambda: ["ok"]),
        _on_projects_loaded=lambda token, projects: loaded.append((token, projects)),
    )

    AnaPencere._ensure_projects_loaded(window, 5)

    assert infos == []
    assert warnings == ["Projeler async yüklenemedi veya boş; senkron fallback çalışıyor."]
    assert loaded == [(5, ["ok"])]
