# Task: Implement PROXORA's `-qu` terminal route

You are working in the existing PROXORA repository. Implement the next increment of the terminal orchestrator so that `proxora -qu` dispatches to the Python/Qiskit quantum-regression implementation, following the project's specification.

## 1. Read the specification first

Read and treat this file as the primary source of truth:

`specs/quentum-linear-regression-from-terminal.md`

Inspect the current Git state and the relevant source files before making changes, especially:

- `bin/proxora`, the existing Babashka dispatcher.
- `python/pyproject.toml`, including the `proxora = "proxora:main"` entry point.
- The existing Python CLI and quantum-regression implementation.
- `python/README.md`, relevant tests, and any other files referenced by the specification.
- The existing Clojure implementation under `clojure/`.

Do not assume the specification's intended behavior is already implemented. Verify it against the actual code.

## 2. Objective

Make the terminal dispatcher select the correct implementation:

- `proxora -lr` → Clojure linear regression, executed through Babashka.
- `proxora -qu` → Python/Qiskit quantum regression, using the existing Python implementation and its intended runtime environment.

The CLI is the orchestrator. The regression implementations remain separate backends.

Follow the specification for the expected inputs, prediction behavior, output, quantum model, and execution requirements. Do not invent a different quantum algorithm or replace the specified design with a toy simulation.

## 3. Implementation constraints

- Preserve the existing working Clojure regression implementation and its tests.
- Preserve the NumPy/Guix runtime fix. Do not remove or bypass the tracked `sitecustomize.py` shim or its wheel-installation mechanism.
- Use the existing Python environment and project configuration. Do not replace Python, recreate the environment unnecessarily, or introduce another package manager.
- Do not hard-code transient `/gnu/store` paths or export a global `LD_LIBRARY_PATH` workaround.
- Avoid unnecessary dependencies and unrelated refactors.
- Preserve existing user changes, including uncommitted or stashed work. Do not discard, overwrite, or commit unrelated changes.
- Keep the command-line interface predictable. Unknown flags and missing arguments should produce a useful usage message and a nonzero exit status, consistent with the specification.
- Ensure subprocess failures propagate as failures. The dispatcher must not report success if the Python/Qiskit implementation fails.
- If the specification leaves a detail ambiguous, inspect existing conventions and choose the smallest consistent implementation. Document unresolved ambiguity instead of silently inventing requirements.

## 4. Work incrementally

1. Inspect the specification and current implementation.
2. Explain briefly what is missing and propose the smallest implementation plan.
3. Implement the Python CLI behavior required by the specification.
4. Connect `-qu` in `bin/proxora` to that implementation.
5. Add or update focused tests for CLI dispatch, argument handling, and the Python behavior required by the specification.
6. Update documentation only where needed to reflect the real behavior.

Do not stop after proposing a plan. Carry the implementation through to verification.

## 5. Verification requirements

Run the checks that are feasible in the current environment and report actual results:

- The existing Clojure regression tests:
  `cd clojure && clojure -M:test`
- The Babashka linear-regression route:
  `bb bin/proxora -lr`
- The quantum route through the dispatcher:
  `bb bin/proxora -qu`
- The Python tests relevant to the modified CLI and quantum implementation.
- The existing environment verification script, if practical:
  `cd python && scripts/verify-env.sh`

Check that `-lr` still produces the expected regression result and that `-qu` actually reaches the intended Qiskit implementation. Do not claim a quantum run passed if Qiskit, the runtime, or another prerequisite prevents it from running.

If the full quantum execution is too expensive or unavailable, run the strongest feasible focused tests and clearly identify what remains unverified.

## 6. Final report

When finished, provide a concise report containing:

- The behavior implemented.
- The files changed and why.
- The exact commands executed and their actual results.
- Any remaining limitations or specification ambiguities.
- Whether the working `-lr` route and the Python environment fix remain intact.

Do not commit changes unless explicitly asked. Leave the repository in a reviewable state so I can inspect the diff and test it locally.

**Definition of done:** The `-qu` flag is implemented according to `specs/quentum-linear-regression-from-terminal.md`, routes through the Babashka orchestrator to the existing Python/Qiskit backend, and is verified to the extent the environment allows, without breaking `-lr`.
