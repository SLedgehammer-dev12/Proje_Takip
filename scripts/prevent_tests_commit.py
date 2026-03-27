#!/usr/bin/env python3
import subprocess
import sys
import re

PATTERN = re.compile(r"(^tests/)|(/tests/)|(^(test_).*\.py$)")


def get_staged_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
        )
        if result.returncode != 0:
            print("Git diff failed:", result.stderr)
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except FileNotFoundError:
        print("Git not found. Pre-commit script requires git to run.")
        return []


def main():
    files = get_staged_files()
    problematic = [f for f in files if PATTERN.search(f)]
    if problematic:
        print(
            "ERROR: The following test files should not be committed to the remote repository:"
        )
        for p in problematic:
            print(" - ", p)
        print(
            "Keep test files in your local workspace. If you really need to commit them, remove or adjust this hook."
        )
        sys.exit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
