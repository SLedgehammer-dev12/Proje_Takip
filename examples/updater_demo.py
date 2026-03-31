"""
examples/updater_demo.py

Small demonstration script showing how to check for updates and prepare an update on Windows.

This is intentionally example-only: it prints what it would do, downloads the asset to a temp
location and prints commands the main app could use to invoke the helper.

DO NOT call the updater helper automatically on platforms that are not Windows; instead, present UI
to the user asking permission to download and update.
"""

from services.update_client import check_and_download_latest
import os
import sys


def demo():
    owner = "SLedgehammer-dev12"
    repo = "Proje_Takip"
    current_version = os.environ.get("APP_VERSION", "1.3")
    # We expect the release asset filename to contain 'ProjeTakip' and end with .exe
    match_asset = r"ProjeTakip-.*\\.exe"

    print("Checking GitHub Releases for updates...")
    path = check_and_download_latest(owner, repo, current_version, match_asset)
    if not path:
        print("No newer release found (or download failed)")
        return 0

    print(f"Downloaded candidate update to: {path}")
    print("Next steps on Windows (example):")
    print("  1) Ensure the running application quits")
    print("  2) Run the updater helper to replace the installed exe:")
    print(f"     python scripts/windows_updater.py --target \"C:\\Program Files\\ProjeTakip\\ProjeTakip.exe\" --src \"{path}\"")
    print("  3) The helper will replace the exe and launch the new version")
    return 0


if __name__ == "__main__":
    sys.exit(demo())
