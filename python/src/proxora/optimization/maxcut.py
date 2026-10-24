"""Max-Cut: graph loading, classical baseline and an exact NumPy model of QAOA.

No quantum SDK is imported here. This module is the reference that the pyQuil
program in ``proxora.optimization.qaoa`` is checked against.

Conventions
-----------
* Graph: undirected weighted edges ``(i, j, w)`` over nodes ``0..n-1``.
* Bit ordering: node/qubit ``q`` is bit ``q`` of the basis index,
  ``bit_q(x) = (x >> q) & 1``. This matches pyQuil's ``ro[q]`` readout.
* Spin mapping: bit 0 -> z = +1, bit 1 -> z = -1 (eigenvalues of Z).
* Cost: C(x) = sum over edges of w * (1 - z_i z_j) / 2 = total weight of cut edges.
* Phase separator (one layer): U_C(gamma) = exp(-i gamma * sum_edges w Z_i Z_j).
  It differs from exp(-i gamma C) only by a global phase and the sign of
  gamma, which the angle search covers anyway.
* Mixer: U_B(beta) = prod_q exp(-i beta X_q) = prod_q RX(2 beta).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

MAX_BRUTE_FORCE_NODES = 20
MAX_QAOA_NODES = 12


@dataclass(frozen=True)
class Graph:
    labels: tuple[str, ...]
    edges: tuple[tuple[int, int, float], ...]

    @property
    def n(self) -> int:
        return len(self.labels)


def ring(n: int) -> Graph:
    return Graph(tuple(str(i) for i in range(n)), tuple((i, (i + 1) % n, 1.0) for i in range(n)))


def load_edge_csv(path: str | Path) -> Graph:
    """Read an edge list: ``source,target[,weight]`` per row.

    Node names are free text, numbered in order of first appearance. A first
    row whose weight column is not numeric (or that reads ``source,target``)
    is treated as a header. Blank lines and lines starting with ``#`` are skipped.
    """
    labels: dict[str, int] = {}
    edges: list[tuple[int, int, float]] = []

    def index(name: str) -> int:
        return labels.setdefault(name, len(labels))

    with open(path, newline="") as handle:
        rows = [r for r in csv.reader(handle) if r and not r[0].lstrip().startswith("#")]

    for line_no, row in enumerate(rows, start=1):
        cells = [c.strip() for c in row]
        if len(cells) not in (2, 3) or not cells[0] or not cells[1]:
            raise ValueError(f"line {line_no}: expected source,target[,weight], got {row!r}")
        if line_no == 1 and _looks_like_header(cells):
            continue
        weight = 1.0
        if len(cells) == 3 and cells[2]:
            try:
                weight = float(cells[2])
            except ValueError:
                raise ValueError(f"line {line_no}: weight {cells[2]!r} is not a number") from None
            if not np.isfinite(weight):
                raise ValueError(f"line {line_no}: weight must be finite")
        if cells[0] == cells[1]:
            raise ValueError(f"line {line_no}: self-loop {cells[0]!r} can never be cut")
        edges.append((index(cells[0]), index(cells[1]), weight))

    if not edges:
        raise ValueError("no edges found")
    return Graph(tuple(labels), tuple(edges))


def _looks_like_header(cells: list[str]) -> bool:
    if [c.lower() for c in cells[:2]] in (["source", "target"], ["from", "to"], ["u", "v"]):
        return True
    if len(cells) == 3:
        try:
            float(cells[2])
        except ValueError:
            return True
    return False


def _bit_matrix(n: int) -> np.ndarray:
    x = np.arange(2**n)
    return (x[:, None] >> np.arange(n)) & 1  # shape (2^n, n)


def cut_table(g: Graph) -> np.ndarray:
    """C(x) for every basis state x."""
    bits = _bit_matrix(g.n)
    out = np.zeros(2**g.n)
    for i, j, w in g.edges:
        out += w * (bits[:, i] != bits[:, j])
    return out


def _zz_table(g: Graph) -> np.ndarray:
    z = 1 - 2 * _bit_matrix(g.n)
    out = np.zeros(2**g.n)
    for i, j, w in g.edges:
        out += w * z[:, i] * z[:, j]
    return out


def bitstring(x: int, n: int) -> str:
    """Basis index -> 'q0 q1 ... q(n-1)' as a string of bits."""
    return "".join(str((x >> q) & 1) for q in range(n))


def cut_value(bits: Sequence[int], g: Graph) -> float:
    return float(sum(w for i, j, w in g.edges if bits[i] != bits[j]))


def brute_force_maxcut(g: Graph) -> tuple[float, list[str]]:
    """Classical baseline: evaluate all 2^n assignments.

    Returns the best cut weight and every optimal bitstring (q0 q1 ... q(n-1)).
    """
    if g.n > MAX_BRUTE_FORCE_NODES:
        raise ValueError(f"{g.n} nodes: brute force is limited to {MAX_BRUTE_FORCE_NODES}")
    table = cut_table(g)
    best = float(table.max())
    winners = np.flatnonzero(np.isclose(table, best))
    return best, [bitstring(int(x), g.n) for x in winners]


def _apply_rx_all(psi: np.ndarray, n: int, beta: float) -> np.ndarray:
    # exp(-i beta X) = [[cos b, -i sin b], [-i sin b, cos b]] on every qubit
    c, s = np.cos(beta), -1j * np.sin(beta)
    psi = psi.reshape([2] * n)
    for axis in range(n):
        a0 = np.take(psi, 0, axis=axis)
        a1 = np.take(psi, 1, axis=axis)
        psi = np.stack([c * a0 + s * a1, s * a0 + c * a1], axis=axis)
    return psi.reshape(-1)


def qaoa_state(g: Graph, gammas: Sequence[float], betas: Sequence[float]) -> np.ndarray:
    """Exact statevector after p QAOA layers starting from |+>^n."""
    if len(gammas) != len(betas):
        raise ValueError("gammas and betas must have the same length (p)")
    if g.n > MAX_QAOA_NODES:
        raise ValueError(f"{g.n} nodes: the statevector model is limited to {MAX_QAOA_NODES} qubits")
    zz = _zz_table(g)
    psi = np.full(2**g.n, 2 ** (-g.n / 2), dtype=complex)
    for gamma, beta in zip(gammas, betas):
        psi = psi * np.exp(-1j * gamma * zz)
        psi = _apply_rx_all(psi, g.n, beta)
    return psi


def probabilities(g: Graph, gammas: Sequence[float], betas: Sequence[float]) -> np.ndarray:
    return np.abs(qaoa_state(g, gammas, betas)) ** 2


def expected_cut(g: Graph, gammas: Sequence[float], betas: Sequence[float]) -> float:
    """<C> for the ideal (noiseless, infinite-shot) QAOA state."""
    return float(probabilities(g, gammas, betas) @ cut_table(g))


def grid_search_p1(g: Graph, steps: int = 61) -> tuple[float, float, float]:
    """Best (gamma, beta, <C>) for p = 1 on a uniform grid.

    gamma in [0, pi), beta in [0, pi/2). That is one full period for
    integer weights; for non-integer weights it is a search window, not a period.
    """
    zz, cuts = _zz_table(g), cut_table(g)
    plus = np.full(2**g.n, 2 ** (-g.n / 2), dtype=complex)
    best = (0.0, 0.0, -np.inf)
    for gamma in np.linspace(0, np.pi, steps, endpoint=False):
        phased = plus * np.exp(-1j * gamma * zz)
        for beta in np.linspace(0, np.pi / 2, steps, endpoint=False):
            e = float(np.abs(_apply_rx_all(phased, g.n, beta)) ** 2 @ cuts)
            if e > best[2]:
                best = (float(gamma), float(beta), e)
    return best


def optimize_p1(g: Graph, steps: int = 61) -> tuple[float, float, float]:
    """Grid search for a good start, then Nelder-Mead on the exact model.

    This is the classical outer loop of QAOA. Here it runs on the ideal
    expectation; on hardware the same loop would run on sampled <C>.
    """
    from scipy.optimize import minimize

    gamma, beta, e = grid_search_p1(g, steps)
    res = minimize(lambda x: -expected_cut(g, [x[0]], [x[1]]), [gamma, beta],
                   method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-10})
    if -res.fun > e:
        return float(res.x[0]), float(res.x[1]), float(-res.fun)
    return gamma, beta, e
