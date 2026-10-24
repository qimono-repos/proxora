"""QAOA for Max-Cut on a 4-node ring, written in pyQuil (Rigetti's Quil SDK).

Runs on the local Quantum Virtual Machine (QVM). Needs pyQuil 4.x plus the
``quilc`` compiler and ``qvm`` simulator running as servers:

    docker run --rm -it -p 5555:5555 rigetti/quilc -S
    docker run --rm -it -p 5000:5000 rigetti/qvm -S

Then:

    python qaoa_pyquil.py            # p = 1, 1000 shots
    python qaoa_pyquil.py --shots 5000

What it shows, side by side:
  1. classical baseline: brute-force Max-Cut (exact answer),
  2. ideal QAOA expectation <C> from the exact NumPy model (maxcut.py),
  3. the same circuit in Quil, sampled on the QVM with finite shots.

Quantum advantage is NOT claimed: 4 nodes is trivially solved classically.
The point is a small, inspectable QAOA whose numbers can be checked by hand.
"""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Sequence

from maxcut import RING_4, Edge, brute_force_maxcut, cut_value, grid_search_p1


def build_program(n: int, edges: Sequence[Edge], p: int = 1):
    """Parametric Quil program: angles live in classical memory (gamma[k], beta[k]).

    Compile once, then rerun with different angles through ``memory_map``.
    """
    from pyquil import Program
    from pyquil.gates import CNOT, MEASURE, RX, RZ, H

    prog = Program()
    ro = prog.declare("ro", "BIT", n)
    gamma = prog.declare("gamma", "REAL", p)
    beta = prog.declare("beta", "REAL", p)

    for q in range(n):
        prog += H(q)  # |+>^n: uniform superposition over all 2^n cuts

    for k in range(p):
        # Phase separator exp(-i gamma Z_i Z_j): CNOT, RZ(2 gamma) on target, CNOT
        for i, j in edges:
            prog += CNOT(i, j)
            prog += RZ(2 * gamma[k], j)
            prog += CNOT(i, j)
        # Mixer exp(-i beta X) on every qubit
        for q in range(n):
            prog += RX(2 * beta[k], q)

    for q in range(n):
        prog += MEASURE(q, ro[q])
    return prog


def run_on_qvm(n: int, edges: Sequence[Edge], gammas: Sequence[float], betas: Sequence[float], shots: int):
    from pyquil import get_qc

    qc = get_qc(f"{n}q-qvm")
    prog = build_program(n, edges, p=len(gammas))
    prog.wrap_in_numshots_loop(shots)
    exe = qc.compile(prog)
    result = qc.run(exe, memory_map={"gamma": list(gammas), "beta": list(betas)})
    return result.get_register_map()["ro"]  # shape (shots, n), column q = qubit q


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--shots", type=int, default=1000)
    ap.add_argument("--print-quil", action="store_true", help="print the Quil program and exit")
    args = ap.parse_args(argv)

    n, edges = 4, RING_4

    if args.print_quil:
        print(build_program(n, edges))
        return 0

    best, winners = brute_force_maxcut(n, edges)
    print(f"[classical] brute force max cut = {best}, optimal cuts: {winners}")

    g, b, ideal = grid_search_p1(n, edges)
    print(f"[ideal]     p=1 angles gamma={g:.4f} beta={b:.4f}  <C> = {ideal:.4f}  ratio = {ideal / best:.4f}")

    bits = run_on_qvm(n, edges, [g], [b], args.shots)
    cuts = [cut_value(row, edges) for row in bits]
    sampled = sum(cuts) / len(cuts)
    hit = sum(1 for c in cuts if c == best) / len(cuts)
    print(f"[qvm]       {args.shots} shots  sampled <C> = {sampled:.4f}  P(optimal cut) = {hit:.3f}")

    top = Counter("".join(map(str, row)) for row in bits).most_common(4)
    print("[qvm]       most frequent bitstrings (q0..q3):", top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
