"""Tests for the Max-Cut routes (-op, -opqaoa) and the NumPy QAOA reference."""

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import numpy as np

import proxora
from proxora.optimization import maxcut, qaoa
from proxora.optimization.maxcut import (
    brute_force_maxcut,
    expected_cut,
    grid_search_p1,
    load_edge_csv,
    qaoa_state,
    ring,
)

RING_4 = ring(4)


def write_csv(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    return path


class CsvLoading(unittest.TestCase):
    def test_header_labels_and_default_weight(self):
        g = load_edge_csv(write_csv("source,target\nA,B\nB,C\nC,A\n"))
        self.assertEqual(g.labels, ("A", "B", "C"))
        self.assertEqual(g.edges, ((0, 1, 1.0), (1, 2, 1.0), (2, 0, 1.0)))

    def test_weights_comments_and_no_header(self):
        g = load_edge_csv(write_csv("# a comment\n0,1,2.5\n\n1,2\n"))
        self.assertEqual(g.edges, ((0, 1, 2.5), (1, 2, 1.0)))

    def test_header_detected_by_non_numeric_weight(self):
        g = load_edge_csv(write_csv("a,b,cost\nx,y,3\n"))
        self.assertEqual(g.edges, ((0, 1, 3.0),))

    def test_bad_rows_raise(self):
        for text in ("A\n", "A,B,C,D\n", "A,A\n", "A,B\nB,C,heavy\n", ""):
            with self.subTest(text=text), self.assertRaises(ValueError):
                load_edge_csv(write_csv(text))


class ClassicalBaseline(unittest.TestCase):
    def test_ring4_max_cut_is_4_with_two_alternating_solutions(self):
        best, winners = brute_force_maxcut(RING_4)
        self.assertEqual(best, 4)
        self.assertEqual(sorted(winners), ["0101", "1010"])

    def test_weighted_triangle_cuts_the_heavy_edges(self):
        g = load_edge_csv(write_csv("A,B,5\nB,C,1\nC,A,5\n"))
        best, winners = brute_force_maxcut(g)
        self.assertEqual(best, 10)
        self.assertEqual(sorted(winners), ["011", "100"])  # A alone vs {B, C}


class QaoaReference(unittest.TestCase):
    def test_state_is_normalized(self):
        psi = qaoa_state(RING_4, [0.7, 0.2], [0.3, 1.1])
        self.assertAlmostEqual(float(np.vdot(psi, psi).real), 1.0, places=12)

    def test_zero_angles_give_random_guess(self):
        # |+>^4 measured: each edge cut with prob 1/2 -> <C> = |E| / 2 = 2
        self.assertAlmostEqual(expected_cut(RING_4, [0.0], [0.0]), 2.0, places=12)

    def test_p1_optimum_on_ring_is_three_quarters(self):
        # Known result (Farhi et al. 2014): p=1 on ring graphs reaches ratio 3/4
        _, _, e = grid_search_p1(RING_4, steps=101)
        self.assertAlmostEqual(e, 3.0, places=3)

    def test_p2_beats_p1(self):
        from scipy.optimize import minimize

        f = lambda x: -expected_cut(RING_4, x[:2], x[2:])
        starts = np.random.default_rng(7).uniform(0, 1.5, (8, 4))
        res = min((minimize(f, x0, method="Nelder-Mead") for x0 in starts), key=lambda r: r.fun)
        self.assertGreater(-res.fun, 3.0 + 1e-3)

    def test_fallback_sampling_is_seeded_and_labelled(self):
        with mock.patch.object(qaoa, "_run_qvm", side_effect=ImportError):
            a = qaoa.sample(RING_4, [0.5], [0.3], shots=200, seed=1)
            b = qaoa.sample(RING_4, [0.5], [0.3], shots=200, seed=1)
        self.assertEqual(a.backend, "numpy-statevector")
        self.assertIn("pyQuil", a.note)
        np.testing.assert_array_equal(a.bits, b.bits)
        self.assertEqual(a.bits.shape, (200, 4))

    def test_size_limits(self):
        with self.assertRaises(ValueError):
            qaoa_state(ring(maxcut.MAX_QAOA_NODES + 1), [0.1], [0.1])


class Routes(unittest.TestCase):
    def run_main(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = proxora.main(args)
        return status, out.getvalue(), err.getvalue()

    def test_op_prints_classical_answer(self):
        status, out, _ = self.run_main(["-op", write_csv("a,b\nb,c\nc,d\nd,a\n")])
        self.assertEqual(status, 0)
        self.assertIn("Max cut weight: 4", out)
        self.assertIn("{a, c} | {b, d}", out)

    def test_opqaoa_reports_backend_and_baseline(self):
        with mock.patch.object(qaoa, "_run_qvm", side_effect=ImportError):
            status, out, _ = self.run_main(["-opqaoa", write_csv("a,b\nb,c\nc,d\nd,a\n")])
        self.assertEqual(status, 0)
        self.assertIn("Backend: numpy-statevector", out)
        self.assertIn("Classical max cut weight: 4", out)
        self.assertIn("approximation ratio: 0.75", out)

    def test_missing_file_fails_cleanly(self):
        status, out, err = self.run_main(["-op", "/nonexistent/graph.csv"])
        self.assertEqual(status, 1)
        self.assertEqual(out, "")
        self.assertIn("proxora -op", err)

    def test_route_without_file_prints_usage(self):
        status, _, err = self.run_main(["-op"])
        self.assertEqual(status, 2)
        self.assertIn("-opqaoa", err)


if __name__ == "__main__":
    unittest.main()
