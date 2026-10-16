"""Preload Guix native libs for manylinux wheels (NumPy / SciPy / Qiskit).

Guix CPython does not search /usr/lib. Wheels still dlopen ``libz`` /
``libstdc++`` by soname. Exporting ``LD_LIBRARY_PATH`` in the login shell
(or the Jupyter unit) makes Ubuntu ``ls``/``date`` load Guix ``libm`` and
die with GLIBC_2.43.

Two things run at interpreter start, in this order:

1. **Re-exec with a larger static-TLS surplus.** SciPy and Qiskit-Aer
   ``dlopen`` ``libgomp`` after start-up, and qiskit's Rust
   ``_accelerate`` needs initial-exec TLS. glibc's default surplus is too
   small once the sonames below are preloaded, which fails with
   ``cannot allocate memory in static TLS block``. ``GLIBC_TUNABLES`` is
   parsed by ld.so *before* ``site`` runs, so the only way to set it for
   this process is one early ``execve`` (guarded by a sentinel; skipped
   when the shell already exported it).

2. **Preload the Guix sonames** with ``RTLD_GLOBAL`` so wheels find them.

Install as ``sitecustomize.py`` in a Guix-CPython venv's site-packages
(see ``scripts/install-guix-wheel-shim.sh``) so only that interpreter
touches the Guix libs; subprocesses (``!ls`` in a notebook) keep the
Ubuntu dynamic linker path.

Override the profile with ``QIMONO_GUIX_PROFILE``. On a machine with no
``~/.guix-profile/lib`` this module is a complete no-op, so it is safe to
ship in a package. Do not import this from an interactive host python.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

_GUIX_LIB = Path(
    os.environ.get("QIMONO_GUIX_PROFILE", str(Path.home() / ".guix-profile"))
) / "lib"
_SONAMES = (
    "libz.so.1",
    "libstdc++.so.6",
    "libgcc_s.so.1",
    "libgomp.so.1",
)
_TLS_TUNABLE = "glibc.rtld.optional_static_tls=65536"
_SENTINEL = "QIMONO_STATIC_TLS"


def _guix_active() -> bool:
    """True only where Guix actually provides the libraries we preload."""
    return _GUIX_LIB.is_dir()


def _raise_static_tls() -> None:
    """Re-exec once so glibc reserves enough static TLS for wheel extensions."""
    current = os.environ.get("GLIBC_TUNABLES", "")
    if _TLS_TUNABLE in current or os.environ.get(_SENTINEL) or not sys.executable:
        return
    argv = list(getattr(sys, "orig_argv", None) or ())
    if not argv:
        return
    env = dict(os.environ)
    env["GLIBC_TUNABLES"] = f"{current}:{_TLS_TUNABLE}" if current else _TLS_TUNABLE
    env[_SENTINEL] = "1"
    try:
        os.execve(sys.executable, [sys.executable, *argv[1:]], env)
    except OSError:
        pass  # cannot re-exec: keep going, preload below still applies


def _preload() -> None:
    if not _GUIX_LIB.is_dir():
        return
    for name in _SONAMES:
        path = _GUIX_LIB / name
        if not path.is_file():
            continue
        try:
            ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL)
        except OSError:
            pass


if _guix_active():
    _raise_static_tls()
    _preload()
