# QAOA Max-Cut in pyQuil

A small, inspectable QAOA (Quantum Approximate Optimization Algorithm) for Max-Cut on a 4-node ring, written in **pyQuil / Quil** for Rigetti's stack. It follows the Proxora rule: classical and quantum side by side, same problem, same score.

```
0 ─── 1
│     │
3 ─── 2        max cut = 4  (0101 or 1010)
```

## Files

| file | what it is | needs |
|---|---|---|
| `maxcut.py` | classical brute force + exact NumPy model of the QAOA circuit | numpy |
| `qaoa_pyquil.py` | the same circuit as a parametric Quil program, sampled on the QVM | pyquil 4.x, quilc, qvm |
| `test_maxcut.py` | checks the reference math | numpy, scipy |

## The circuit

Start in `|+>^4`, then for each layer k:

* phase separator `exp(-i γ Σ Z_i Z_j)`, built per edge as `CNOT(i,j) · RZ(2γ) on j · CNOT(i,j)`
* mixer `exp(-i β X)` on every qubit, i.e. `RX(2β)`

Then measure. The angles `gamma[k]`, `beta[k]` are declared as Quil classical memory, so the program is compiled once and rerun with new angles through `memory_map`. That is how a hybrid loop on QCS would work too.

Conventions: qubit `q` is bit `q` (pyQuil `ro[q]`), bit 0 means z = +1.

## Run

```bash
# reference math, no quantum SDK needed
python -m unittest -v test_maxcut

# pyQuil on the local QVM
docker run --rm -it -p 5555:5555 rigetti/quilc -S
docker run --rm -it -p 5000:5000 rigetti/qvm -S
pip install pyquil
python qaoa_pyquil.py --print-quil   # see the Quil
python qaoa_pyquil.py --shots 5000
```

## What to expect

| | value |
|---|---|
| classical brute force | 4 |
| random guess (`γ = β = 0`) | `<C>` = 2 |
| ideal QAOA p = 1 | `<C>` ≈ 3.00 (ratio 3/4, the known p = 1 result for ring graphs) |
| ideal QAOA p = 2 | `<C>` ≈ 4.00 (reaches the optimum) |
| QVM p = 1, finite shots | ≈ 3, within shot noise |

## Honest scope

* 4 nodes: brute force wins trivially. No quantum advantage is claimed or implied.
* `maxcut.py` and `test_maxcut.py` were run. `qaoa_pyquil.py` was written against the pyQuil 4 API but not yet executed against a live QVM. First run on a machine with quilc/qvm is the real check.
* Next steps: optimizer loop over `memory_map` (p = 2), a Qiskit twin of the same circuit to compare SDKs, then a QPU run on Rigetti QCS.
