"""Quantum Fourier Transform — building block for QPE and Shor's."""
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector


def qft_circuit(n: int, inverse: bool = False) -> QuantumCircuit:
    """Build n-qubit QFT circuit (or inverse QFT)."""
    qc = QuantumCircuit(n)
    for j in range(n - 1, -1, -1):
        qc.h(j)
        for k in range(j - 1, -1, -1):
            angle = np.pi / (2 ** (j - k))
            qc.cp(angle, k, j)
    # Swap qubits to match standard bit ordering
    for i in range(n // 2):
        qc.swap(i, n - i - 1)
    if inverse:
        qc = qc.inverse()
        qc.name = "IQFT"
    else:
        qc.name = "QFT"
    return qc


def run_qft(input_state: list[complex] | None = None, n: int = 3) -> dict:
    """
    Run QFT on n qubits.
    input_state: optional statevector of length 2^n.
    Defaults to uniform superposition.
    """
    if input_state is not None:
        n = int(np.log2(len(input_state)))

    qc = QuantumCircuit(n)
    if input_state is not None:
        qc.initialize(input_state)
    else:
        qc.h(range(n))  # uniform superposition

    qft = qft_circuit(n)
    qc.compose(qft, inplace=True)

    sv = Statevector(qc)
    return {
        "n_qubits": n,
        "output_statevector": sv.data.tolist(),
        "amplitudes": np.abs(sv.data).tolist(),
    }
