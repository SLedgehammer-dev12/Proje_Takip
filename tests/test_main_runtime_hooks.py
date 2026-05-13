from types import SimpleNamespace

import main


def test_install_runtime_hooks_registers_all_supported_hooks(monkeypatch):
    installed = {}

    monkeypatch.setattr(main.sys, "excepthook", object())
    monkeypatch.setattr(main.threading, "excepthook", object(), raising=False)
    monkeypatch.setattr(main.sys, "unraisablehook", object(), raising=False)
    monkeypatch.setattr(
        main.QtCore,
        "qInstallMessageHandler",
        lambda handler: installed.setdefault("qt_handler", handler),
    )

    main.install_runtime_hooks()

    assert main.sys.excepthook is main.exception_hook
    assert main.threading.excepthook is main.thread_exception_hook
    assert main.sys.unraisablehook is main.unraisable_hook
    assert installed["qt_handler"] is main.qt_message_handler


def test_thread_exception_hook_ignores_system_exit():
    args = SimpleNamespace(
        exc_type=SystemExit,
        exc_value=SystemExit(),
        exc_traceback=None,
        thread=SimpleNamespace(name="worker"),
    )

    main.thread_exception_hook(args)
