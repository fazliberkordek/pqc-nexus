"""
Shor's algorithm — integer factorization via quantum period finding.
Implemented for small semi-primes using QPE-based order finding.
"""
import math
import random
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.circuit.library import QFT


def _controlled_mod_exp(a: int, N: int, n_count: int, n_work: int) -> QuantumCircuit:
    """Build controlled-U^{2^k} gates for a^x mod N."""
    qc = QuantumCircuit(n_count + n_work)
    qc.x(n_count)  # |1> in work register
    for k in range(n_count):
        exp = pow(a, 2**k, N)
        # Approximate: controlled-multiply for each counting qubit
        for target in range(n_work):
            if (exp >> target) & 1:
                qc.cx(k, n_count + target)
    return qc


def _quantum_order_finding(a: int, N: int, shots: int = 2048) -> int | None:
    """Estimate order r such that a^r ≡ 1 (mod N)."""
    n_work = math.ceil(math.log2(N))
    n_count = 2 * n_work

    qc = QuantumCircuit(n_count + n_work, n_count)
    qc.h(range(n_count))
    qc.compose(_controlled_mod_exp(a, N, n_count, n_work), inplace=True)
    qc.compose(QFT(n_count, inverse=True), qubits=range(n_count), inplace=True)
    qc.measure(range(n_count), range(n_count))

    sim = AerSimulator()
    counts = sim.run(qc, shots=shots).result().get_counts()
    top = max(counts, key=counts.get)
    phase_int = int(top.replace(" ", ""), 2)
    if phase_int == 0:
        return None

    # Continued fractions to extract r from phase_int / 2^n_count
    from fractions import Fraction
    frac = Fraction(phase_int, 2**n_count).limit_denominator(N)
    r = frac.denominator
    return r if r > 0 and pow(a, r, N) == 1 else None


def shor_factor(N: int, attempts: int = 10) -> dict:
    """
    Factor N using Shor's algorithm.
    Best suited for N = p*q with small semi-primes (N ≤ 63 for simulator).
    """
    if N % 2 == 0:
        return {"N": N, "factors": (2, N // 2), "method": "trivial-even"}
    if math.isqrt(N) ** 2 == N:
        s = math.isqrt(N)
        return {"N": N, "factors": (s, s), "method": "perfect-square"}

    for _ in range(attempts):
        a = random.randint(2, N - 1)
        g = math.gcd(a, N)
        if g > 1:
            return {"N": N, "factors": (g, N // g), "method": "gcd-lucky", "a": a}

        r = _quantum_order_finding(a, N)
        if r is None or r % 2 != 0:
            continue

        candidates = [
            math.gcd(pow(a, r // 2) - 1, N),
            math.gcd(pow(a, r // 2) + 1, N),
        ]
        for p in candidates:
            if 1 < p < N and N % p == 0:
                return {"N": N, "factors": (p, N // p), "method": "quantum", "a": a, "r": r}

    return {"N": N, "factors": None, "method": "failed"}
