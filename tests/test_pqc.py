"""Tests for ML-KEM conformance and parameter correctness."""
import pytest
from pqc_tester.ml_kem.params import PARAMS, MLKEMVariant
from pqc_tester.ml_kem.conformance import ConformanceTester
from pqc_tester.ml_kem.test_vectors import get_vectors


@pytest.mark.parametrize("variant", ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"])
def test_params_sizes(variant):
    p = PARAMS[variant]
    assert p.ss_size == 32
    assert p.ek_size in {800, 1184, 1568}
    assert p.ct_size in {768, 1088, 1568}
    assert p.dk_size > p.ek_size


def test_ml_kem_512_params():
    p = PARAMS["ML-KEM-512"]
    assert p.k == 2
    assert p.ek_size == 800
    assert p.ct_size == 768
    assert p.dk_size == 1632


def test_ml_kem_768_params():
    p = PARAMS["ML-KEM-768"]
    assert p.k == 3
    assert p.ek_size == 1184
    assert p.ct_size == 1088
    assert p.dk_size == 2400


def test_ml_kem_1024_params():
    p = PARAMS["ML-KEM-1024"]
    assert p.k == 4
    assert p.ek_size == 1568
    assert p.ct_size == 1568
    assert p.dk_size == 3168


@pytest.mark.parametrize("variant", list(MLKEMVariant))
def test_conformance_structural(variant):
    """Structural conformance runs without oqs; checks params are sane."""
    tester = ConformanceTester(variant.value)
    report = tester.run()
    summary = report.summary()
    assert "variant" in summary
    assert "passed" in summary
    # If oqs not available, structural checks should pass
    structural_failures = [f for f in summary["failures"]
                           if not f.startswith("oqs")]
    assert structural_failures == [], f"Structural failures: {structural_failures}"


def test_test_vectors_exist():
    for variant in ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"]:
        vecs = get_vectors(variant)
        assert len(vecs) >= 1, f"No test vectors for {variant}"


def test_test_vector_sizes():
    for variant in ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"]:
        p = PARAMS[variant]
        for v in get_vectors(variant):
            assert v["ek_size"] == p.ek_size
            assert v["ct_size"] == p.ct_size
            assert v["ss_size"] == 32
