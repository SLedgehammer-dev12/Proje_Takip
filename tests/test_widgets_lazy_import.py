import pytest

import widgets


def test_get_fitz_module_is_cached():
    original = widgets._FITZ_MODULE
    calls = []

    try:
        widgets._FITZ_MODULE = None

        def fake_import(name):
            calls.append(name)
            return object()

        first = widgets._get_fitz_module(fake_import)
        second = widgets._get_fitz_module(fake_import)

        assert first is second
        assert calls == ["fitz"]
    finally:
        widgets._FITZ_MODULE = original


def test_get_fitz_module_raises_clear_error_when_backend_missing():
    original = widgets._FITZ_MODULE

    try:
        widgets._FITZ_MODULE = None

        def missing_import(name):
            raise ModuleNotFoundError(name)

        with pytest.raises(RuntimeError, match="PyMuPDF"):
            widgets._get_fitz_module(missing_import)
    finally:
        widgets._FITZ_MODULE = original
