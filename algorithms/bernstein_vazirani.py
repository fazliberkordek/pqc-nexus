"""Bernstein-Vazirani algorithm — recovers hidden bitstring s from f(x) = s·x mod 2."""
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


def _bv_oracle(n: int, secret: str) -> QuantumCircuit:
    qc = QuantumCircuit(n + 1)
    for i, bit in enumerate(reversed(secret)):
        if bit == "1":
            qc.cx(i, n)
    return qc


def bernstein_vazirani(secret: str) -> dict:
    """
    Recover secret bitstring using a single query.
    secret: binary string e.g. '1011'
    """
    n = len(secret)
    oracle = _bv_oracle(n, secret)

    qc = QuantumCircuit(n + 1, n)
    qc.x(n)
    qc.h(range(n + 1))
    qc.compose(oracle, inplace=True)
    qc.h(range(n))
    qc.measure(range(n), range(n))

    sim = AerSimulator()
    counts = sim.run(qc, shots=1).result().get_counts()
    found = list(counts.keys())[0].replace(" ", "")
    return {
        "secret": secret,
        "found": found,
        "success": found == secret,
    }
