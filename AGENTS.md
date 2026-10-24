# AGENTS.md

## Project purpose and architecture

PROXORA is a focused next-value predictor. It compares classical linear regression with a variational quantum regression implementation on the same prediction task. Preserve the project's core principles:

- Use comparable inputs, walk-forward evaluation, and the same scoring metrics when comparing methods.
- Prioritize mathematical clarity, reproducibility, and honest measurement.
- Do not claim quantum advantage without experimental evidence.
- Keep implementation details replaceable; do not tie the project identity to one model, optimizer, circuit, or backend.

Read the relevant README and specification before editing. Treat the current implementation as ground truth to inspect, and follow the specific task specification when one applies.

Main components:
- `bin/proxora`: Babashka command dispatcher; `-lr` invokes the Clojure backend, `-qu` invokes the Python/Qiskit backend, and `-op` / `-opqaoa FILE.csv` invoke the Python Max-Cut routes (classical brute force / QAOA in pyQuil).
- `clojure/`: classical linear-regression implementation.
- `python/`: Python engine, including forecast models, scoring, CLI, and the line-delimited JSON bridge.
- `mcp/`: Kotlin MCP server adapter. The prediction/scoring mathematics belongs in the Python engine, not duplicated in the adapter.
- `specs/`: task-level requirements. Read the relevant specification before implementing its task.
- `packaging/`: packaging and release-verification work.

## General working rules

1. Inspect the working tree, relevant code, tests, docs, and specifications before proposing or making changes.
2. Keep changes small, focused, and consistent with existing conventions. Avoid unrelated refactors and new dependencies unless justified.
3. Preserve user changes, including uncommitted or stashed work. Never discard or overwrite unrelated work.
4. For substantial work, briefly state the identified gap and implementation plan, then carry it through to verification.
5. If a requirement is ambiguous, inspect existing behavior and specifications; choose the smallest consistent interpretation and report unresolved ambiguity rather than silently inventing behavior.
6. Update documentation when behavior or developer commands change.
7. Do not commit changes unless explicitly requested.

## Python engine

The Python package lives under `python/`, with source under `python/src/proxora/`. It requires Python 3.12 or newer and uses `uv` for dependency and environment management.

- Work from `python/` for Python package commands.
- Use the existing `pyproject.toml` and lockfile. Do not introduce a second package manager or casually regenerate/change dependency versions.
- Keep Qiskit, Qiskit Aer, NumPy, and SciPy imports and runtime behavior compatible with the established environment.
- Preserve the lazy-import behavior where lightweight scoring or forecast imports should not need to load the full quantum stack unnecessarily.
- Keep CLI behavior predictable: invalid or missing flags should print usage to stderr and return a nonzero status as covered by tests.
- Keep the Python bridge protocol stable: one JSON request per input line and one JSON response per output line. Standard output is protocol data only; diagnostic/log output belongs on standard error.
- Bridge failures should be returned as structured error responses rather than unexpectedly crashing the process. Ensure serialized JSON is valid (no NaN or Infinity).

Useful Python commands:

```bash
cd python
uv sync
uv run python -m unittest discover -s tests
uv run proxora -qu
scripts/verify-env.sh
```

The environment verification script supports `--recreate`, but that option runs `uv venv --clear` and is destructive to the existing project virtual environment. Do not use it unless explicitly requested or the environment can safely be recreated.

## Critical Guix / native-library compatibility

Do not remove, bypass, or casually refactor the tracked `python/shim/sitecustomize.py` or its packaging mechanism in `python/pyproject.toml` (`[tool.uv.build-backend.data]` with `purelib = "shim"`). This shim is deliberately shipped in the built wheel so `uv sync` restores it when the virtual environment is recreated.

- Do not tell users to export `LD_LIBRARY_PATH=$GUIX_PROFILE/lib`; the Python README documents that this can cause Ubuntu tools to load incompatible Guix libraries.
- Do not hard-code transient `/gnu/store` paths.
- Do not replace the Guix-provided Python with a `uv`-downloaded CPython for the Qimono Guix fleet workflow.
- Do not manually copy the shim into `.venv/site-packages` as a permanent fix; it must remain part of the package installation flow.
- Before changing this area, read `python/README.md`, `python/scripts/verify-env.sh`, `python/pyproject.toml`, and the shim itself.

## Quantum and evaluation correctness

- Distinguish ideal statevector/simulator calculations from finite-shot measurements and from real hardware execution.
- Keep random seeds and other controls exposed where the existing API supports them; use deterministic settings in tests when appropriate.
- Add tests for mathematical edge cases and reproducibility when changing forecast or quantum behavior.
- When comparing classical and quantum methods, keep the evaluated series, walk-forward steps, confidence/range semantics, and score definitions comparable.
- Treat percentage-based scores as undefined when the observed value is zero, consistent with `scoring.py`.
- Do not interpret native-unit MSE aggregated across different assets as meaningful; the current batch scorer deliberately omits overall MSE for mixed assets.
- Avoid claims about predictive superiority or quantum advantage unless supported by appropriate baselines and reproducible evidence.

## Kotlin MCP adapter and engine protocol

The MCP server in `mcp/` is an adapter around the Python engine. It communicates over stdio with MCP clients and starts the engine through a line-delimited JSON process.

Useful commands:

```bash
cd mcp
./gradlew test
./gradlew shadowJar
```

- JDK 21 is the project's documented toolchain.
- Keep MCP protocol output on stdout free of logs or diagnostics.
- Preserve the shared engine boundary: implement forecasting/scoring behavior in Python and expose it through the bridge instead of duplicating mathematics in Kotlin.
- When adding or changing an MCP tool, inspect `mcp/README.md`, the tool schema/validation classes, `ProxoraServer.defaultTools()`, and the matching Python bridge function.
- MCP tests can start the real Python engine; check the environment configuration and prerequisites when investigating failures.

## Specifications, tests, and verification

For a task with a specification under `specs/`, read that file first and follow its requirements. In particular, the quantum terminal route specification calls out preserving the Clojure `-lr` route, the Python/Qiskit runtime fix, focused CLI tests, and honest reporting of unavailable checks.

Run the most relevant tests for changed components and report exactly what ran:

```bash
# Python
cd python
uv run python -m unittest discover -s tests

# MCP server and its engine integration tests
cd mcp
./gradlew test

# Environment imports (from python/)
scripts/verify-env.sh
```

Other useful checks, when relevant and available:

```bash
bb bin/proxora -lr
bb bin/proxora -qu
cd clojure && clojure -M:test
```

Do not claim a command passed unless it was actually executed successfully. If a runtime, dependency, hardware access, or other prerequisite is unavailable, run the strongest feasible focused checks and state what remains unverified.

## Final report

When finishing a task, summarize:
- What changed and why.
- Files changed.
- Exact verification commands and actual results.
- Any limitations, assumptions, or unresolved issues.
- Whether relevant behavior and environment safeguards remain intact.
