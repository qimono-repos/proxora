"""Combinatorial optimization routes: classical Max-Cut (-op) and QAOA (-opqaoa).

Same Proxora rule as forecasting: the quantum method runs next to an exact
classical baseline on the same input and is scored the same way (cut weight).
"""

from __future__ import annotations

import sys
from collections import Counter

from proxora.optimization.maxcut import (
    Graph,
    brute_force_maxcut,
    cut_value,
    optimize_p1,
    load_edge_csv,
)


def _describe(g: Graph) -> str:
    return f"{g.n} nodes, {len(g.edges)} edges, total weight {sum(w for *_, w in g.edges):g}"


def _assignment(bits: str, g: Graph) -> str:
    a = [lab for lab, b in zip(g.labels, bits) if b == "0"]
    b = [lab for lab, b in zip(g.labels, bits) if b == "1"]
    return f"{{{', '.join(a)}}} | {{{', '.join(b)}}}"


def run_classical(path: str) -> int:
    g = load_edge_csv(path)
    best, winners = brute_force_maxcut(g)
    print("PROXORA: Max-Cut, classical brute force")
    print(f"Graph: {_describe(g)}")
    print(f"Nodes (q0..q{g.n - 1}): {', '.join(g.labels)}")
    print(f"Max cut weight: {best:g}")
    print(f"Optimal cuts ({len(winners)}):")
    for w in winners[:8]:
        print(f"  {w}  {_assignment(w, g)}")
    if len(winners) > 8:
        print(f"  ... {len(winners) - 8} more")
    return 0


def run_qaoa(path: str) -> int:
    from proxora.optimization.qaoa import SHOTS, sample

    g = load_edge_csv(path)
    best, _ = brute_force_maxcut(g)
    gamma, beta, ideal = optimize_p1(g)
    s = sample(g, [gamma], [beta], shots=SHOTS)

    cuts = [cut_value([int(c) for c in row], g) for row in s.strings()]
    sampled = sum(cuts) / len(cuts)
    hit = sum(1 for c in cuts if abs(c - best) < 1e-9) / len(cuts)
    top_bits, top_count = Counter(s.strings()).most_common(1)[0]
    best_sampled = max(set(s.strings()), key=lambda b: cut_value([int(c) for c in b], g))

    print("PROXORA: Max-Cut, QAOA p=1 (pyQuil / Quil)")
    print(f"Graph: {_describe(g)}")
    print(f"Nodes (q0..q{g.n - 1}): {', '.join(g.labels)}")
    print(f"Backend: {s.backend}" + (f"  [{s.note}]" if s.note else ""))
    print(f"Angles (grid + Nelder-Mead on exact model): gamma={gamma:.6f} beta={beta:.6f}")
    print(f"Classical max cut weight: {best:g}")
    print(f"Ideal <C>: {ideal:.6f}  approximation ratio: {ideal / best:.4f}")
    print(f"Sampled <C> ({SHOTS} shots): {sampled:.4f}  P(optimal cut): {hit:.3f}")
    print(f"Most frequent: {top_bits} ({top_count} shots)")
    print(f"Best sampled cut: {best_sampled} weight {cut_value([int(c) for c in best_sampled], g):g}"
          f"  {_assignment(best_sampled, g)}")
    return 0


def run(route: str, path: str) -> int:
    try:
        return run_classical(path) if route == "-op" else run_qaoa(path)
    except (OSError, ValueError) as exc:
        print(f"proxora {route}: {exc}", file=sys.stderr)
        return 1
