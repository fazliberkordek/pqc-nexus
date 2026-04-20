"""
BB84 Quantum Key Distribution — simulate the full protocol including
eavesdropping detection via QBER (Quantum Bit Error Rate).
"""
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


def _encode_bit(bit: int, basis: int) -> QuantumCircuit:
    """Encode one bit in Z-basis (0) or X-basis (1)."""
    qc = QuantumCircuit(1, 1)
    if bit == 1:
        qc.x(0)
    if basis == 1:  # X-basis
        qc.h(0)
    return qc


def _measure_bit(basis: int) -> QuantumCircuit:
    """Measure in Z-basis (0) or X-basis (1)."""
    qc = QuantumCircuit(1, 1)
    if basis == 1:
        qc.h(0)
    qc.measure(0, 0)
    return qc


def bb84_qkd(
    n_bits: int = 256,
    eavesdrop: bool = False,
    rng_seed: int | None = None,
) -> dict:
    """
    Simulate BB84 QKD between Alice and Bob (with optional Eve).

    Returns sifted key, QBER, and whether eavesdropping was detected.
    """
    rng = np.random.default_rng(rng_seed)
    sim = AerSimulator()

    alice_bits = rng.integers(0, 2, n_bits)
    alice_bases = rng.integers(0, 2, n_bits)
    bob_bases = rng.integers(0, 2, n_bits)

    bob_results = []
    for i in range(n_bits):
        # Alice encodes
        enc = _encode_bit(int(alice_bits[i]), int(alice_bases[i]))

        # Optional Eve: measure in random basis then re-encode
        if eavesdrop:
            eve_basis = int(rng.integers(0, 2))
            eve_meas = enc.compose(_measure_bit(eve_basis))
            job = sim.run(eve_meas, shots=1)
            eve_bit = int(list(job.result().get_counts().keys())[0])
            enc = _encode_bit(eve_bit, eve_basis)

        # Bob measures
        full = enc.compose(_measure_bit(int(bob_bases[i])))
        job = sim.run(full, shots=1)
        bob_results.append(int(list(job.result().get_counts().keys())[0]))

    bob_bits = np.array(bob_results)

    # Sift: keep positions where bases match
    matching = alice_bases == bob_bases
    alice_sifted = alice_bits[matching]
    bob_sifted = bob_bits[matching]

    # QBER on first 25% of sifted key (sacrificed for check)
    check_n = max(1, len(alice_sifted) // 4)
    qber = float(np.mean(alice_sifted[:check_n] != bob_sifted[:check_n]))

    final_key = alice_sifted[check_n:].tolist()
    return {
        "n_bits_sent": n_bits,
        "sifted_key_length": len(alice_sifted) - check_n,
        "final_key": final_key,
        "qber": round(qber, 4),
        "eavesdrop_simulated": eavesdrop,
        "eavesdropping_detected": qber > 0.11,  # threshold: ~11% QBER with Eve
    }
