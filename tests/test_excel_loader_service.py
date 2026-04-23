import sys
from pathlib import Path

from services.excel_loader_service import ExcelLoaderService


def test_excel_loader_caches_missing_file_warning_once(tmp_path):
    missing_path = tmp_path / "proje_listesi.xlsx"
    service = ExcelLoaderService(str(missing_path))
    warnings = []
    service.logger.warning = lambda message, *args: warnings.append(message % args if args else message)

    assert service.find_project("ABC-1") is None
    assert service.find_project("ABC-1") is None

    assert warnings == [f"Excel dosyası bulunamadı: {missing_path}"]
    assert service.get_load_error() == f"Excel dosyası bulunamadı: {missing_path}"

def test_excel_loader_falls_back_to_ancestor_excel_path(tmp_path, monkeypatch):
    root_excel = tmp_path / "proje_listesi.xlsx"
    backup_dir = tmp_path / "veritabani_yedekleri" / "yedek_Acilis_20260423"
    backup_dir.mkdir(parents=True)
    requested_path = backup_dir / "proje_listesi.xlsx"
    root_excel.write_text("placeholder", encoding="utf-8")

    class _FakeWorksheet:
        def iter_rows(self, min_row=2, values_only=True):
            yield ("", 1, "Mekanik", "1-MEK-2026", "Pompa Projesi")

    class _FakeWorkbook:
        def __init__(self):
            self.active = _FakeWorksheet()

        def close(self):
            return None

    loaded_paths = []

    class _FakeOpenPyxl:
        @staticmethod
        def load_workbook(path, read_only=True, data_only=True):
            loaded_paths.append(Path(path))
            return _FakeWorkbook()

    monkeypatch.setitem(sys.modules, "openpyxl", _FakeOpenPyxl)

    service = ExcelLoaderService(str(requested_path))

    assert service.find_project("1-MEK-2026") == ("Mekanik", "Pompa Projesi")
    assert Path(service.excel_path) == root_excel
    assert loaded_paths == [root_excel]
