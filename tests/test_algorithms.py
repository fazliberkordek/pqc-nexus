"""Smoke tests for all quantum algorithm implementations."""
import pytest
import numpy as np
from algorithms import (
    deutsch_jozsa, constant_oracle, balanced_oracle,
    bernstein_vazirani,
    simon,
    grover_search,
    qft_circuit,
    quantum_phase_estimation,
    teleport,
    bb84_qkd,
    vqe_h2,
    qaoa_maxcut,
    hhl_solve,
)


def test_deutsch_jozsa_constant():
    oracle = constant_oracle(3)
    result = deutsch_jozsa(oracle, 3)
    assert result["verdict"] == "constant"


def test_deutsch_jozsa_balanced():
    oracle = balanced_oracle(3)
    result = deutsch_jozsa(oracle, 3)
    assert result["verdict"] == "balanced"


def test_bernstein_vazirani():
    for secret in ["101", "1100", "0110"]:
        result = bernstein_vazirani(secret)
        assert result["success"], f"Failed to recover secret={secret}, got {result['found']}"


def test_simon_trivial():
    result = simon("000", shots=512)
    assert result["recovered"] is not None


def test_grover_small():
    for target in [0, 3, 5, 7]:
        result = grover_search(n=3, target=target, shots=2048)
        assert result["success"], f"Grover failed: target={target} found={result['found']}"


def test_grover_result_structure():
    result = grover_search(n=3, target=4)
    assert "search_space" in result
    assert result["search_space"] == 8
    assert 1 <= result["iterations"] <= 3


def test_qft_returns_statevector():
    result = qft_circuit(3)
    assert result.num_qubits == 3


def test_qpe_accuracy():
    for phase in [0.25, 0.5, 0.125]:
        result = quantum_phase_estimation(phase, n_counting=4)
        assert result["error"] < result["resolution"] + 0.05, \
            f"QPE error too large for phase={phase}"


def test_teleportation_completes():
    result = teleport()
    assert result["teleported"] is True
    assert "cbits_distribution" in result


def test_teleportation_custom_state():
    result = teleport(alpha=1.0, beta=0.0)
    assert result["teleported"]


def test_bb84_no_eavesdrop():
    result = bb84_qkd(n_bits=64, eavesdrop=False, rng_seed=42)
    assert result["qber"] < 0.05
    assert not result["eavesdropping_detected"]
    assert len(result["final_key"]) > 0


def test_bb84_eavesdrop_detected():
    result = bb84_qkd(n_bits=256, eavesdrop=True, rng_seed=0)
    assert result["eavesdropping_detected"], \
        f"Eavesdropping not detected, QBER={result['qber']}"


def test_vqe_structure():
    result = vqe_h2(max_iter=50)
    assert "estimated_energy_hartree" in result
    assert result["estimated_energy_hartree"] < 0, "H2 ground state energy must be negative"


def test_qaoa_maxcut_returns_cut():
    result = qaoa_maxcut(p=1)
    assert result["cut_value"] >= 0
    assert len(result["best_cut_bitstring"]) == result["n_nodes"]


def test_hhl_classical_match():
    import numpy as np
    A = np.array([[2.0, 0.0], [0.0, 1.0]])
    b = np.array([1.0, 1.0])
    result = hhl_solve(A, b)
    x = np.array(result["x_classical"])
    assert np.allclose(A @ x, b, atol=1e-6)
