"""Focused tests for the PROXORA command-line interface."""

import contextlib
import io
import math
import unittest
from unittest import mock

import proxora


class MainDispatchTest(unittest.TestCase):
    def test_quantum_flag_runs_quantum_regression(self):
        with mock.patch.object(proxora, "run_quantum_regression") as run:
            status = proxora.main(["-qu"])

        run.assert_called_once_with()
        self.assertEqual(status, 0)

    def test_missing_flag_prints_usage_and_fails(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = proxora.main([])

        self.assertEqual(status, 2)
        self.assertIn("Usage: proxora -qu", stderr.getvalue())

    def test_unknown_flag_prints_usage_and_fails(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = proxora.main(["--bogus"])

        self.assertEqual(status, 2)
        self.assertIn("Usage: proxora -qu", stderr.getvalue())

    def test_extra_argument_around_quantum_flag_fails(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = proxora.main(["-qu", "extra"])

        self.assertEqual(status, 2)
        self.assertIn("Usage: proxora -qu", stderr.getvalue())


class ProbabilityTest(unittest.TestCase):
    def test_ry_zero_measures_zero(self):
        self.assertAlmostEqual(proxora.probability_of_one(0.0), 0.0)

    def test_ry_pi_measures_one(self):
        self.assertAlmostEqual(proxora.probability_of_one(math.pi), 1.0)


if __name__ == "__main__":
    unittest.main()
