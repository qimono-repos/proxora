"""QAOA for Max-Cut in pyQuil (Rigetti Quil), sampled on the QVM.

pyQuil is optional (``uv sync --extra rigetti``) and imported lazily. The QVM
needs the ``quilc`` compiler and ``qvm`` simulator running as servers:

    docker run --rm -it -p 5555:5555 rigetti/quilc -S
    docker run --rm -it -p 5000:5000 rigetti/qvm -S

When pyQuil or the servers are unavailable, ``sample`` falls back to drawing
shots from the exact NumPy statevector, and says so in the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from proxora.optimization.maxcut import Graph, bitstring, probabilities

SHOTS = 1000
SEED = 42


def build_program(g: Graph, p: int = 1):
    """Parametric Quil program: angles live in classical memory gamma[k], beta[k].

    Compile once, then rerun with different angles through ``memory_map``.
    """
    from pyquil import Program
    from pyquil.gates import CNOT, MEASURE, RX, RZ, H

    prog = Program()
    ro = prog.declare("ro", "BIT", g.n)
    gamma = prog.declare("gamma", "REAL", p)
    beta = prog.declare("beta", "REAL", p)

    for q in range(g.n):
        prog += H(q)  # |+>^n: uniform superposition over all 2^n cuts

    for k in range(p):
        # Phase separator exp(-i gamma w Z_i Z_j): CNOT, RZ(2 w gamma) on target, CNOT
        for i, j, w in g.edges:
            prog += CNOT(i, j)
            prog += RZ(2 * w * gamma[k], j)
            prog += CNOT(i, j)
        # Mixer exp(-i beta X) on every qubit
        for q in range(g.n):
            prog += RX(2 * beta[k], q)

    for q in range(g.n):
        prog += MEASURE(q, ro[q])
    return prog


def _run_qvm(g: Graph, gammas: Sequence[float], betas: Sequence[float], shots: int) -> np.ndarray:
    from pyquil import get_qc

    qc = get_qc(f"{g.n}q-qvm")
    prog = build_program(g, p=len(gammas))
    prog.wrap_in_numshots_loop(shots)
    exe = qc.compile(prog)
    result = qc.run(exe, memory_map={"gamma": list(gammas), "beta": list(betas)})
    return np.asarray(result.get_register_map()["ro"])  # (shots, n), column q = qubit q


def _sample_statevector(g: Graph, gammas, betas, shots: int, seed: int) -> np.ndarray:
    probs = probabilities(g, gammas, betas)
    draws = np.random.default_rng(seed).choice(len(probs), size=shots, p=probs / probs.sum())
    return (draws[:, None] >> np.arange(g.n)) & 1


@dataclass
class Samples:
    bits: np.ndarray  # (shots, n)
    backend: str      # "pyquil-qvm" or "numpy-statevector"
    note: str = ""

    def strings(self) -> list[str]:
        return ["".join(map(str, row)) for row in self.bits]


def sample(g: Graph, gammas: Sequence[float], betas: Sequence[float],
           shots: int = SHOTS, seed: int = SEED) -> Samples:
    try:
        return Samples(_run_qvm(g, gammas, betas, shots), "pyquil-qvm")
    except ImportError:
        note = "pyQuil not installed (uv sync --extra rigetti)"
    except Exception as exc:  # quilc/qvm not reachable, compile error, ...
        note = f"QVM unavailable: {type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}".rstrip(": ")
    return Samples(_sample_statevector(g, gammas, betas, shots, seed), "numpy-statevector", note)


__all__ = ["build_program", "sample", "Samples", "SHOTS", "SEED", "bitstring"]
