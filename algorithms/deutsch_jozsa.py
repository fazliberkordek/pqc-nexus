"""Deutsch-Jozsa algorithm — determines if f:{0,1}^n→{0,1} is constant or balanced."""
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


def constant_oracle(n: int) -> QuantumCircuit:
    """Oracle for constant f(x) = 0."""
    return QuantumCircuit(n + 1)


def balanced_oracle(n: int) -> QuantumCircuit:
    """Oracle for balanced f(x) = x_0 XOR x_1 XOR ... XOR x_{n-1}."""
    qc = QuantumCircuit(n + 1)
    for i in range(n):
        qc.cx(i, n)
    return qc


def deutsch_jozsa(oracle: QuantumCircuit, n: int) -> dict:
    """
    Run Deutsch-Jozsa. Returns verdict: 'constant' or 'balanced'.
    oracle must act on n+1 qubits (n input + 1 ancilla).
    """
    qc = QuantumCircuit(n + 1, n)
    qc.x(n)
    qc.h(range(n + 1))
    qc.compose(oracle, inplace=True)
    qc.h(range(n))
    qc.measure(range(n), range(n))

    sim = AerSimulator()
    counts = sim.run(qc, shots=1).result().get_counts()
    result_bits = list(counts.keys())[0].replace(" ", "")
    verdict = "constant" if result_bits == "0" * n else "balanced"
    return {"verdict": verdict, "measurement": result_bits}
