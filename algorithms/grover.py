"""Grover's algorithm — quadratic speedup for unstructured search."""
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


def _phase_oracle(n: int, target: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    bits = format(target, f"0{n}b")
    # Flip qubits where target bit is 0
    for i, b in enumerate(reversed(bits)):
        if b == "0":
            qc.x(i)
    # Multi-controlled Z via H + MCX + H on last qubit
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    for i, b in enumerate(reversed(bits)):
        if b == "0":
            qc.x(i)
    return qc


def _diffuser(n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    qc.h(range(n))
    qc.x(range(n))
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    qc.x(range(n))
    qc.h(range(n))
    return qc


def grover_search(n: int, target: int, shots: int = 1024) -> dict:
    """
    Search for target in an unsorted space of size 2^n.
    Optimal iterations ≈ π/4 * sqrt(2^n).
    """
    iterations = max(1, round(np.pi / 4 * np.sqrt(2**n)))
    qc = QuantumCircuit(n, n)
    qc.h(range(n))
    for _ in range(iterations):
        qc.compose(_phase_oracle(n, target), inplace=True)
        qc.compose(_diffuser(n), inplace=True)
    qc.measure(range(n), range(n))

    sim = AerSimulator()
    counts = sim.run(qc, shots=shots).result().get_counts()
    top = max(counts, key=counts.get)
    found = int(top.replace(" ", ""), 2)
    return {
        "n_qubits": n,
        "search_space": 2**n,
        "target": target,
        "found": found,
        "success": found == target,
        "iterations": iterations,
        "top_probability": counts[top] / shots,
    }
