from services.update_client import (
    extract_checksum_for_asset,
    find_asset_for_platform,
    find_checksum_asset,
    is_newer,
)


def test_is_newer_supports_mixed_length_versions():
    assert is_newer("v2.1.8.5", "v2.1.9") is True
    assert is_newer("v2.1.9", "v2.1.9.1") is True


def test_is_newer_normalizes_trailing_zero_variants():
    assert is_newer("v2.1.9", "v2.1.9.0") is False
    assert is_newer("v2.1.9.0", "v2.1.9") is False


def test_find_asset_for_platform_prefers_exe_before_zip():
    release = {
        "assets": [
            {"name": "ProjeTakip-v2.1.9-windows-x64.zip"},
            {"name": "ProjeTakip-v2.1.9-windows-x64.exe"},
        ]
    }

    asset = find_asset_for_platform(
        release,
        r"ProjeTakip-.*\.(exe|zip)$",
        preferred_extensions=["msi", "exe", "zip"],
    )

    assert asset["name"] == "ProjeTakip-v2.1.9-windows-x64.exe"


def test_find_checksum_asset_and_extract_checksum_support_multi_asset_release():
    release = {
        "assets": [
            {"name": "ProjeTakip-v2.1.9-windows-x64.exe"},
            {"name": "ProjeTakip-v2.1.9-windows-x64.zip"},
            {"name": "SHA256SUMS"},
        ]
    }

    asset = release["assets"][0]
    checksum_asset = find_checksum_asset(release, asset)

    assert checksum_asset["name"] == "SHA256SUMS"

    checksum_text = (
        "a" * 64
        + " *ProjeTakip-v2.1.9-windows-x64.exe\n"
        + "b" * 64
        + " *ProjeTakip-v2.1.9-windows-x64.zip\n"
    )
    assert (
        extract_checksum_for_asset(checksum_text, "ProjeTakip-v2.1.9-windows-x64.zip")
        == "b" * 64
    )
