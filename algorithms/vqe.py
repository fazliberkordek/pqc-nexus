"""
VQE — Variational Quantum Eigensolver.
Finds ground state energy of H2 molecule using a hardware-efficient ansatz.
"""
import numpy as np
from scipy.optimize import minimize
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector


# H2 Hamiltonian in STO-3G basis (qubit-mapped, frozen core)
# Coefficients from Jordan-Wigner transform at equilibrium bond length
_H2_HAMILTONIAN = SparsePauliOp.from_list([
    ("II", -1.0523732),
    ("IZ",  0.3979374),
    ("ZI", -0.3979374),
    ("ZZ", -0.0112801),
    ("XX",  0.1809312),
])

_H2_EXACT_ENERGY = -1.8572750  # Hartree, FCI reference


def _ansatz(params: np.ndarray) -> QuantumCircuit:
    """Hardware-efficient 2-qubit ansatz with Ry rotations and CNOT."""
    qc = QuantumCircuit(2)
    qc.ry(params[0], 0)
    qc.ry(params[1], 1)
    qc.cx(0, 1)
    qc.ry(params[2], 0)
    qc.ry(params[3], 1)
    return qc


def _energy(params: np.ndarray) -> float:
    """Compute ⟨ψ|H|ψ⟩ via exact statevector."""
    sv = Statevector(_ansatz(params))
    return float(sv.expectation_value(_H2_HAMILTONIAN).real)


def vqe_h2(max_iter: int = 200) -> dict:
    """Run VQE to find ground state energy of H2."""
    rng = np.random.default_rng(42)
    x0 = rng.uniform(0, 2 * np.pi, 4)

    result = minimize(_energy, x0, method="COBYLA", options={"maxiter": max_iter})
    estimated = result.fun
    error = abs(estimated - _H2_EXACT_ENERGY)

    return {
        "molecule": "H2",
        "estimated_energy_hartree": round(estimated, 6),
        "exact_energy_hartree": _H2_EXACT_ENERGY,
        "absolute_error": round(error, 6),
        "chemical_accuracy": error < 1.6e-3,  # 1 kcal/mol threshold
        "optimizer_iterations": result.nfev,
        "converged": result.success,
    }
