# PROXORA MCP server

The PROXORA engine exposed as [Model Context Protocol](https://modelcontextprotocol.io)
tools, so any MCP client (Claude, other models, scripts) predicts and scores
forecasts with the same mathematics.

This folder is only an **adapter**. All mathematics lives in the engine,
`python/src/proxora`:

```
proxora/
├── bin/        CLI dispatcher (Babashka)
├── clojure/    classical regression, Clojure
├── python/     the engine: proxora.forecast (lr, qu), proxora.scoring
└── mcp/        this adapter: proxora_mcp.server → MCP tools
```

## Tools

| Tool | What it does |
|---|---|
| `score_forecast` | One forecast vs the observed value: residual, square error, percentage error, **SPE**, and for a range `[low, high]` whether it landed inside and the epsilon-tube loss. |
| `score_batch` | Many forecasts: per-row scores, plus **MSPE / RMSPE / MAPE / hit rate**, overall and per asset (per asset also MSE in price units). |
| `predict_next` | Next value of a series, as a point plus a range. `method="lr"`: least squares with a classical prediction interval. `method="qu"`: variational quantum regressor. |
| `backtest` | Walk-forward comparison of `lr` and `qu` on one series, scored with the same metrics. |

## The mathematics

**Scoring.** A forecast is a point on the model's line; the observed value is
the data point. The residual is `actual − forecast` and its square is the
least-squares "error square". Squares in price units cannot be averaged across
assets, so the percentage form is used to compare:

```
SPE   = ((actual − forecast) / actual)²
MSPE  = mean(SPE)        RMSPE = √MSPE   (a typical miss, as a fraction)
```

A forecast range works like the **epsilon tube of support vector regression**:
a miss inside `[low, high]` costs nothing; only the distance outside is
penalised (`epsilon_loss`, `epsilon_loss_pct`). Logging both gives the
least-squares view and the SVR view of the same forecasts.

**`lr`.** Ordinary least squares on the time index (same model as
`clojure/src/proxora/regression.clj`), with the prediction interval
`ŷ ± t · s · √(1 + 1/n + (x₀ − x̄)²/Sxx)`.

**`qu`.** A small variational quantum regressor:

- by default it learns **step changes** (`target="diff"`), so a trend can
  continue past the highest value seen; `target="level"` learns the values;
- the previous `lags` scaled values are the inputs, **one qubit per lag**;
- `layers` blocks of data re-uploading: `Ry(π·xᵢ)`, trainable `Ry(θ)`, `CZ`
  between neighbours;
- readout `⟨Z₀⟩` through a closed-form least-squares affine head, with the
  circuit angles trained by COBYLA from seeded restarts (hybrid loop);
- the range is `z · in-sample RMSE`, inflated for the parameters fitted.

`backend="numpy"` (default) is an exact statevector simulation (Ry and CZ keep
amplitudes real, so it is the state Qiskit's `Statevector` gives) and is fast
enough to train interactively. `backend="qiskit"` evaluates every circuit with
Qiskit; a test checks both agree when Qiskit is installed.

No quantum advantage is assumed. Use `backtest` and compare RMSPE.

## Run

```bash
cd mcp
uv sync
uv run proxora-mcp          # stdio server
```

### Connect a client

Claude Code:

```bash
claude mcp add proxora -- uv --directory /path/to/proxora/mcp run proxora-mcp
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "proxora": {
      "command": "uv",
      "args": ["--directory", "/path/to/proxora/mcp", "run", "proxora-mcp"]
    }
  }
}
```

## Tests

```bash
cd mcp
uv run python -m unittest discover -s tests
```

The tests call every tool in-process and also launch the server over stdio,
the way a client does.

## License

GNU Affero General Public License, version 3 or later. See [LICENSE](../LICENSE).
