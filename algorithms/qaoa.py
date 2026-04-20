"""
QAOA — Quantum Approximate Optimization Algorithm.
Solves MaxCut on a weighted graph using p-layer QAOA.
"""
import numpy as np
from scipy.optimize import minimize
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, SparsePauliOp


def _build_cost_operator(edges: list[tuple[int, int, float]], n: int) -> SparsePauliOp:
    """MaxCut cost: C = sum_{(i,j)} w_{ij}/2 * (I - Z_i Z_j)."""
    terms = []
    for i, j, w in edges:
        zi_zj = ["I"] * n
        zi_zj[i] = "Z"
        zi_zj[j] = "Z"
        terms.append(("".join(reversed(zi_zj)), -w / 2))
        terms.append(("I" * n, w / 2))
    return SparsePauliOp.from_list(terms)


def _qaoa_circuit(gamma: list[float], beta: list[float],
                  edges: list[tuple[int, int, float]], n: int) -> QuantumCircuit:
    p = len(gamma)
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for layer in range(p):
        # Cost layer
        for i, j, w in edges:
            qc.cx(i, j)
            qc.rz(2 * gamma[layer] * w, j)
            qc.cx(i, j)
        # Mixer layer
        qc.rx(2 * beta[layer], range(n))
    return qc


def qaoa_maxcut(
    edges: list[tuple[int, int, float]] | None = None,
    n_nodes: int = 4,
    p: int = 2,
) -> dict:
    """
    Run QAOA for MaxCut.
    edges: list of (node_i, node_j, weight). Defaults to a 4-node cycle.
    p: number of QAOA layers.
    """
    if edges is None:
        edges = [(0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0), (3, 0, 1.0)]
        n_nodes = 4

    cost_op = _build_cost_operator(edges, n_nodes)

    def objective(params: np.ndarray) -> float:
        gamma = params[:p]
        beta = params[p:]
        qc = _qaoa_circuit(gamma, beta, edges, n_nodes)
        sv = Statevector(qc)
        return -float(sv.expectation_value(cost_op).real)

    rng = np.random.default_rng(0)
    x0 = rng.uniform(0, np.pi, 2 * p)
    result = minimize(objective, x0, method="COBYLA", options={"maxiter": 500})

    # Get best bitstring
    gamma_opt = result.x[:p]
    beta_opt = result.x[p:]
    qc_opt = _qaoa_circuit(gamma_opt, beta_opt, edges, n_nodes)
    sv = Statevector(qc_opt)
    probs = np.abs(sv.data) ** 2
    best_idx = int(np.argmax(probs))
    best_cut = format(best_idx, f"0{n_nodes}b")

    # Compute actual cut value
    cut_value = sum(
        w for i, j, w in edges
        if best_cut[n_nodes - 1 - i] != best_cut[n_nodes - 1 - j]
    )

    return {
        "n_nodes": n_nodes,
        "edges": edges,
        "p_layers": p,
        "best_cut_bitstring": best_cut,
        "cut_value": cut_value,
        "expected_cost": round(-result.fun, 4),
        "optimal_params": {"gamma": gamma_opt.tolist(), "beta": beta_opt.tolist()},
    }
