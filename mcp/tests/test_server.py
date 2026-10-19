"""Tests for the PROXORA MCP adapter: tool registry, tool calls, and stdio."""

import json
import os
import sys
import unittest
from pathlib import Path

from proxora_mcp.server import server

ROOT = Path(__file__).resolve().parents[2]


def payload(result) -> dict:
    """Return the JSON body of a CallToolResult."""
    return json.loads(result.content[0].text)


class ToolRegistryTest(unittest.IsolatedAsyncioTestCase):
    async def test_exposes_the_four_tools(self):
        names = {tool.name for tool in await server.list_tools()}
        self.assertEqual(names, {"score_forecast", "score_batch", "predict_next", "backtest"})


class ToolCallTest(unittest.IsolatedAsyncioTestCase):
    async def test_score_forecast_out_of_tube(self):
        body = payload(
            await server.call_tool(
                "score_forecast", {"actual": 369.15, "forecast": 378, "low": 372, "high": 385}
            )
        )
        self.assertFalse(body["in_range"])
        self.assertAlmostEqual(body["squared_error"], 78.3225)
        self.assertAlmostEqual(body["epsilon_loss"], 2.85)

    async def test_score_batch_summaries(self):
        records = [
            {"asset": "TSLAB", "actual": 369.15, "forecast": 378, "low": 372, "high": 385},
            {"asset": "DOT", "actual": 1.1692, "forecast": 1.14, "low": 1.11, "high": 1.17},
        ]
        body = payload(await server.call_tool("score_batch", {"records": records}))
        self.assertEqual(body["overall"]["n"], 2)
        self.assertAlmostEqual(body["overall"]["hit_rate"], 0.5)
        self.assertEqual(set(body["by_asset"]), {"TSLAB", "DOT"})

    async def test_predict_next_both_methods(self):
        series = [10, 11, 12, 13, 14, 15, 16, 17]
        lr = payload(await server.call_tool("predict_next", {"values": series}))
        qu = payload(await server.call_tool("predict_next", {"values": series, "method": "qu"}))
        self.assertAlmostEqual(lr["value"], 18.0)
        self.assertEqual(qu["method"], "qu")
        self.assertAlmostEqual(qu["value"], 18.0, delta=0.5)

    async def test_backtest_lr_only(self):
        body = payload(
            await server.call_tool(
                "backtest", {"values": [1, 2, 3, 4, 5, 6, 7, 8], "methods": ["lr"]}
            )
        )
        self.assertEqual(set(body), {"lr"})
        self.assertAlmostEqual(body["lr"]["summary"]["mspe"], 0.0)


class StdioTest(unittest.IsolatedAsyncioTestCase):
    """Launch the server as a subprocess, the way an MCP client does."""

    async def test_round_trip_over_stdio(self):
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT / "mcp" / "src"), str(ROOT / "python" / "src"), env.get("PYTHONPATH", "")]
        )
        params = StdioServerParameters(command=sys.executable, args=["-m", "proxora_mcp"], env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                self.assertIn("predict_next", {t.name for t in tools.tools})
                result = await session.call_tool("predict_next", {"values": [1, 3, 5, 7]})
                self.assertAlmostEqual(payload(result)["value"], 9.0)


if __name__ == "__main__":
    unittest.main()
