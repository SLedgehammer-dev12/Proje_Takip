#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-}"
REMOTE="${2:-origin}"
BRANCH="${3:-main}"
NOTES_FILE="${4:-}"
shift $(( $# > 4 ? 4 : $# ))
ASSETS=("$@")

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "$VERSION" ]]; then
  VERSION="$(python3 - <<'PY'
import pathlib
import re
content = pathlib.Path("config.py").read_text(encoding="utf-8")
match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
if not match:
    raise SystemExit("APP_VERSION bulunamadi")
print(match.group(1))
PY
)"
fi

if [[ -z "$NOTES_FILE" ]]; then
  candidate="$repo_root/docs/releases/$VERSION.md"
  if [[ -f "$candidate" ]]; then
    NOTES_FILE="$candidate"
  else
    NOTES_FILE="$repo_root/guncelleme_notlari.txt"
  fi
fi

git -C "$repo_root" push "$REMOTE" "$BRANCH"
if ! git -C "$repo_root" rev-parse "$VERSION" >/dev/null 2>&1; then
  git -C "$repo_root" tag -a "$VERSION" -m "Release $VERSION"
fi
git -C "$repo_root" push "$REMOTE" "$VERSION"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI bulunamadi. Release'i manuel olusturun."
  exit 1
fi

if gh release view "$VERSION" >/dev/null 2>&1; then
  if [[ ${#ASSETS[@]} -gt 0 ]]; then
    gh release upload "$VERSION" --clobber "${ASSETS[@]}"
  fi
  echo "Release zaten mevcut. Asset'ler guncellendi: $VERSION"
  exit 0
fi

cmd=(gh release create "$VERSION" --title "$VERSION" --notes-file "$NOTES_FILE")
for asset in "${ASSETS[@]}"; do
  [[ -f "$asset" ]] && cmd+=("$asset")
done

"${cmd[@]}"
echo "GitHub release hazir: $VERSION"
