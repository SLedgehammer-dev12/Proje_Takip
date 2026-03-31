"""
services/update_client.py

Simple GitHub Releases based update client.

This module is intentionally dependency-light (standard library only) so it can be used
inside the main application without forcing additional packages.

Usage (high level):
  from services.update_client import check_and_download_latest

  path = check_and_download_latest(
      owner="SLedgehammer-dev12",
      repo="Proje_Takip",
      current_version="1.3",
      match_asset_filter="ProjeTakip-.*\\.exe",
      dest_dir="/path/to/tmp",
  )

If `path` is returned (a file path) it's the downloaded asset and the caller should
verify code signature and invoke the updater helper to replace the running exe.
"""

from __future__ import annotations

import json
import os
import re
import hashlib
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional


def _get_github_headers() -> Dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "ProjeTakip-Updater/1.0"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def check_latest_release(owner: str, repo: str) -> Optional[Dict]:
    """Return the latest release JSON (or None on failure).

    Relies on the public GitHub releases API. For private repos or higher rate limits
    set GITHUB_TOKEN in env or pass a token to the download function.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    headers = _get_github_headers()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except Exception:
        return None


def get_latest_release_info(
    owner: str,
    repo: str,
    current_version: str,
    match_asset_filter: str,
    preferred_extensions: Optional[List[str]] = None,
) -> Dict:
    """Return a structured update status for the latest GitHub release."""
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    headers = _get_github_headers()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            release_json = json.load(r)
    except urllib.error.HTTPError as e:
        return {
            "status": "error",
            "error_type": "http",
            "error": f"HTTP {e.code}",
        }
    except urllib.error.URLError as e:
        return {
            "status": "error",
            "error_type": "network",
            "error": str(e.reason),
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "unknown",
            "error": str(e),
        }

    latest_tag = release_json.get("tag_name") or release_json.get("name") or ""
    latest_ver = latest_tag.lstrip("v")
    html_url = release_json.get("html_url") or f"https://github.com/{owner}/{repo}/releases/latest"
    release_info = {
        "release": release_json,
        "latest_tag": latest_tag,
        "latest_version": latest_ver,
        "release_url": html_url,
    }

    if not latest_tag:
        return {
            "status": "error",
            "error_type": "release",
            "error": "Latest release metadata is missing.",
            **release_info,
        }

    if not is_newer(current_version, latest_ver):
        return {"status": "up_to_date", **release_info}

    asset = find_asset_for_platform(
        release_json, match_asset_filter, preferred_extensions=preferred_extensions
    )
    if not asset:
        return {"status": "asset_missing", "asset": None, **release_info}
    checksum_asset = find_checksum_asset(release_json, asset)
    if not checksum_asset:
        return {
            "status": "asset_unverified",
            "asset": asset,
            "checksum_asset": None,
            **release_info,
        }

    return {
        "status": "update_available",
        "asset": asset,
        "checksum_asset": checksum_asset,
        **release_info,
    }


def _version_tuple(v: str) -> List[int]:
    m = re.findall(r"\d+", str(v))
    return [int(x) for x in m]


def is_newer(current: str, latest: str) -> bool:
    try:
        return _version_tuple(latest) > _version_tuple(current)
    except Exception:
        return False


def find_asset_for_platform(
    release_json: Dict,
    name_pattern: str,
    preferred_extensions: Optional[List[str]] = None,
) -> Optional[Dict]:
    """Search assets for the best filename matching `name_pattern`."""
    assets = release_json.get("assets", []) if release_json else []
    pat = re.compile(name_pattern, re.IGNORECASE)
    matches = [a for a in assets if pat.search(a.get("name", ""))]
    if not matches:
        return None

    preferred_extensions = [ext.lower().lstrip(".") for ext in (preferred_extensions or [])]

    def _sort_key(asset: Dict):
        name = asset.get("name", "")
        ext = os.path.splitext(name)[1].lower().lstrip(".")
        ext_priority = (
            preferred_extensions.index(ext)
            if ext in preferred_extensions
            else len(preferred_extensions)
        )
        return (ext_priority, name.lower())

    matches.sort(key=_sort_key)
    return matches[0]


def find_checksum_asset(release_json: Dict, asset: Dict) -> Optional[Dict]:
    """Return a checksum asset for the given release asset when available."""
    assets = release_json.get("assets", []) if release_json else []
    asset_name = asset.get("name", "")
    candidates = {
        f"{asset_name}.sha256",
        f"{asset_name}.sha256.txt",
        "checksums.txt",
        "checksum.txt",
        "sha256sums.txt",
        "sha256sum.txt",
        "SHA256SUMS",
    }
    candidates = {name.lower() for name in candidates}
    for checksum_asset in assets:
        if checksum_asset.get("name", "").lower() in candidates:
            return checksum_asset
    return None


def download_asset(asset: Dict, dest_dir: str) -> Optional[str]:
    """Download a release asset to dest_dir and return local file path.

    Uses the `browser_download_url` field which does not require special headers.
    """
    if not asset:
        return None
    
    url = asset.get("browser_download_url")
    if not url:
        return None
        
    import logging
    logger = logging.getLogger(__name__)
    name = asset.get("name", "update_download.tmp")
    
    os.makedirs(dest_dir, exist_ok=True)
    out_path = os.path.join(dest_dir, name)
    
    try:
        req = urllib.request.Request(url, headers=_get_github_headers())
        with urllib.request.urlopen(req, timeout=120) as r, open(out_path, "wb") as f:
            while True:
                chunk = r.read(8192 * 4)  # 32KB chunks
                if not chunk:
                    break
                f.write(chunk)
        return out_path
    except Exception as e:
        logger.error(f"Asset downloading failed for {url}: {e}", exc_info=True)
        return None


def download_asset_text(asset: Dict) -> Optional[str]:
    """Download a text asset and return it as UTF-8 text."""
    if not asset:
        return None
    url = asset.get("browser_download_url")
    if not url:
        return None
    headers = _get_github_headers()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8-sig", errors="replace")
    except Exception:
        return None


def _sha256_file(path: str) -> Optional[str]:
    try:
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                sha.update(chunk)
        return sha.hexdigest()
    except Exception:
        return None


def extract_checksum_for_asset(checksum_text: str, asset_name: str) -> Optional[str]:
    """Extract the expected SHA-256 checksum for a named asset."""
    if not checksum_text:
        return None
    normalized_text = checksum_text.replace("\ufeff", "")

    for raw_line in normalized_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(
            r"^([A-Fa-f0-9]{64})\s+[* ]?(.+)$",
            line,
        )
        if match:
            checksum, candidate = match.groups()
            if candidate.strip() == asset_name:
                return checksum.lower()
        if line.lower() == asset_name.lower():
            continue
            
    # Support simple "filename: checksum" format.
    for raw_line in normalized_text.splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        candidate, checksum = [part.strip() for part in line.split(":", 1)]
        if candidate == asset_name and re.fullmatch(r"[A-Fa-f0-9]{64}", checksum):
            return checksum.lower()

    # Support PowerShell Get-FileHash output, including wrapped paths.
    hash_match = re.search(r"(?im)^\s*Hash\s*:\s*([A-Fa-f0-9]{64})\s*$", normalized_text)
    if hash_match:
        collected_path_parts: List[str] = []
        collecting_path = False
        for raw_line in normalized_text.splitlines():
            path_match = re.match(r"^\s*Path\s*:\s*(.*)$", raw_line)
            if path_match:
                collecting_path = True
                collected_path_parts = [path_match.group(1).strip()]
                continue
            if collecting_path:
                if not raw_line.strip():
                    break
                if re.match(r"^\s*[A-Za-z]+\s*:", raw_line):
                    break
                collected_path_parts.append(raw_line.strip())

        candidate_path = "".join(collected_path_parts).strip()
        candidate_name = os.path.basename(candidate_path.replace("/", "\\"))
        if candidate_name.lower() == asset_name.lower():
            return hash_match.group(1).lower()

    # Fallback for wrapped output by stripping all whitespace.
    clean_text = re.sub(r"\s+", "", normalized_text)
    clean_asset = re.sub(r"\s+", "", asset_name)

    if clean_asset.lower() in clean_text.lower():
        hex_matches = re.findall(r"(?i)[a-f0-9]{64}", clean_text)
        if hex_matches:
            return hex_matches[0].lower()

    return None


def verify_downloaded_asset(
    release_json: Dict,
    asset: Dict,
    downloaded_path: str,
) -> Dict:
    """Verify the downloaded asset against a published checksum."""
    checksum_asset = find_checksum_asset(release_json, asset)
    if not checksum_asset:
        return {"status": "unavailable", "error": "Checksum dosyası bulunamadı."}
    checksum_text = download_asset_text(checksum_asset)
    if not checksum_text:
        return {
            "status": "error",
            "error": f"Checksum dosyası indirilemedi: {checksum_asset.get('name', '-')}",
        }
    expected = extract_checksum_for_asset(checksum_text, asset.get("name", ""))
    if not expected:
        return {
            "status": "error",
            "error": f"Checksum içinde asset girdisi bulunamadı: {asset.get('name', '-')}",
        }
    actual = _sha256_file(downloaded_path)
    if not actual:
        return {"status": "error", "error": "İndirilen dosyanın SHA-256 özeti hesaplanamadı."}
    if actual != expected:
        return {
            "status": "error",
            "error": "İndirilen dosyanın checksum doğrulaması başarısız oldu.",
        }
    return {"status": "verified", "checksum_asset": checksum_asset.get("name", "")}


def download_repo_zip(owner: str, repo: str, branch: str = "main", dest_dir: Optional[str] = None) -> Optional[str]:
    """Download the repository ZIP for the given branch. Returns local path or None on failure."""
    dest_dir = dest_dir or tempfile.mkdtemp(prefix="projetakip-zip-")
    dest = os.path.join(dest_dir, f"{repo}-{branch}.zip")
    url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
    headers = _get_github_headers()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        return dest
    except Exception:
        try:
            if os.path.exists(dest):
                os.remove(dest)
        except Exception:
            pass
        return None


def check_and_download_latest(owner: str, repo: str, current_version: str, match_asset_filter: str, dest_dir: Optional[str] = None, fallback_branch: Optional[str] = None) -> Optional[str]:
    """Check GitHub releases and download the first matching asset if a newer version exists.

    - owner/repo: GitHub repo
    - current_version: current local version string (e.g. "1.3")
    - match_asset_filter: a regex to match asset name for the target platform (eg: r"ProjeTakip-.*\\.exe")
    - dest_dir: where to put the downloaded file (defaults to a temporary dir)
    - fallback_branch: if provided, download <branch> zip when no newer release/asset is found

    Returns path to the downloaded file or None when no newer release was found or an error occurred.
    """
    r = check_latest_release(owner, repo)
    if not r:
        # optionally fallback to branch zip
        if fallback_branch:
            return download_repo_zip(owner, repo, branch=fallback_branch, dest_dir=dest_dir)
        return None
    latest_tag = r.get("tag_name") or r.get("name") or ""
    # strip leading v if present
    latest_ver = latest_tag.lstrip("v")
    if not is_newer(current_version, latest_ver):
        if fallback_branch:
            return download_repo_zip(owner, repo, branch=fallback_branch, dest_dir=dest_dir)
        return None
    asset = find_asset_for_platform(r, match_asset_filter)
    if not asset:
        if fallback_branch:
            return download_repo_zip(owner, repo, branch=fallback_branch, dest_dir=dest_dir)
        return None
    dest_dir = dest_dir or tempfile.mkdtemp(prefix="projetakip-upd-")
    return download_asset(asset, dest_dir)


if __name__ == "__main__":
    # quick local demo / smoke test
    import argparse

    parser = argparse.ArgumentParser(description="Check GitHub Releases and optionally download a matching asset")
    parser.add_argument("owner")
    parser.add_argument("repo")
    parser.add_argument("current_version")
    parser.add_argument("asset_regex")
    parser.add_argument("--dest", default=None)
    args = parser.parse_args()

    result = check_and_download_latest(args.owner, args.repo, args.current_version, args.asset_regex, args.dest)
    if result:
        print("Downloaded:", result)
    else:
        print("No newer release found or download failed.")
