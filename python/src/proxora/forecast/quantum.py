"""Variational quantum next-value prediction (a small VQR).

Model
-----
By default the model learns step changes (``target="diff"``): the first
differences of the series are min-max scaled to s in [0, 1], the prediction is
the next change, and it is added to the last value, so a trend can carry on
past the highest price seen. ``target="level"`` models the prices themselves.
Each training example uses the previous ``lags`` scaled values as inputs and
the next scaled value as target, so the model is autoregressive and never
extrapolates a time axis.

The circuit has one qubit per lag and ``layers`` blocks of *data re-uploading*:

    for each layer l:
        Ry(pi * x_i) on qubit i          encode the inputs
        Ry(theta[l, i]) on qubit i       trainable rotation
        CZ between neighbouring qubits   entangle

The readout is the expectation value <Z> of qubit 0, mapped to the target by a
classical affine head: s_hat = w0 + w1 * <Z_0>. For fixed circuit angles the
head has a closed-form least-squares solution, so the classical optimiser only
searches over the circuit angles (a hybrid quantum-classical loop).

Backends
--------
``numpy``  exact statevector simulation written out with NumPy. Ry and CZ keep
           amplitudes real, so this is the same state Qiskit's ``Statevector``
           produces, and it is fast enough to train interactively.
``qiskit`` builds each circuit with Qiskit and evaluates
           ``Statevector(circuit).expectation_value(Z_0)``. Slower; use it to
           cross-check or as the step towards hardware and shot-based runs.

No quantum advantage is claimed: compare against ``lr`` with ``backtest``.
"""

from __future__ import annotations

from math import pi, sqrt

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

from proxora.forecast.types import Prediction


# ---------------------------------------------------------------------------
# Circuit evaluation
# ---------------------------------------------------------------------------


def _apply_ry(state: np.ndarray, qubit: int, angle: float) -> np.ndarray:
    c, s = np.cos(angle / 2), np.sin(angle / 2)
    gate = np.array([[c, -s], [s, c]])
    state = np.tensordot(gate, state, axes=([1], [qubit]))
    return np.moveaxis(state, 0, qubit)


def _apply_cz(state: np.ndarray, a: int, b: int) -> np.ndarray:
    state = state.copy()
    index = [slice(None)] * state.ndim
    index[a] = 1
    index[b] = 1
    state[tuple(index)] *= -1
    return state


def expectation_z0_numpy(inputs: np.ndarray, thetas: np.ndarray) -> float:
    """<Z_0> of the re-uploading circuit, by exact NumPy statevector."""
    n_qubits = len(inputs)
    state = np.zeros((2,) * n_qubits)
    state[(0,) * n_qubits] = 1.0
    for layer in thetas:
        for q in range(n_qubits):
            state = _apply_ry(state, q, pi * inputs[q])
            state = _apply_ry(state, q, layer[q])
        for q in range(n_qubits - 1):
            state = _apply_cz(state, q, q + 1)
    probs = state**2
    return float(probs[0].sum() - probs[1].sum())


def build_circuit(inputs: np.ndarray, thetas: np.ndarray):
    """The same circuit as a Qiskit ``QuantumCircuit`` (requires qiskit)."""
    from qiskit import QuantumCircuit

    n_qubits = len(inputs)
    circuit = QuantumCircuit(n_qubits)
    for layer in thetas:
        for q in range(n_qubits):
            circuit.ry(pi * float(inputs[q]), q)
            circuit.ry(float(layer[q]), q)
        for q in range(n_qubits - 1):
            circuit.cz(q, q + 1)
    return circuit


def expectation_z0_qiskit(inputs: np.ndarray, thetas: np.ndarray) -> float:
    """<Z_0> of the re-uploading circuit, evaluated with Qiskit."""
    from qiskit.quantum_info import SparsePauliOp, Statevector

    circuit = build_circuit(inputs, thetas)
    z0 = SparsePauliOp.from_sparse_list([("Z", [0], 1.0)], num_qubits=len(inputs))
    return float(np.real(Statevector(circuit).expectation_value(z0)))


_BACKENDS = {"numpy": expectation_z0_numpy, "qiskit": expectation_z0_qiskit}


# ---------------------------------------------------------------------------
# Training and prediction
# ---------------------------------------------------------------------------


def _windows(scaled: np.ndarray, lags: int) -> tuple[np.ndarray, np.ndarray]:
    xs = np.array([scaled[i : i + lags] for i in range(len(scaled) - lags)])
    ys = scaled[lags:]
    return xs, ys


def _head(z: np.ndarray, ys: np.ndarray) -> tuple[float, float]:
    """Closed-form least-squares affine head ys ~ w0 + w1 * z."""
    design = np.column_stack([np.ones_like(z), z])
    (w0, w1), *_ = np.linalg.lstsq(design, ys, rcond=None)
    return float(w0), float(w1)


def predict_next_quantum(
    values: list[float],
    confidence: float = 0.9,
    lags: int = 2,
    layers: int = 2,
    restarts: int = 3,
    seed: int = 42,
    backend: str = "numpy",
    maxiter: int = 300,
    target: str = "diff",
) -> Prediction:
    """Train the variational regressor on ``values`` and predict the next value."""
    if backend not in _BACKENDS:
        raise ValueError(f"Unknown backend {backend!r}; use one of {sorted(_BACKENDS)}.")
    if lags < 1 or layers < 1:
        raise ValueError("lags and layers must be at least 1.")
    if target not in ("diff", "level"):
        raise ValueError("target must be 'diff' (model step changes) or 'level' (model prices).")
    values = np.asarray(values, dtype=float)
    n = len(values)
    needed = lags + 3 + (1 if target == "diff" else 0)
    if n < needed:
        raise ValueError(f"The quantum regressor needs at least {needed} values here; got {n}.")

    expectation = _BACKENDS[backend]
    last = float(values[-1])
    # "diff" learns the next step change and adds it to the last value, so a
    # trend can continue past the highest price seen; "level" learns prices.
    series = np.diff(values) if target == "diff" else values
    base = last if target == "diff" else 0.0
    lo, hi = float(series.min()), float(series.max())
    span = hi - lo
    if span == 0:
        point = base + lo
        return Prediction("qu", point, point, point, confidence, n, {"note": "constant series", "target": target})

    scaled = (series - lo) / span
    xs, ys = _windows(scaled, lags)

    def readouts(thetas: np.ndarray, inputs: np.ndarray) -> np.ndarray:
        return np.array([expectation(x, thetas) for x in inputs])

    def loss(flat: np.ndarray) -> float:
        thetas = flat.reshape(layers, lags)
        z = readouts(thetas, xs)
        w0, w1 = _head(z, ys)
        return float(np.mean((w0 + w1 * z - ys) ** 2))

    rng = np.random.default_rng(seed)
    best = None
    for _ in range(restarts):
        start = rng.uniform(0, 2 * pi, size=layers * lags)
        result = minimize(loss, start, method="COBYLA", options={"maxiter": maxiter})
        if best is None or result.fun < best.fun:
            best = result

    thetas = best.x.reshape(layers, lags)
    z = readouts(thetas, xs)
    w0, w1 = _head(z, ys)

    next_inputs = scaled[-lags:]
    z_next = expectation(next_inputs, thetas)
    point = base + lo + span * (w0 + w1 * z_next)

    residuals = (w0 + w1 * z - ys) * span
    m = len(ys)
    n_params = layers * lags + 2
    in_sample_rmse = float(sqrt(np.mean(residuals**2)))
    # Inflate the in-sample error for the parameters spent fitting it.
    spread = in_sample_rmse * sqrt(m / max(m - n_params, 1))
    half_width = float(norm.ppf(1 - (1 - confidence) / 2)) * spread

    return Prediction(
        method="qu",
        value=float(point),
        low=float(point - half_width),
        high=float(point + half_width),
        confidence=confidence,
        n_observations=n,
        details={
            "backend": backend,
            "target": target,
            "lags": lags,
            "layers": layers,
            "qubits": lags,
            "trained_thetas": thetas.tolist(),
            "head": {"w0": w0, "w1": w1},
            "train_loss_scaled_mse": float(best.fun),
            "in_sample_rmse": in_sample_rmse,
            "seed": seed,
        },
    )
