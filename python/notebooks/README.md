# PROXORA Jupyter notebooks

This directory contains exploratory Jupyter workspaces for continuous development of PROXORA.

## Variational quantum learning

Open `variational_quantum_learning.ipynb` to explore the first one-qubit variational experiment from `src/proxora/__init__.py`. The notebook explains the statevector, Born-rule probability, squared-error loss, bounded optimization, and finite-shot sampling in Markdown, then visualizes the probability and loss as Cartesian x-y plots with Matplotlib.

## Environment

Run these commands from the `python/` directory, using the project's configured Python environment:

```bash
uv add --dev jupyterlab ipykernel matplotlib
uv sync
uv run jupyter lab
```

The first command records the notebook tools and plotting library in the project configuration and updates the lockfile. If those dependencies are already declared, do not add them again.

Select the project's Python 3.12+ environment as the notebook kernel. On the Qimono Guix fleet, follow the parent `python/README.md` instructions for the Guix wheel shim before importing NumPy, SciPy, Qiskit, or Qiskit Aer.

Notebook outputs are intentionally not committed by default; run cells in order to reproduce the results and plots.
