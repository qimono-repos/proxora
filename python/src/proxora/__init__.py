"""PROXORA: a next-value prediction engine."""

import sys
from math import pi

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from scipy.optimize import minimize_scalar


TARGET_PROBABILITY = 0.8
SHOTS = 1000

USAGE = (
    "Usage: proxora -qu\n"
    "  -qu  Run the Python/Qiskit variational quantum implementation"
)


def usage() -> None:
    """Print the command-line usage message to stderr."""
    print(USAGE, file=sys.stderr)


def probability_of_one(theta: float) -> float:
    """Return the ideal probability of measuring |1> after an Ry(theta) gate."""
    circuit = QuantumCircuit(1)
    circuit.ry(theta, 0)

    state = Statevector.from_instruction(circuit)
    return float(abs(state.data[1]) ** 2)


def run_quantum_regression() -> None:
    """Train one circuit parameter to match a target probability."""
    initial_theta = 0.7

    def loss(theta: float) -> float:
        error = probability_of_one(theta) - TARGET_PROBABILITY
        return error**2

    initial_probability = probability_of_one(initial_theta)
    result = minimize_scalar(
        loss,
        bounds=(0.0, pi),
        method="bounded",
        options={"xatol": 1e-8},
    )
    trained_theta = float(result.x)
    trained_probability = probability_of_one(trained_theta)

    circuit = QuantumCircuit(1, 1)
    circuit.ry(trained_theta, 0)
    circuit.measure(0, 0)

    simulator = AerSimulator()
    counts = simulator.run(
        circuit,
        shots=SHOTS,
        seed_simulator=42,
    ).result().get_counts()

    measured_probability = counts.get("1", 0) / SHOTS

    print("PROXORA: variational quantum learning, first step")
    print(f"Target probability P(1): {TARGET_PROBABILITY:.3f}")
    print(f"Initial theta: {initial_theta:.6f}")
    print(f"Initial ideal P(1): {initial_probability:.6f}")
    print(f"Trained theta: {trained_theta:.6f}")
    print(f"Trained ideal P(1): {trained_probability:.6f}")
    print(f"Final loss: {result.fun:.8f}")
    print(f"Measured counts ({SHOTS} shots): {counts}")
    print(f"Measured P(1): {measured_probability:.3f}")
    print(f"Circuit:\n{circuit.draw(output='text')}")


def main(argv: list[str] | None = None) -> int:
    """Dispatch the PROXORA command line and return the process exit status."""
    args = list(sys.argv[1:] if argv is None else argv)

    if args == ["-qu"]:
        run_quantum_regression()
        return 0

    usage()
    return 2


if __name__ == "__main__":
    sys.exit(main())
