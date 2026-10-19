"""Tests for the line-delimited JSON engine bridge used by the Kotlin MCP server."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from proxora.bridge import handle

SRC = Path(__file__).resolve().parents[1] / "src"


class HandleTest(unittest.TestCase):
    def test_predict_next_lr(self):
        response = handle({"id": 1, "tool": "predict_next", "args": {"values": [1, 3, 5, 7]}})
        self.assertTrue(response["ok"])
        self.assertEqual(response["id"], 1)
        self.assertAlmostEqual(response["result"]["value"], 9.0)

    def test_predict_next_qu_passes_options(self):
        args = {"values": [100, 101, 103, 102, 105, 107, 106, 109], "method": "qu", "seed": 3, "lags": 2}
        response = handle({"id": 2, "tool": "predict_next", "args": args})
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["details"]["seed"], 3)

    def test_score_batch(self):
        records = [{"asset": "DOT", "actual": 1.1692, "forecast": 1.14, "low": 1.11, "high": 1.17}]
        response = handle({"id": 3, "tool": "score_batch", "args": {"records": records}})
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["overall"]["hit_rate"], 1.0)

    def test_errors_are_data_not_crashes(self):
        self.assertFalse(handle({"id": 4, "tool": "nope"})["ok"])
        missing = handle({"id": 5, "tool": "score_forecast", "args": {}})
        self.assertFalse(missing["ok"])
        self.assertIn("actual", missing["error"])
        bad = handle({"id": 6, "tool": "predict_next", "args": {"values": [1, 2, 3], "method": "qu"}})
        self.assertFalse(bad["ok"])
        self.assertIn("ValueError", bad["error"])


class ProcessTest(unittest.TestCase):
    def test_one_response_line_per_request_line(self):
        requests = [
            {"id": 1, "tool": "ping"},
            {"id": 2, "tool": "score_forecast", "args": {"actual": 2, "forecast": 1}},
        ]
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(SRC), os.environ.get("PYTHONPATH", "")]))
        done = subprocess.run(
            [sys.executable, "-m", "proxora.bridge"],
            input="\n".join(json.dumps(r) for r in requests) + "\nnot json\n",
            capture_output=True, text=True, env=env, timeout=120, check=True,
        )
        lines = [json.loads(line) for line in done.stdout.splitlines()]
        self.assertEqual([line["id"] for line in lines], [1, 2, None])
        self.assertEqual(lines[1]["result"]["spe"], 0.25)
        self.assertFalse(lines[2]["ok"])


if __name__ == "__main__":
    unittest.main()
