"""Simon's algorithm — finds hidden XOR period s: f(x) = f(x XOR s)."""
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


def _simon_oracle(n: int, s: str) -> QuantumCircuit:
    """Build 2n-qubit oracle for Simon's problem with period s."""
    qc = QuantumCircuit(2 * n)
    # Copy input to output
    for i in range(n):
        qc.cx(i, n + i)
    # XOR with s on the second copy if x[0] == 1
    if s != "0" * n:
        for i, bit in enumerate(reversed(s)):
            if bit == "1":
                qc.cx(0, n + i)
    return qc


def _gaussian_elimination(equations: list[list[int]], n: int) -> str | None:
    """Solve system of equations over GF(2) to recover s."""
    mat = [list(row) for row in equations]
    pivot_cols = []
    row = 0
    for col in range(n):
        pivot = next((r for r in range(row, len(mat)) if mat[r][col] == 1), None)
        if pivot is None:
            continue
        mat[row], mat[pivot] = mat[pivot], mat[row]
        pivot_cols.append(col)
        for r in range(len(mat)):
            if r != row and mat[r][col] == 1:
                mat[r] = [(mat[r][j] ^ mat[row][j]) for j in range(n)]
        row += 1

    free_cols = [c for c in range(n) if c not in pivot_cols]
    if not free_cols:
        return "0" * n

    s = ["0"] * n
    for fc in free_cols:
        s[fc] = "1"
    for r, pc in enumerate(pivot_cols):
        val = 0
        for fc in free_cols:
            val ^= mat[r][fc] * int(s[fc])
        s[pc] = str(val)
    return "".join(s)


def simon(s: str, shots: int = 1024) -> dict:
    """Run Simon's algorithm to recover hidden period s."""
    n = len(s)
    oracle = _simon_oracle(n, s)

    qc = QuantumCircuit(2 * n, n)
    qc.h(range(n))
    qc.compose(oracle, inplace=True)
    qc.h(range(n))
    qc.measure(range(n), range(n))

    sim = AerSimulator()
    counts = sim.run(qc, shots=shots).result().get_counts()

    equations = []
    for bitstr in counts:
        row = [int(b) for b in bitstr.replace(" ", "")]
        if any(row):
            equations.append(row)

    found = _gaussian_elimination(equations, n)
    return {
        "hidden_period": s,
        "recovered": found,
        "success": found == s,
        "equations_collected": len(equations),
    }
