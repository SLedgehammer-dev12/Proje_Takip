import argparse
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OWNER = "SLedgehammer-dev12"
DEFAULT_REPO = "Proje_Takip"


def load_github_token() -> Optional[str]:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
            check=True,
        )
    except Exception:
        return None

    values: Dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values.get("password")


def github_headers(token: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ProjeTakip-ReleasePublisher",
    }
    if extra:
        headers.update(extra)
    return headers


def github_request_json(url: str, token: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
    payload = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers=github_headers(token),
        method=method,
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    return json.loads(body.decode("utf-8")) if body else {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a GitHub release and upload canonical assets.")
    parser.add_argument("--version", default="", help="Release version/tag, e.g. v2.1.1")
    parser.add_argument("--owner", default=DEFAULT_OWNER, help="GitHub owner/org")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository name")
    parser.add_argument("--branch", default="main", help="Target commitish when creating/updating the release")
    parser.add_argument("--release-dir", default="", help="Directory containing release assets")
    parser.add_argument("--notes-file", default="", help="Release notes markdown path")
    parser.add_argument("--asset", action="append", default=[], help="Asset path to upload; may be passed multiple times")
    return parser.parse_args()


def version_from_config() -> str:
    config_text = (REPO_ROOT / "config.py").read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', config_text)
    if not match:
        raise SystemExit("APP_VERSION config.py içinden okunamadı.")
    return match.group(1)


def release_notes_path(version: str, explicit_path: str) -> Path:
    if explicit_path:
        return Path(explicit_path).resolve()
    candidate = REPO_ROOT / "docs" / "releases" / f"{version}.md"
    if candidate.exists():
        return candidate
    fallback = REPO_ROOT / "guncelleme_notlari.txt"
    if fallback.exists():
        return fallback
    raise SystemExit(f"Release notes bulunamadı: {candidate}")


def release_dir_path(version: str, explicit_path: str) -> Path:
    if explicit_path:
        return Path(explicit_path).resolve()
    return (REPO_ROOT / "release" / version).resolve()


def detect_assets(release_dir: Path, explicit_assets: Iterable[str]) -> List[Path]:
    if explicit_assets:
        assets = [Path(asset).resolve() for asset in explicit_assets]
    else:
        assets = []
        for suffix in (".exe", ".zip", ".msi"):
            assets.extend(sorted(release_dir.glob(f"*{suffix}")))

    assets = [asset for asset in assets if asset.exists()]
    if not assets:
        raise SystemExit(f"Yüklenecek asset bulunamadı: {release_dir}")
    return assets


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksum_file(asset_paths: List[Path], checksum_path: Path) -> Path:
    checksum_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{sha256_file(asset)} *{asset.name}" for asset in asset_paths]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path


def get_release_by_tag(owner: str, repo: str, version: str, token: str) -> Optional[Dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{version}"
    request = urllib.request.Request(url, headers=github_headers(token), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def upsert_release(owner: str, repo: str, version: str, branch: str, notes_file: Path, token: str) -> Dict:
    body = notes_file.read_text(encoding="utf-8")
    release_name = f"Proje Takip Sistemi {version}"
    payload = {
        "tag_name": version,
        "target_commitish": branch,
        "name": release_name,
        "body": body,
        "draft": False,
        "prerelease": False,
    }

    current = get_release_by_tag(owner, repo, version, token)
    if current:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/{current['id']}"
        return github_request_json(url, token, method="PATCH", data=payload)

    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    return github_request_json(url, token, method="POST", data=payload)


def delete_existing_asset(asset_id: int, owner: str, repo: str, token: str) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{asset_id}"
    request = urllib.request.Request(url, headers=github_headers(token), method="DELETE")
    with urllib.request.urlopen(request, timeout=60):
        return


def upload_asset(upload_url: str, asset_path: Path, token: str) -> None:
    mime_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
    encoded_name = urllib.parse.quote(asset_path.name)
    request = urllib.request.Request(
        f"{upload_url}?name={encoded_name}",
        data=asset_path.read_bytes(),
        headers=github_headers(
            token,
            {
                "Accept": "application/vnd.github+json",
                "Content-Type": mime_type,
            },
        ),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300):
        return


def replace_release_assets(release: Dict, asset_paths: List[Path], owner: str, repo: str, token: str) -> None:
    existing_by_name = {asset.get("name"): asset for asset in release.get("assets", [])}
    upload_url = release["upload_url"].split("{", 1)[0]

    for asset_path in asset_paths:
        existing = existing_by_name.get(asset_path.name)
        if existing:
            delete_existing_asset(existing["id"], owner, repo, token)
        upload_asset(upload_url, asset_path, token)


def main() -> int:
    args = parse_args()
    version = args.version or version_from_config()
    token = load_github_token()
    if not token:
        raise SystemExit("GitHub token bulunamadı. GITHUB_TOKEN ayarlayın veya github.com credential helper yapılandırın.")

    release_dir = release_dir_path(version, args.release_dir)
    notes_file = release_notes_path(version, args.notes_file)
    asset_paths = detect_assets(release_dir, args.asset)
    checksum_path = write_checksum_file(asset_paths, release_dir / "SHA256SUMS")

    release = upsert_release(args.owner, args.repo, version, args.branch, notes_file, token)
    replace_release_assets(release, [*asset_paths, checksum_path], args.owner, args.repo, token)

    html_url = release.get("html_url") or f"https://github.com/{args.owner}/{args.repo}/releases/tag/{version}"
    print(f"Release hazır: {html_url}")
    print("Yüklenen asset'ler:")
    for asset_path in [*asset_paths, checksum_path]:
        print(f" - {asset_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
