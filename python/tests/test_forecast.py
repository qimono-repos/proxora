"""Tests for scoring and next-value prediction (classical and quantum)."""

import importlib.util
import math
import unittest

import numpy as np

from proxora.forecast import backtest, predict_next
from proxora.forecast.quantum import expectation_z0_numpy
from proxora.scoring import score_batch, score_forecast

HAS_QISKIT = importlib.util.find_spec("qiskit") is not None


class ScoringTest(unittest.TestCase):
    def test_residual_squares_and_percentage(self):
        s = score_forecast(actual=369.15, forecast=378.0, low=372.0, high=385.0)
        self.assertAlmostEqual(s.residual, -8.85)
        self.assertAlmostEqual(s.squared_error, 78.3225)
        self.assertAlmostEqual(s.spe, (8.85 / 369.15) ** 2)
        self.assertFalse(s.in_range)
        self.assertAlmostEqual(s.epsilon_loss, 372.0 - 369.15)

    def test_inside_the_tube_costs_nothing(self):
        s = score_forecast(actual=1.1692, forecast=1.14, low=1.11, high=1.17)
        self.assertTrue(s.in_range)
        self.assertEqual(s.epsilon_loss, 0.0)
        self.assertGreater(s.spe, 0.0)

    def test_range_needs_both_bounds(self):
        with self.assertRaises(ValueError):
            score_forecast(1.0, 1.0, low=0.5)

    def test_zero_actual_has_no_percentage(self):
        s = score_forecast(0.0, 0.1)
        self.assertIsNone(s.spe)
        self.assertAlmostEqual(s.squared_error, 0.01)

    def test_batch_reproduces_the_book_baseline(self):
        book = [
            ("NVDAB", 216.56, 218.5, 214, 222),
            ("TSMB", 421.22, 422, 412, 430),
            ("TSLAB", 369.15, 378, 372, 385),
            ("IBMB", 235.27, 235, 232, 238),
            ("QNTB", 36.55, 36, 34.5, 37.5),
            ("XNDU", 3.04, 3.10, 2.95, 3.30),
            ("PSQL", 5.67, 5.80, 5.55, 6.05),
            ("SLP", 0.00059, 0.00059, 0.000575, 0.000605),
            ("DOT", 1.1692, 1.14, 1.11, 1.17),
        ]
        result = score_batch(
            {"asset": a, "actual": y, "forecast": f, "low": lo, "high": hi}
            for a, y, f, lo, hi in book
        )
        overall = result["overall"]
        self.assertEqual(overall["n"], 9)
        self.assertAlmostEqual(overall["mspe"], 0.000269458568, places=9)
        self.assertAlmostEqual(overall["hit_rate"], 8 / 9)
        self.assertNotIn("mse", overall)
        self.assertIn("mse", result["by_asset"]["TSLAB"])


class LinearTest(unittest.TestCase):
    def test_recovers_the_clojure_example(self):
        p = predict_next([1, 3, 5, 7], method="lr")
        self.assertAlmostEqual(p.value, 9.0)
        self.assertAlmostEqual(p.details["slope"], 2.0)

    def test_interval_contains_point_and_widens_with_noise(self):
        clean = predict_next([1, 2, 3, 4, 5], method="lr")
        noisy = predict_next([1, 2.5, 2.8, 4.6, 4.9], method="lr")
        self.assertLessEqual(noisy.low, noisy.value)
        self.assertGreaterEqual(noisy.high, noisy.value)
        self.assertGreater(noisy.high - noisy.low, clean.high - clean.low)


class QuantumTest(unittest.TestCase):
    def test_empty_circuit_reads_plus_one(self):
        # Inputs 0 and zero angles leave |00>, so <Z_0> = +1.
        self.assertAlmostEqual(expectation_z0_numpy(np.zeros(2), np.zeros((1, 2))), 1.0)

    def test_single_ry_pi_flips_qubit(self):
        # Ry(pi) on qubit 0 alone gives |1>, so <Z_0> = -1.
        self.assertAlmostEqual(
            expectation_z0_numpy(np.array([0.0, 0.0]), np.array([[math.pi, 0.0]])), -1.0
        )

    def test_prediction_is_deterministic_and_bracketed(self):
        series = [100, 101, 103, 102, 105, 107, 106, 109, 111, 110, 113]
        a = predict_next(series, method="qu", seed=7)
        b = predict_next(series, method="qu", seed=7)
        self.assertEqual(a.value, b.value)
        self.assertLessEqual(a.low, a.value)
        self.assertGreaterEqual(a.high, a.value)
        self.assertEqual(a.details["qubits"], 2)

    def test_trend_continues_past_the_maximum(self):
        p = predict_next([10, 11, 12, 13, 14, 15, 16, 17], method="qu")
        self.assertAlmostEqual(p.value, 18.0, delta=0.5)

    def test_too_short_series_is_rejected(self):
        with self.assertRaises(ValueError):
            predict_next([1, 2, 3], method="qu")

    @unittest.skipUnless(HAS_QISKIT, "qiskit not installed")
    def test_numpy_and_qiskit_backends_agree(self):
        from proxora.forecast.quantum import expectation_z0_qiskit

        rng = np.random.default_rng(0)
        for _ in range(5):
            x = rng.uniform(0, 1, 3)
            thetas = rng.uniform(0, 2 * math.pi, (2, 3))
            self.assertAlmostEqual(
                expectation_z0_numpy(x, thetas), expectation_z0_qiskit(x, thetas), places=10
            )


class BacktestTest(unittest.TestCase):
    def test_compares_both_methods_on_the_same_steps(self):
        series = [100, 101, 103, 102, 105, 107, 106, 109, 111, 110, 113]
        result = backtest(series)
        self.assertEqual(set(result), {"lr", "qu"})
        self.assertEqual(result["lr"]["summary"]["n"], result["qu"]["summary"]["n"])
        self.assertIsNotNone(result["qu"]["summary"]["rmspe"])


if __name__ == "__main__":
    unittest.main()
