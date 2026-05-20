"""
Shared test fixtures for Proje Takip test suite.
"""

import os
import tempfile
from typing import Generator

import pytest

try:
    from PySide6.QtWidgets import QApplication
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False


@pytest.fixture(scope="session")
def qapp() -> Generator:
    """Provide an offscreen QApplication for the test session.
    Returns None if PySide6 is not installed.
    """
    if not PYSIDE6_AVAILABLE:
        pytest.skip("PySide6 is not installed")
        yield None
        return

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def tmp_db_path() -> Generator[str, None, None]:
    """Provide a temporary SQLite database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture
def tmp_dir() -> Generator[str, None, None]:
    """Provide a temporary directory for test output files."""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    import shutil
    try:
        shutil.rmtree(dir_path, ignore_errors=True)
    except Exception:
        pass
