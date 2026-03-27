#!/usr/bin/env python3
import re
import subprocess
import sys

# Patterns that should not be allowed in commits
PATTERN = re.compile(
    r"\.(db|sqlite|sqlite3|bak)$|^veritabani_yedekleri/|test_output.txt$|_output\.txt$|test_.*\.txt$|^(htmlcov|coverage)/|^coverage\.xml$|^\.coverage$"
)


def get_staged_files():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
        )
        if result.returncode != 0:
            print("Git diff kaçıp hata verdi:", result.stderr)
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except FileNotFoundError:
        print("Git bulunamadı. Pre-commit script'i git komutunu kullanıyor.")
        return []


def main():
    files = get_staged_files()
    problematic = [f for f in files if PATTERN.search(f)]
    if problematic:
        print(
            "HATA: Aşağıdaki dosyalar commit edilmemeli/silinmeli veya .gitignore'a eklenmeli:"
        )
        for p in problematic:
            print(" - ", p)
        print(
            "Lütfen dosyaları git takibinden çıkarmak için scripts/remove_tracked_db.ps1 betiğini veya `git rm --cached <file>` komutunu kullanın."
        )
        sys.exit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
