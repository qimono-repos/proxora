# optimization/

Combinatorial optimization experiments, kept apart from the next-value predictor engine in `python/`.

Same Proxora rule applies: every quantum method sits next to a classical baseline on the same problem, scored the same way.

* `qaoa/` QAOA for Max-Cut in pyQuil (Rigetti Quil), with a NumPy reference and brute-force baseline.

Not here: forecasting models (`python/src/proxora/forecast/`), MCP adapter code (`mcp/`).
