#!/usr/bin/env bash
# Regression check for the PROXORA Guix + uv environment.
#
# The historical failure: NumPy (and SciPy/Qiskit/Aer) failed to import in the
# project venv with `libz.so.1: cannot open shared object file`, because the
# Guix CPython loader does not search /usr/lib. It was "fixed" by copying a
# sitecustomize.py into .venv/site-packages by hand, which silently disappeared
# whenever the venv was recreated.
#
# The shim now ships inside the project wheel (shim/ -> .data/purelib/), so a
# plain `uv sync` reinstalls it. This script imports the stack through the
# project's own interpreter to prove it.
#
# Usage:
#   scripts/verify-env.sh              # verify the current venv
#   scripts/verify-env.sh --recreate   # DESTRUCTIVE: `uv venv --clear` + sync first
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ "${1:-}" == "--recreate" ]]; then
  echo "==> recreating .venv from uv.lock (uv venv --clear && uv sync)"
  uv venv --clear && uv sync || exit 1
fi

uv run python - <<'PY'
import importlib
import os
import sys

# Direct dependencies of proxora-engine; all must import.
REQUIRED = ("numpy", "scipy", "qiskit", "qiskit_aer")
# Not a dependency; only reported when present.
OPTIONAL = ("matplotlib.pyplot",)

print(f"interpreter: {sys.executable}")
print(f"version:     {sys.version.split()[0]}")
print(f"guix shim:   {'re-exec active' if os.environ.get('QIMONO_STATIC_TLS') else 'not engaged (non-Guix or no profile)'}")

failed = False
for name in REQUIRED:
    try:
        module = importlib.import_module(name)
    except Exception as exc:  # noqa: BLE001 - report the real loader error
        failed = True
        print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
    else:
        print(f"ok    {name} {getattr(module, '__version__', '?')}")

for name in OPTIONAL:
    try:
        importlib.import_module(name)
    except ImportError:
        continue
    except Exception as exc:  # noqa: BLE001
        failed = True
        print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
    else:
        print(f"ok    {name} (optional)")

if failed:
    print("\nVERIFY FAILED: a dependency could not be imported.")
    sys.exit(1)
print("\nVERIFY OK")
PY
