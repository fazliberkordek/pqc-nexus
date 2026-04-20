"""Quantum Phase Estimation — estimate eigenphase θ of unitary U|ψ⟩ = e^{2πiθ}|ψ⟩."""
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.circuit.library import QFT


def quantum_phase_estimation(phase: float, n_counting: int = 4, shots: int = 2048) -> dict:
    """
    Estimate a known phase θ ∈ [0,1) using n_counting ancilla qubits.
    Uses R_z rotation as the unitary U (eigenphase = phase).
    """
    qc = QuantumCircuit(n_counting + 1, n_counting)

    # Prepare eigenstate |+⟩ of Rz (for demo: use |0⟩ with phase kick)
    qc.h(n_counting)

    # Hadamard on counting qubits
    qc.h(range(n_counting))

    # Apply controlled-U^{2^k}: controlled-Rz(2*pi*phase * 2^k)
    for k in range(n_counting):
        angle = 2 * np.pi * phase * (2**k)
        qc.cp(angle, k, n_counting)

    # Inverse QFT on counting register
    iqft = QFT(n_counting, inverse=True)
    qc.compose(iqft, qubits=range(n_counting), inplace=True)
    qc.measure(range(n_counting), range(n_counting))

    sim = AerSimulator()
    counts = sim.run(qc, shots=shots).result().get_counts()
    top = max(counts, key=counts.get)
    measured_int = int(top.replace(" ", ""), 2)
    estimated_phase = measured_int / (2**n_counting)

    return {
        "true_phase": phase,
        "estimated_phase": estimated_phase,
        "error": abs(phase - estimated_phase),
        "n_counting_qubits": n_counting,
        "resolution": 1 / (2**n_counting),
        "counts": dict(sorted(counts.items(), key=lambda x: -x[1])[:5]),
    }
