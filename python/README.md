# PROXORA Engine

The Python implementation of PROXORA, a next-value prediction engine.

## Models

- `-lr`: Classical linear regression (implemented by the Clojure backend; the
  `bin/proxora` dispatcher routes `-lr` there, not here).
- `-qu`: Variational quantum regression.

Both implementations target the same prediction task so that
predictive performance, reproducibility, and computational cost
can be compared.

## Command line

The Python backend implements `-qu`, `-op` and `-opqaoa`:

```bash
uv run proxora -qu
uv run proxora -op FILE.csv
uv run proxora -opqaoa FILE.csv
```

Missing or unknown flags print a usage message to stderr and exit with status
`2`, matching the `bin/proxora` dispatcher.

## Optimization: Max-Cut

```bash
uv run proxora -op     examples/ring4.csv       # classical brute force, up to 20 nodes
uv run proxora -opqaoa examples/weighted5.csv   # QAOA p=1, up to 12 qubits
```

Input CSV: one edge per row, `source,target[,weight]` (weight defaults to 1).
Node names are free text; they become qubits `q0, q1, ...` in order of first
appearance. A header row and `#` comments are allowed.

`-opqaoa` runs the hybrid loop:

1. Grid search plus Nelder-Mead finds `gamma`, `beta` on the exact NumPy
   model (`proxora/optimization/maxcut.py`).
2. The same circuit is built as a parametric Quil program
   (`proxora/optimization/qaoa.py`): `H` on every qubit, then per edge
   `CNOT · RZ(2 w gamma) · CNOT` (that is `exp(-i gamma w Z_i Z_j)`), then
   `RX(2 beta)` on every qubit, then measure. Angles are Quil classical
   memory, passed through `memory_map`, so the program compiles once.
3. 1000 shots on the QVM, scored with the same cut weight as `-op`.

Running on the Rigetti QVM:

```bash
uv sync --extra rigetti
docker run --rm -it -p 5555:5555 rigetti/quilc -S
docker run --rm -it -p 5000:5000 rigetti/qvm -S
uv run proxora -opqaoa examples/ring4.csv
```

If pyQuil or the servers are missing, `-opqaoa` still runs: it samples the
exact statevector (seeded) and prints `Backend: numpy-statevector` with the
reason. Read the backend line before quoting results.

Expected on `examples/ring4.csv`: classical max cut 4, ideal QAOA `<C>` = 3,
ratio 0.75 (the known p=1 value for ring graphs). Small graphs are trivial
classically; no quantum advantage is claimed.

## Tests

```bash
cd python
uv run python -m unittest discover -s tests
```

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
