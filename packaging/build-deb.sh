#!/usr/bin/env bash
# Build a self-contained PROXORA .deb for Ubuntu 26.10 amd64.
#
# The package carries its own CPython, the pinned Python wheels (NumPy, SciPy,
# Qiskit, Qiskit Aer) and a static Babashka, so it does not depend on the
# target's Python version, Qiskit availability, or Babashka being installed.
#
# Usage:
#   packaging/build-deb.sh              # build dist/proxora_<version>_amd64.deb
#   VERSION=0.1.0 DEB_VERSION=0.1.0-1 packaging/build-deb.sh
#
# Network is required on the build host to fetch the pinned interpreter,
# wheels and Babashka. The resulting package needs no network.
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PACKAGING_DIR=$REPO_ROOT/packaging
WORK=${WORK:-$PACKAGING_DIR/.work}
DIST=${DIST:-$REPO_ROOT/dist}

PKG=proxora
ARCH=amd64
PREFIX=/usr/lib/proxora

PYTHON_VERSION=${PYTHON_VERSION:-3.12.13}
BABASHKA_VERSION=${BABASHKA_VERSION:-1.13.219}
BABASHKA_SHA256=${BABASHKA_SHA256:-9ac1fe988d7001625b30ef3e3307e67f8545505a7cb49a4aa179f578115a3e09}

VERSION=${VERSION:-$(sed -n 's/^version = "\(.*\)"/\1/p' "$REPO_ROOT/python/pyproject.toml" | head -1)}
DEB_VERSION=${DEB_VERSION:-${VERSION}-1}

log() { printf '==> %s\n' "$*"; }

[[ -n "$VERSION" ]] || { echo "could not determine version" >&2; exit 1; }

ROOT=$WORK/root
log "staging in $ROOT"
rm -rf "$WORK"
mkdir -p \
  "$ROOT/DEBIAN" \
  "$ROOT/usr/bin" \
  "$ROOT$PREFIX/bin" \
  "$ROOT$PREFIX/clojure" \
  "$ROOT/usr/share/doc/$PKG"

# --- portable CPython ------------------------------------------------------
PY_MANAGED_ROOT=${UV_PYTHON_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/uv/python}
PY_SRC=$PY_MANAGED_ROOT/cpython-$PYTHON_VERSION-linux-x86_64-gnu
if [[ ! -x "$PY_SRC/bin/python3" ]]; then
  log "installing managed CPython $PYTHON_VERSION"
  UV_PYTHON_DOWNLOADS=manual uv python install "$PYTHON_VERSION"
fi
[[ -x "$PY_SRC/bin/python3" ]] || {
  echo "managed CPython not found at $PY_SRC" >&2
  echo "set PYTHON_VERSION to an installed uv-managed 3.12 build" >&2
  exit 1
}
log "bundling CPython from $PY_SRC"
cp -a "$PY_SRC" "$ROOT$PREFIX/python"

# --- pinned Python dependencies -------------------------------------------
SITE=$ROOT$PREFIX/site-packages
log "installing locked Python dependencies"
uv export --project "$REPO_ROOT/python" --frozen --no-emit-project \
  --format requirements.txt > "$WORK/requirements.txt"
uv pip install \
  --python "$ROOT$PREFIX/python/bin/python3" \
  --target "$SITE" \
  --requirement "$WORK/requirements.txt" >/dev/null

# The engine itself is copied (not built) to avoid depending on the build
# backend version available on the host.
log "copying the proxora engine"
cp -a "$REPO_ROOT/python/src/proxora" "$SITE/proxora"
find "$SITE/proxora" -type d -name __pycache__ -prune -exec rm -rf {} +

# --- Babashka and the Clojure backend -------------------------------------
log "fetching Babashka $BABASHKA_VERSION"
BB_TARBALL=$WORK/babashka.tar.gz
curl -fsSL -o "$BB_TARBALL" \
  "https://github.com/babashka/babashka/releases/download/v$BABASHKA_VERSION/babashka-$BABASHKA_VERSION-linux-amd64-static.tar.gz"
echo "$BABASHKA_SHA256  $BB_TARBALL" | sha256sum -c - >/dev/null
tar xzf "$BB_TARBALL" -C "$ROOT$PREFIX/bin"
chmod 0755 "$ROOT$PREFIX/bin/bb"

log "copying the Clojure backend"
cp -a "$REPO_ROOT/clojure/src" "$ROOT$PREFIX/clojure/src"
find "$ROOT$PREFIX/clojure" -type d -name .cpcache -prune -exec rm -rf {} +

# --- launcher and documentation -------------------------------------------
log "installing launcher and documentation"
install -m 0755 "$PACKAGING_DIR/proxora" "$ROOT/usr/bin/proxora"
install -m 0644 "$PACKAGING_DIR/copyright" "$ROOT/usr/share/doc/$PKG/copyright"
install -m 0644 "$REPO_ROOT/README.md" "$ROOT/usr/share/doc/$PKG/README.md"

{
  printf '%s (%s) unstable; urgency=medium\n\n' "$PKG" "$DEB_VERSION"
  printf '  * Self-contained build for Ubuntu 26.10 amd64.\n\n'
  printf ' -- Qimono <%s>  %s\n' "albert@qimono.vip" "$(date -R)"
} | gzip -9n > "$ROOT/usr/share/doc/$PKG/changelog.Debian.gz"
chmod 0644 "$ROOT/usr/share/doc/$PKG/changelog.Debian.gz"

# Normalise modes: cp -a preserves the build host's group-writable bits, but
# files installed under /usr should be 0644 (0755 for executables/directories).
find "$ROOT" -type d -exec chmod 0755 {} +
find "$ROOT" -type f -perm -u+x -exec chmod 0755 {} +
find "$ROOT" -type f ! -perm -u+x -exec chmod 0644 {} +

# --- control ---------------------------------------------------------------
INSTALLED_SIZE=$(du -sk "$ROOT" | cut -f1)
cat > "$ROOT/DEBIAN/control" <<EOF
Package: $PKG
Version: $DEB_VERSION
Section: science
Priority: optional
Architecture: $ARCH
Maintainer: Qimono <albert@qimono.vip>
Installed-Size: $INSTALLED_SIZE
Depends: libc6 (>= 2.17), libgcc-s1, libstdc++6, zlib1g
Homepage: https://github.com/qimono-repos/proxora
Description: next-value predictor with classical and quantum backends
 PROXORA predicts the next value of a numerical sequence. The -lr route uses
 ordinary least squares; the -qu route runs a variational quantum regressor on
 Qiskit. The package is self-contained: it bundles its own CPython and the
 pinned NumPy, SciPy, Qiskit, Qiskit Aer and Babashka releases.
EOF
chmod 0644 "$ROOT/DEBIAN/control"

# --- build -----------------------------------------------------------------
mkdir -p "$DIST"
ARTIFACT=$DIST/${PKG}_${DEB_VERSION}_${ARCH}.deb
log "building $ARTIFACT"
dpkg-deb --root-owner-group -Zxz --build "$ROOT" "$ARTIFACT"

log "artifact"
ls -lh "$ARTIFACT"
sha256sum "$ARTIFACT"
