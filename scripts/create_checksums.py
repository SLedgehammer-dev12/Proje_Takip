#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create SHA256SUMS for release assets.")
    parser.add_argument("assets", nargs="+", help="Asset files to hash")
    parser.add_argument(
        "--output",
        default="SHA256SUMS",
        help="Output checksum file path",
    )
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for asset_name in args.assets:
        asset_path = Path(asset_name).resolve()
        if not asset_path.exists():
            raise FileNotFoundError(f"Asset not found: {asset_path}")
        checksum = sha256_file(asset_path)
        lines.append(f"{checksum} *{asset_path.name}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
