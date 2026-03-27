from __future__ import annotations

import argparse
from pathlib import Path
import zipfile


def create_zip(source_dir: Path, destination_zip: Path) -> None:
    source_dir = source_dir.resolve()
    destination_zip = destination_zip.resolve()
    destination_zip.parent.mkdir(parents=True, exist_ok=True)

    if not source_dir.is_dir():
        raise SystemExit(f"Source directory not found: {source_dir}")

    if destination_zip.exists():
        destination_zip.unlink()

    with zipfile.ZipFile(
        destination_zip,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir")
    parser.add_argument("destination_zip")
    args = parser.parse_args()

    create_zip(Path(args.source_dir), Path(args.destination_zip))


if __name__ == "__main__":
    main()
