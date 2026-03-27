"""
scripts/windows_updater.py

Small updater helper for Windows. Usage:

  python windows_updater.py --target "C:\\Program Files\\ProjeTakip\\ProjeTakip.exe" --src "C:\\Users\\you\\AppData\\Local\\Temp\\ProjeTakip-1.3.0.exe" --timeout 60

This script will try to replace `target` with `src` by repeatedly attempting an atomic replace while
the target is locked (another process is running). Once the replace succeeds, it will launch the
new target and exit.

Notes:
- This is intentionally simple and robust. In production you might implement the helper in a native
  language (C/C#/Go) to reduce chance of being flagged by AV, but Python is ok as an example.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time


def replace_with_retry(src: str, target: str, timeout: int = 60) -> bool:
    """Attempt to atomically replace target with src, retrying until timeout.

    Returns True on success.
    """
    start = time.time()
    # Make sure source exists
    if not os.path.exists(src):
        print(f"Source file not found: {src}")
        return False

    while time.time() - start < timeout:
        try:
            # Use replace if available for atomic behaviour
            if hasattr(os, "replace"):
                os.replace(src, target)
            else:
                # fallback: rename/move
                shutil.move(src, target)
            return True
        except PermissionError:
            # target probably locked by the running process
            time.sleep(1)
            continue
        except Exception as e:
            print("Replace failed:", e)
            return False

    print("Timed out waiting for target to be free")
    return False


def launch_target(target: str, args: list[str] | None = None) -> bool:
    try:
        cmd = [target]
        if args:
            cmd += args
        # On Windows, using CREATE_NEW_CONSOLE or DETACHED_PROCESS is possible.
        subprocess.Popen(cmd, close_fds=True)
        return True
    except Exception as e:
        print("Failed to launch target:", e)
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="Windows updater helper: install new exe and restart")
    parser.add_argument("--target", required=True, help="Path to current exe (target to replace)")
    parser.add_argument("--src", required=True, help="Path to downloaded new exe")
    parser.add_argument("--timeout", type=int, default=60, help="Seconds to wait for target to become writable")
    parser.add_argument("--args", nargs=argparse.REMAINDER, help="Arguments to pass when launching the new exe")

    args = parser.parse_args(argv)

    target = args.target
    src = args.src
    timeout = args.timeout
    launch_args = args.args or None

    # Replace the file (will fail if target is running and locked). Caller should exit main app first.
    ok = replace_with_retry(src, target, timeout=timeout)
    if not ok:
        print("Update failed: could not replace target")
        return 1

    # launch the new version
    if launch_target(target, launch_args):
        print("Update completed, launched new version")
        return 0
    else:
        print("Update completed but failed to launch new version")
        return 2


if __name__ == "__main__":
    sys.exit(main())
