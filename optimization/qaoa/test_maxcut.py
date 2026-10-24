"""Checks for the NumPy QAOA reference. Run: python -m unittest test_maxcut (from this folder)."""

import unittest

import numpy as np

from maxcut import RING_4, brute_force_maxcut, expected_cut, grid_search_p1, qaoa_state


class ClassicalBaseline(unittest.TestCase):
    def test_ring4_max_cut_is_4_with_two_alternating_solutions(self):
        best, winners = brute_force_maxcut(4, RING_4)
        self.assertEqual(best, 4)
        self.assertEqual(sorted(winners), ["0101", "1010"])


class QaoaReference(unittest.TestCase):
    def test_state_is_normalized(self):
        psi = qaoa_state(4, RING_4, [0.7, 0.2], [0.3, 1.1])
        self.assertAlmostEqual(float(np.vdot(psi, psi).real), 1.0, places=12)

    def test_zero_angles_give_random_guess(self):
        # |+>^4 measured: each edge cut with prob 1/2 -> <C> = |E| / 2 = 2
        self.assertAlmostEqual(expected_cut(4, RING_4, [0.0], [0.0]), 2.0, places=12)

    def test_p1_optimum_on_2_regular_ring_is_three_quarters(self):
        # Known analytic result (Farhi et al. 2014): p=1 on ring graphs reaches ratio 3/4
        g, b, e = grid_search_p1(4, RING_4, steps=101)
        self.assertAlmostEqual(e, 3.0, places=3)

    def test_p2_beats_p1(self):
        from scipy.optimize import minimize

        f = lambda x: -expected_cut(4, RING_4, x[:2], x[2:])
        res = min((minimize(f, x0, method="Nelder-Mead") for x0 in np.random.default_rng(7).uniform(0, 1.5, (8, 4))),
                  key=lambda r: r.fun)
        self.assertGreater(-res.fun, 3.0 + 1e-3)


if __name__ == "__main__":
    unittest.main()
