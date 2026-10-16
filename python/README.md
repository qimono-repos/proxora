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

### Why a shim exists (and why it is built in)

`numpy` / `scipy` / `qiskit-aer` are manylinux wheels that `dlopen` `libz`
and `libstdc++`. Guix CPython's loader searches the Guix store, not
`/usr/lib`, so `import numpy` fails with
`libz.so.1: cannot open shared object file` unless the interpreter preloads
those sonames at startup.

`shim/sitecustomize.py` does that. It ships **inside the project wheel**
(`[tool.uv.build-backend.data] purelib = "shim"` → the PEP 427 `purelib`
wheel-data scheme), so `uv sync` installs it into
`.venv/…/site-packages/sitecustomize.py` every time — including when the
venv is recreated. This replaces the old manual copy, which silently
vanished on `uv venv --clear` and caused the failure to recur.

The shim is a no-op on machines without `~/.guix-profile/lib`, so it is
safe in a published package. It also re-execs the process once with
`GLIBC_TUNABLES=glibc.rtld.optional_static_tls=65536`, because SciPy and
`qiskit-aer` `dlopen` `libgomp` and qiskit's Rust `_accelerate` would
otherwise exceed glibc's default static-TLS surplus
(`cannot allocate memory in static TLS block`). That happens automatically
per interpreter — do not export it yourself.

### Verifying the environment

```bash
cd python
scripts/verify-env.sh              # import numpy/scipy/qiskit/qiskit_aer
scripts/verify-env.sh --recreate   # also does `uv venv --clear && uv sync` first
```

Do **not** export `LD_LIBRARY_PATH=$GUIX_PROFILE/lib` in your shell —
Ubuntu tools then load Guix `libm` and die with `GLIBC_2.43 not found`.
For non-`uv`/non-project venvs the fleet helper installs the same shim:

```bash
~/source/repos/qimono-repos/dotfiles/scripts/install-guix-wheel-shim.sh .
```

## License

Licensed under the GNU Affero General Public License,
version 3 or (at your option) any later version.

See the repository's [LICENSE](../LICENSE).
