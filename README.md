# PROXORA

*proxora* /prok-SOR-ah/ — **next-value predictor**.

A focused command-line tool that predicts the next value in a sequence. One task, classical or quantum implementation.

![project-art](./assets/image_readme.png)

## Name

**PROXORA** is a coined name inspired by *proximity* and the idea of what comes next. It is not an established Esperanto word.

- *proximity* — nearness; closeness to the present point in a sequence.
- *future* — the not-yet-observed value to be estimated.

Esperanto note: *proksima* means “near” or “close”; *proksimo* is related to proximity. **PROXORA** is a creative project name, not a literal Esperanto derivation.

## Usage

Choose the implementation with a short flag:

```bash
proxora -lr
proxora -qu
```

- `-lr` — classical linear-regression implementation.
- `-qu` — quantum implementation using a variational quantum regressor.

The command examples describe the intended interface. Input arguments and output behavior depend on the implementation.

### As an MCP server

The [`mcp/`](mcp/README.md) folder exposes the engine to AI clients as Model
Context Protocol tools: `predict_next` (`lr` or `qu`), `score_forecast`,
`score_batch` (SPE, MSPE, RMSPE, hit rate) and `backtest`.

## Layout

```
bin/        CLI dispatcher (Babashka)
clojure/    classical regression in Clojure
python/     the engine: proxora.forecast (lr, qu) and proxora.scoring
mcp/        MCP adapter over the engine
specs/      task specifications
```

## Purpose

PROXORA does one thing: **predict the next value**.

It is designed to compare classical regression with variational quantum regression on that same task. The quantum model uses a parameterized quantum circuit whose parameters are optimized with a classical procedure.

Quantum methods are not assumed to be better by default. Predictive quality, reproducibility, and computational cost must be evaluated against appropriate baselines.

## Principles

- **One job, done well.**
- **Same task, comparable evaluation.**
- **Clear mathematics and reproducible results.**
- **No claims of quantum advantage without evidence.**
- **Implementation independence:** the name remains valid if the model, optimizer, circuit, or backend changes.

---

*PROXORA — the next value, estimated.*

## License

PROXORA is free software licensed under the GNU Affero General Public License,
version 3 or (at your option) any later version.

See [LICENSE](LICENSE) for the full license text.

Copyright (C) 2026 Qimono
