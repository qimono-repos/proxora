"""Engine bridge: the PROXORA engine as a line-delimited JSON process.

Any language can drive the engine by starting ``python -m proxora.bridge`` and
exchanging one JSON object per line over stdin/stdout. The Kotlin MCP server
does exactly that; the engine stays the single home of the mathematics.

Request  (one line):  {"id": 1, "tool": "predict_next", "args": {"values": [1, 3, 5, 7]}}
Response (one line):  {"id": 1, "ok": true,  "result": {...}}
                      {"id": 1, "ok": false, "error": "ValueError: ..."}

Tools: score_forecast, score_batch, predict_next, backtest, ping.
Only responses are written to stdout; anything else goes to stderr.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

from proxora import scoring
from proxora.forecast import backtest, predict_next


def _score_forecast(args: dict) -> dict:
    return scoring.score_forecast(
        float(args["actual"]),
        float(args["forecast"]),
        None if args.get("low") is None else float(args["low"]),
        None if args.get("high") is None else float(args["high"]),
    ).as_dict()


def _score_batch(args: dict) -> dict:
    return scoring.score_batch(args["records"])


_QU_OPTIONS = ("lags", "layers", "seed", "backend", "target", "restarts")


def _predict_next(args: dict) -> dict:
    method = args.get("method", "lr")
    options = {k: args[k] for k in _QU_OPTIONS if k in args and args[k] is not None} if method == "qu" else {}
    return predict_next(
        [float(v) for v in args["values"]],
        method=method,
        confidence=float(args.get("confidence", 0.9)),
        **options,
    ).as_dict()


def _backtest(args: dict) -> dict:
    methods = tuple(args.get("methods") or ("lr", "qu"))
    return backtest(
        [float(v) for v in args["values"]],
        methods=methods,
        min_train=int(args.get("min_train", 6)),
        confidence=float(args.get("confidence", 0.9)),
    )


def _ping(_: dict) -> dict:
    return {"engine": "proxora", "tools": sorted(TOOLS)}


TOOLS: dict[str, Callable[[dict], Any]] = {
    "score_forecast": _score_forecast,
    "score_batch": _score_batch,
    "predict_next": _predict_next,
    "backtest": _backtest,
    "ping": _ping,
}


def handle(request: dict) -> dict:
    """Run one request and return the response object (never raises)."""
    request_id = request.get("id")
    tool = request.get("tool")
    if tool not in TOOLS:
        return {"id": request_id, "ok": False, "error": f"Unknown tool {tool!r}; use one of {sorted(TOOLS)}."}
    try:
        result = TOOLS[tool](request.get("args") or {})
    except KeyError as missing:
        return {"id": request_id, "ok": False, "error": f"Missing argument {missing}."}
    except Exception as problem:  # report every engine failure as data, not a crash
        return {"id": request_id, "ok": False, "error": f"{type(problem).__name__}: {problem}"}
    return {"id": request_id, "ok": True, "result": result}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle(request) if isinstance(request, dict) else {
                "id": None, "ok": False, "error": "Request must be a JSON object."}
        except json.JSONDecodeError as problem:
            response = {"id": None, "ok": False, "error": f"Invalid JSON: {problem}"}
        except Exception as problem:  # keep the process alive for the next request
            response = {"id": None, "ok": False, "error": f"{type(problem).__name__}: {problem}"}
        try:
            payload = json.dumps(response, allow_nan=False, default=str)
        except ValueError as problem:  # NaN or infinity cannot be sent as JSON
            payload = json.dumps({"id": response.get("id"), "ok": False, "error": f"Unserialisable result: {problem}"})
        sys.stdout.write(payload + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
