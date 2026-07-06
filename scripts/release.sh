#!/usr/bin/env bash
#
# Interactive release: tag -> push -> build -> publish to PyPI.
# Version comes from the git tag (hatch-vcs), so the tag is the single input.
#
# Usage:
#   ./scripts/release.sh 0.1.1
#   ./scripts/release.sh v0.1.1
#   ./scripts/release.sh            # prompts for the version
#
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# --- helpers ---------------------------------------------------------------
red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n'  "$*"; }
die()   { red "error: $*" >&2; exit 1; }
confirm() { read -r -p "$1 [y/N] " a; [[ "$a" =~ ^[Yy]$ ]]; }

# --- 1. resolve + validate the version ------------------------------------
VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  read -r -p "Version to release (e.g. 0.1.1): " VERSION
fi
VERSION="${VERSION#v}"                       # strip a leading v if given
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([abrc.].*)?$ ]] \
  || die "not a valid version: '$VERSION' (want X.Y.Z)"
TAG="v$VERSION"

# --- 2. preflight checks ---------------------------------------------------
git diff-index --quiet HEAD -- \
  || die "working tree is dirty — commit or stash first (hatch-vcs needs a clean tree)"

git rev-parse "$TAG" >/dev/null 2>&1 \
  && die "tag $TAG already exists"

# refuse to release a version already on PyPI
if uv run python - "$VERSION" <<'PY' 2>/dev/null
import sys, urllib.request, json
v = sys.argv[1]
d = json.load(urllib.request.urlopen("https://pypi.org/pypi/youtube-watch-mcp/json", timeout=10))
sys.exit(0 if v in d["releases"] else 1)
PY
then
  die "version $VERSION is already published on PyPI (versions are immutable)"
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
bold "About to release:"
echo "  tag     : $TAG"
echo "  branch  : $BRANCH -> origin"
echo "  package : youtube-watch-mcp $VERSION -> PyPI"
confirm "Proceed?" || { echo "aborted."; exit 0; }

# --- 3. tag + push ---------------------------------------------------------
green "-> tagging $TAG"
git tag -a "$TAG" -m "Release $TAG"

green "-> pushing branch + tags"
git push origin "$BRANCH"
git push origin "$TAG"

# --- 4. build (version stamped from the tag) -------------------------------
green "-> building"
rm -rf dist
uv build

BUILT="$(ls dist/*.whl | head -1)"
bold "built: $BUILT"
# guard: a '+local' segment means the tree wasn't clean -> PyPI would reject
[[ "$BUILT" == *"+"* ]] && die "built a local/dev version — tree not clean at the tag"

uvx twine check dist/*

# --- 5. publish ------------------------------------------------------------
confirm "Upload $VERSION to PyPI now?" || { echo "built but not uploaded."; exit 0; }
green "-> uploading"
uvx twine upload dist/*

green "done. released $TAG"
echo "verify: uvx --refresh youtube-watch-mcp-cli info 'https://youtu.be/jNQXAC9IVRw'"
