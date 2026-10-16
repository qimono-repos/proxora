# PROXORA Engine

The Python implementation of PROXORA, a next-value prediction engine.

## Models

- `-lr`: Classical linear regression.
- `-qu`: Variational quantum regression.

Both implementations target the same prediction task so that
predictive performance, reproducibility, and computational cost
can be compared.

## Setup (Qimono Guix fleet)

This engine targets a Guix-provided Python (**never** a `uv`-downloaded
CPython). On a Qimono machine:

```bash
cd python
uv sync            # uses the Guix python3 (3.12+) from the fleet profile
uv run proxora -qu
```

`numpy` / `scipy` / `qiskit-aer` are manylinux wheels that `dlopen` `libz`
and `libstdc++`. Guix CPython's loader searches the Guix store, not
`/usr/lib`, so `import numpy` fails with
`libz.so.1: cannot open shared object file` unless the venv preloads those
sonames. Install the fleet shim once per venv — and again after any
`uv sync` that recreates `.venv`:

```bash
~/source/repos/qimono-repos/dotfiles/scripts/install-guix-wheel-shim.sh .
```

The shim (`sitecustomize.py`) is scoped to the venv interpreter. Do **not**
export `LD_LIBRARY_PATH=$GUIX_PROFILE/lib` in your shell — Ubuntu tools then
load Guix `libm` and die with `GLIBC_2.43 not found`.

The shim also re-execs the process once with
`GLIBC_TUNABLES=glibc.rtld.optional_static_tls=65536`, because SciPy and
`qiskit-aer` `dlopen` `libgomp` and qiskit's Rust `_accelerate` then exceeds
glibc's default static-TLS surplus (`cannot allocate memory in static TLS
block`). That happens automatically per interpreter — do not export it.

## License

Licensed under the GNU Affero General Public License,
version 3 or (at your option) any later version.

See the repository's [LICENSE](../LICENSE).
