# GitHub Releases based updater (simple flow)

This document describes the small, example updater flow added to the repository.

Files added:
- `services/update_client.py` — dependency-light GitHub Releases checker + downloader.
- `scripts/windows_updater.py` — a small helper that can replace a running exe (retries while the file is locked) and launch the new exe.
- `examples/updater_demo.py` — example script showing how to use the client + helper together.

Basic flow (current repository flow):

1. Build your Windows package and attach it to a GitHub Release for tag `vX.Y.Z`.
2. App calls `services.update_client.check_and_download_latest(owner, repo, current_version, asset_regex)`
   where `asset_regex` matches the file name of the release asset for Windows (for example `ProjeTakip-.*\.(zip|exe|msi)`).
3. If a newer version is found, the app shows release notes and lets the user download the asset into `Downloads`.
4. Before offering the asset, the app expects a checksum asset such as `SHA256SUMS` or `<asset>.sha256`.

Security & practical notes
- Always publish signed binaries/installers when possible. The app should download only from a trusted source. Use `GITHUB_TOKEN`
  as an environment variable for higher API rate limits or private repos (the updater respects `GITHUB_TOKEN`).
- The current app verifies SHA-256 checksum data before download is offered to the user.
- This repository currently uses a manual install model after download. `scripts/windows_updater.py` remains available
  for a future automatic replacement flow if you later decide to move from "download only" to "download and install".

Limitations & next steps
- The current release process is documented in `docs/RELEASING.md`.
- For production you may still want:
  - A signed installer (MSI/EXE) instead of a ZIP package.
  - A signed update manifest in addition to SHA-256 checksums.
  - A more robust installer/updater helper with rollback support.
