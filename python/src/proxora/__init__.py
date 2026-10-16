"""PROXORA: a next-value prediction engine."""

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


def main() -> None:
    """Run the first PROXORA quantum experiment."""
    theta = 0.7

    circuit = QuantumCircuit(1, 1)
    circuit.ry(theta, 0)
    circuit.measure(0, 0)

    simulator = AerSimulator()
    result = simulator.run(circuit, shots=1000, seed_simulator=42).result()
    counts = result.get_counts()

    print("PROXORA: first quantum experiment")
    print(f"Rotation angle: {theta}")
    print(f"Measurement counts: {counts}")
    print(f"Circuit:\n{circuit.draw(output='text')}")


if __name__ == "__main__":
    main()

