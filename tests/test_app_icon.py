from pathlib import Path

from app_icon import iter_application_icon_sources


def test_application_icon_sources_include_repo_icon():
    sources = iter_application_icon_sources(icon_name="app_icon.ico", frozen=False)

    assert any(Path(source).name == "app_icon.ico" for source in sources)


def test_application_icon_sources_include_executable_when_frozen(tmp_path):
    fake_exe = tmp_path / "ProjeTakip.exe"
    fake_exe.write_bytes(b"not-a-real-exe")

    sources = iter_application_icon_sources(
        icon_name="missing.ico",
        executable_path=str(fake_exe),
        frozen=True,
    )

    assert str(fake_exe) in sources
