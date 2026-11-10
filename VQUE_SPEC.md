# VQUE_SPEC.md — Experimental VQE ground-energy endpoint (proposal)

Status: **DRAFT / DESIGN ONLY**, 2026-11-09. No endpoint or quantum algorithm has been implemented by this specification. Filename `VQUE_SPEC.md` preserves the requested name; the algorithm is conventionally abbreviated **VQE**.

## 1. Context, scope, and product boundary

PROXORA currently does **one job: next-value forecasting**, comparing classical linear regression (`-lr`) to variational quantum regression (`-qu`). Its Python engine, line-delimited JSON bridge, and Kotlin MCP adapter are production-facing boundaries. The existing variational *regressor* is **not** a Variational Quantum Eigensolver.

This document explores an **opt-in experimental research endpoint**, not a new implementation of `predict_next`, `backtest`, or the `-qu` CLI flag. The longer-term decision is whether to expose it as a clearly labeled research namespace inside PROXORA or move it into a separate Qimono ground-state application/service. Do **not** silently change PROXORA's stated single-purpose contract.

Related MIT xPRO pre-assessment Q8 (not yet submitted/verified at spec creation): VQE is a hybrid algorithm: state preparation and measurements occur on a quantum backend, while **parameter optimization is typically classical**. The correct intended single-choice option is **#3, parameter optimization**; record actual MIT feedback separately after submission.

## 2. Mathematical contract

Input: a finite-dimensional Hermitian Hamiltonian H (MVP as a real-valued weighted sum of Pauli strings), and an ansatz circuit with parameter vector theta.

* Quantum backend prepares `|psi(theta)>` and estimates observables.
* Energy objective: `E(theta) = <psi(theta)|H|psi(theta)>`.
* A **classical** optimizer proposes theta, consumes E(theta), and repeats.
* Variational principle: for normalized ansatz states and exact expectations, `E(theta) >= E0`, where E0 is the smallest eigenvalue of H.
* Output is an **estimated ground energy** and optionally the prepared candidate state (simulator only where accessible), not a guarantee of the exact eigenvector or a claim of quantum advantage.

A Hamiltonian ground state is not necessarily the computational state `|0...0>`; degenerate ground spaces are possible. `H` must be Hermitian. Define Pauli-string qubit ordering explicitly and keep it consistent across matrices, circuit qubits, and result serialization.

## 3. Proposed experimental API (not yet implemented)

Python bridge request, one JSON object per line:

```json
{"id": 8, "tool": "estimate_ground_energy", "args": {
  "hamiltonian": [{"pauli":"Z","coefficient":1.0}],
  "ansatz": "ry_single_qubit",
  "optimizer": {"name":"cobyla","max_iterations":100},
  "backend": "statevector",
  "seed": 7
}}
```

If/when implemented, return an ordinary bridge envelope:

```json
{"id":8,"ok":true,"result":{
  "status":"converged",
  "estimated_energy":-1.0,
  "exact_reference_energy":-1.0,
  "parameters":[3.141592653589793],
  "iterations":42,
  "backend":"statevector",
  "shots":null,
  "seed":7,
  "units":"dimensionless",
  "warnings":[]
}}
```

**These numbers are illustrative schema values, NOT outputs from a run.** Exact reference calculations should use NumPy/SciPy diagonalization on small matrices only, and may be omitted when infeasible. For finite-shot runs include `shots`, an uncertainty estimate where justified, and how Pauli terms were grouped/estimated. Support structured error results for invalid parameters, unsupported backend, invalid Pauli strings, excessive qubit counts, nonfinite coefficients, and optimization failure; JSON must not serialize NaN/Infinity.

API decisions before implementation:
- Choose a stable name, e.g. `estimate_ground_energy`; avoid overloading forecasting's `-qu`.
- MVP: one or two qubits; coefficient convention real; `I/X/Y/Z` Pauli strings; explicit endianness and max-qubit bounds.
- Make optimizer, ansatz depth, stopping condition, seed, and backend explicit.
- Provide iterations, evaluations, optional trace, and failure/convergence status; distinguish estimated energy from exact benchmark.
- Do not expose arbitrary user-supplied Python code, filesystem paths, or remote device credentials through a public tool.

## 4. Architecture options

**Option A, experimental PROXORA MCP endpoint:** implement numerical work in `python/src/proxora/` with a lazy import, add a dispatch function to `python/src/proxora/bridge.py`, then a Kotlin `ProxoraTool` subclass, schema validation, and registration in `ProxoraServer.defaultTools()`. Keep stdout as strict line-delimited JSON protocol data; log to stderr.

**Option B, preferred if feature expands beyond an educational proof-of-concept:** put ground-state/VQE in a separate Qimono service/app and use PROXORA's MCP and console architecture as a reusable pattern. This preserves the repository's single-purpose next-value prediction identity.

Architecture choice is an explicit decision gate, not settled by adding this document.

Current relevant repository files: `AGENTS.md`, `README.md`, `mcp/README.md`, `python/src/proxora/bridge.py`, `python/pyproject.toml`. Respect the Python 3.12 + uv setup and the tracked Guix `sitecustomize.py` shim. No new dependency or lockfile modification is authorized by this proposal.

## 5. Verification / acceptance criteria

1. **MVP physics:** for H=Z, energy minimum is -1 and a valid ground state is |1>. For H=-Z, energy minimum is -1 and |0> is a valid ground state. For H=X, minimum -1 is achieved by |- >. Tests should check energy and state overlap up to global phase, not arbitrary statevector sign.
2. **Classical reference:** calculate small-H exact eigenspectrum with `numpy.linalg.eigh`; compare VQE result within explicitly stated tolerance, and report failures honestly.
3. **Estimator integrity:** distinguish ideal analytic/statevector expectations from finite-shot sampling. Repeat seeded experiments and record seed, shots and uncertainty. Different circuit initializations or optimizers may converge differently.
4. **Bridge compatibility:** existing `predict_next`, `score_forecast`, `score_batch`, `backtest`, `ping` behavior remains unchanged. Request IDs and structured errors round-trip; multi-line sessions remain alive after errors.
5. **MCP adapter:** independently test schema validation, request mapping and serialized result; no duplicated quantum mathematics in Kotlin.
6. **Documentation:** one reproducible request/response example with actual measured output only after code is executed; list physical and backend limitations.
7. **Regression tests (when implemented):**
   ```sh
   cd python && uv run python -m unittest discover -s tests
   cd mcp && ./gradlew test
   ```
   Environment compatibility: `cd python && scripts/verify-env.sh` (non-destructive mode).
8. **No fabricated quantum advantage:** compare classical compute cost and solution quality honestly; an ideal simulator is not real quantum hardware.

## 6. Incremental milestones

- **M0 (design):** decide whether the feature belongs in PROXORA's experimental namespace or in a separate ground-state app. Output: architecture decision note.
- **M1 (classical):** implement a limited 1–2 qubit Hamiltonian parser plus NumPy exact reference solution and tests.
- **M2 (hybrid simulation):** prepare parameterized circuits; evaluate `<H>`; optimize theta with SciPy; compare with M1.
- **M3 (bridge/MCP):** only if Option A is approved, expose JSON-lines dispatcher and Kotlin tool with tests.
- **M4 (chemistry):** use a well-specified H2 electronic-structure example with finite-basis and molecular model assumptions; compare to classical Hartree–Fock/FCI as appropriate. Do not conflate static ground state with reaction kinetics.
- **M5 (publishing):** reproducible notebook, energy-versus-iteration visualization, Qimono educational demo and limitations.

## 7. Why this matters for Qimono

Q8 connects directly to the distinction between variational quantum **regression** (already in PROXORA) and variational quantum **eigensolving** (potential experimental capability). Shared workflow: a classical optimizer tunes quantum-circuit parameters based on quantum measurements. Different objective: prediction loss versus Hamiltonian expectation energy. This is a teaching opportunity and candidate scientific app, not an automatic extension of a next-value predictor.

Open questions: where should this service live, what is the minimal qubit/Pauli contract, how should simulator-vs-hardware backends be represented, and which model/validation assumptions must be visible to scientific users?
