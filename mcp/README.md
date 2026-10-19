# PROXORA MCP server (Kotlin)

The PROXORA engine exposed as [Model Context Protocol](https://modelcontextprotocol.io)
tools, written in Kotlin with the official
[MCP Kotlin SDK](https://github.com/modelcontextprotocol/kotlin-sdk).

The mathematics stays in one place, the Python engine. This server is the
**adapter**: it speaks MCP to the client and line-delimited JSON to the engine.

```
MCP client (Claude, other models)
      │  MCP over stdio
      ▼
mcp/       Kotlin: ProxoraServer → ProxoraTool subclasses → EngineClient
      │  one JSON object per line over a pipe
      ▼
python/    python -m proxora.bridge → proxora.forecast, proxora.scoring (NumPy, SciPy, Qiskit)
```

## Tools

| Tool | What it does |
|---|---|
| `score_forecast` | One forecast vs the observed value: residual, square error, percentage error, **SPE**, and for a range `[low, high]` whether it landed inside and the epsilon-tube loss. |
| `score_batch` | Many forecasts: per-row scores, plus **MSPE / RMSPE / MAPE / hit rate**, overall and per asset. |
| `predict_next` | Next value of a series as a point plus a range: `lr` (least squares) or `qu` (variational quantum regressor). |
| `backtest` | Walk-forward comparison of `lr` and `qu` on one series, same metrics. |

The mathematics behind each tool is documented in the engine:
`python/src/proxora/scoring.py` and `python/src/proxora/forecast/`.

## Code tour

```
src/main/kotlin/vip/qimono/proxora/mcp/
├── Main.kt                 stdio entry point
├── ProxoraServer.kt        builds the SDK Server and registers every tool
├── engine/
│   ├── Engine.kt           interface: request(tool, argumentsJson) → reply line
│   ├── EngineClient.kt     one long-lived Python process, restart + retry once
│   └── EngineCommand.kt    how to start the engine (env vars, repo layout)
└── tools/
    ├── ProxoraTool.kt      abstract base: validate → call engine → MCP result
    ├── EngineReply.kt      sealed Success / Failure, mapped to CallToolResult
    ├── Schemas.kt          JSON Schema builders
    └── ScoreForecastTool.kt, ScoreBatchTool.kt, PredictNextTool.kt, BacktestTool.kt
```

Adding a tool means one new `ProxoraTool` subclass (name, description,
schema), one entry in `ProxoraServer.defaultTools()`, and the matching
function in `python/src/proxora/bridge.py`.

## Requirements

- JDK 21 (`sudo apt install openjdk-21-jdk-headless` on Ubuntu)
- Gradle, only once, to generate the wrapper
- [uv](https://docs.astral.sh/uv/) and the engine's Python environment (`cd ../python && uv sync`)

## Build and run

```bash
cd mcp
gradle wrapper --gradle-version 9.8.0   # once; afterwards use ./gradlew
./gradlew test                           # unit tests + tests against the real Python engine
./gradlew shadowJar                      # build/libs/proxora-mcp-0.2.0-all.jar
```

The server finds the engine through, in order:

1. `PROXORA_ENGINE_CMD`: a full command, e.g. `python3 -m proxora.bridge`;
2. `PROXORA_ENGINE_DIR`: the repo's `python/` folder, run with `uv run`;
3. the repo layout: `../python` from `mcp/`, or `python` from the repo root.

### Connect a client

Claude Code:

```bash
claude mcp add proxora \
  -e PROXORA_ENGINE_DIR=/path/to/proxora/python \
  -- java -jar /path/to/proxora/mcp/build/libs/proxora-mcp-0.2.0-all.jar
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "proxora": {
      "command": "java",
      "args": ["-jar", "/path/to/proxora/mcp/build/libs/proxora-mcp-0.2.0-all.jar"],
      "env": { "PROXORA_ENGINE_DIR": "/path/to/proxora/python" }
    }
  }
}
```

The engine bridge can also be driven by hand, which helps when debugging:

```bash
cd python
echo '{"id":1,"tool":"predict_next","args":{"values":[1,3,5,7]}}' | uv run python -m proxora.bridge
```

## License

GNU Affero General Public License, version 3 or later. See [LICENSE](../LICENSE).
