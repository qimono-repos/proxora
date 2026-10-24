"""Max-Cut: classical baseline and an exact NumPy model of the QAOA circuit.

This module has no quantum SDK dependency. It is the reference that the
pyQuil program in ``qaoa_pyquil.py`` is checked against.

Conventions
-----------
* Graph: list of undirected edges ``(i, j)`` over qubits ``0..n-1``.
* Bit ordering: qubit ``q`` is bit ``q`` of the basis index,
  ``bit_q(x) = (x >> q) & 1``. This matches pyQuil's ``ro[q]`` readout.
* Spin mapping: bit 0 -> z = +1, bit 1 -> z = -1 (eigenvalues of Z).
* Cost: C(x) = sum over edges of (1 - z_i z_j) / 2 = number of cut edges.
* Phase separator (one layer): U_C(gamma) = exp(-i gamma * sum_edges Z_i Z_j).
  It differs from exp(-i gamma C) only by a global phase and the sign of
  gamma, which the angle search covers anyway.
* Mixer: U_B(beta) = prod_q exp(-i beta X_q) = prod_q RX(2 beta).
"""

from __future__ import annotations

from itertools import product
from typing import Sequence

import numpy as np

Edge = tuple[int, int]

RING_4: list[Edge] = [(0, 1), (1, 2), (2, 3), (3, 0)]


def bits_of(x: int, n: int) -> list[int]:
    return [(x >> q) & 1 for q in range(n)]


def cut_value(bits: Sequence[int], edges: Sequence[Edge]) -> int:
    return sum(1 for i, j in edges if bits[i] != bits[j])


def brute_force_maxcut(n: int, edges: Sequence[Edge]) -> tuple[int, list[str]]:
    """Classical baseline: try all 2^n assignments.

    Returns the best cut and every optimal bitstring, written q0 q1 ... q(n-1).
    """
    best, winners = -1, []
    for bits in product((0, 1), repeat=n):
        c = cut_value(bits, edges)
        label = "".join(map(str, bits))
        if c > best:
            best, winners = c, [label]
        elif c == best:
            winners.append(label)
    return best, winners


def _cut_table(n: int, edges: Sequence[Edge]) -> np.ndarray:
    return np.array([cut_value(bits_of(x, n), edges) for x in range(2**n)], dtype=float)


def _zz_table(n: int, edges: Sequence[Edge]) -> np.ndarray:
    # sum_edges z_i z_j for each basis state; z = 1 - 2 * bit
    out = np.zeros(2**n)
    for x in range(2**n):
        b = bits_of(x, n)
        out[x] = sum((1 - 2 * b[i]) * (1 - 2 * b[j]) for i, j in edges)
    return out


def _apply_rx_all(psi: np.ndarray, n: int, beta: float) -> np.ndarray:
    # exp(-i beta X) = [[cos b, -i sin b], [-i sin b, cos b]] on every qubit
    c, s = np.cos(beta), -1j * np.sin(beta)
    psi = psi.reshape([2] * n)  # axis k <-> qubit n-1-k (C order, little endian index)
    for axis in range(n):
        a0 = np.take(psi, 0, axis=axis)
        a1 = np.take(psi, 1, axis=axis)
        psi = np.stack([c * a0 + s * a1, s * a0 + c * a1], axis=axis)
    return psi.reshape(-1)


def qaoa_state(n: int, edges: Sequence[Edge], gammas: Sequence[float], betas: Sequence[float]) -> np.ndarray:
    """Exact statevector after p QAOA layers starting from |+>^n."""
    if len(gammas) != len(betas):
        raise ValueError("gammas and betas must have the same length (p)")
    zz = _zz_table(n, edges)
    psi = np.full(2**n, 2 ** (-n / 2), dtype=complex)
    for g, b in zip(gammas, betas):
        psi = psi * np.exp(-1j * g * zz)
        psi = _apply_rx_all(psi, n, b)
    return psi


def expected_cut(n: int, edges: Sequence[Edge], gammas: Sequence[float], betas: Sequence[float]) -> float:
    """<C> for the ideal (noiseless, infinite-shot) QAOA state."""
    probs = np.abs(qaoa_state(n, edges, gammas, betas)) ** 2
    return float(probs @ _cut_table(n, edges))


def grid_search_p1(n: int, edges: Sequence[Edge], steps: int = 101) -> tuple[float, float, float]:
    """Best (gamma, beta, <C>) for p = 1 on a uniform grid.

    gamma in [0, pi), beta in [0, pi/2): one period of each for integer-weight Max-Cut.
    """
    best = (0.0, 0.0, -np.inf)
    for g in np.linspace(0, np.pi, steps, endpoint=False):
        for b in np.linspace(0, np.pi / 2, steps, endpoint=False):
            e = expected_cut(n, edges, [g], [b])
            if e > best[2]:
                best = (float(g), float(b), e)
    return best
