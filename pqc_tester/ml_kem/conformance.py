"""
ML-KEM conformance checks against FIPS 203.
Tests byte sizes, API surface, and structural properties of a KEM implementation.
Uses oqs-python (liboqs) if available; otherwise performs size-only checks.
"""
from __future__ import annotations
import os
import hmac
import hashlib
from dataclasses import dataclass, field
from .params import PARAMS, MLKEMParams

try:
    import oqs  # type: ignore
    OQS_AVAILABLE = True
except ImportError:
    OQS_AVAILABLE = False


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ConformanceReport:
    variant: str
    results: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append(TestResult(name, passed, detail))

    def summary(self) -> dict:
        return {
            "variant": self.variant,
            "passed": self.passed,
            "total": len(self.results),
            "failures": [r.name for r in self.results if not r.passed],
            "details": [{"name": r.name, "passed": r.passed, "detail": r.detail}
                        for r in self.results],
        }


class ConformanceTester:
    def __init__(self, variant: str = "ML-KEM-768"):
        if variant not in PARAMS:
            raise ValueError(f"Unknown variant: {variant}. Choose from {list(PARAMS)}")
        self.variant = variant
        self.p: MLKEMParams = PARAMS[variant]

    def run(self) -> ConformanceReport:
        report = ConformanceReport(self.variant)

        if OQS_AVAILABLE:
            self._run_oqs_tests(report)
        else:
            report.add(
                "oqs_availability",
                False,
                "oqs-python not installed. Install liboqs + pip install oqs-python for full tests.",
            )
            self._run_structural_tests(report)

        return report

    def _run_oqs_tests(self, report: ConformanceReport) -> None:
        """Full conformance tests using liboqs."""
        # Map variant name to oqs KEM name
        kem_name = self.variant.replace("-", "_").replace("ML_KEM", "ML-KEM")

        try:
            with oqs.KeyEncapsulation(self.variant) as kem:
                # Key generation
                ek = kem.generate_keypair()
                report.add(
                    "keygen_ek_size",
                    len(ek) == self.p.ek_size,
                    f"expected {self.p.ek_size}, got {len(ek)}",
                )

                dk = kem.export_secret_key()
                report.add(
                    "keygen_dk_size",
                    len(dk) == self.p.dk_size,
                    f"expected {self.p.dk_size}, got {len(dk)}",
                )

                # Encapsulation
                ct, ss_enc = kem.encap_secret(ek)
                report.add(
                    "encap_ct_size",
                    len(ct) == self.p.ct_size,
                    f"expected {self.p.ct_size}, got {len(ct)}",
                )
                report.add(
                    "encap_ss_size",
                    len(ss_enc) == self.p.ss_size,
                    f"expected {self.p.ss_size}, got {len(ss_enc)}",
                )
                report.add(
                    "encap_ss_nonzero",
                    ss_enc != bytes(self.p.ss_size),
                    "shared secret should not be all zeros",
                )

                # Decapsulation
                ss_dec = kem.decap_secret(ct)
                report.add(
                    "decap_ss_matches",
                    ss_enc == ss_dec,
                    "encap and decap shared secrets must match",
                )

                # Implicit rejection: bad ciphertext must yield pseudo-random output
                bad_ct = os.urandom(self.p.ct_size)
                ss_bad = kem.decap_secret(bad_ct)
                report.add(
                    "implicit_rejection_differs",
                    ss_bad != ss_dec,
                    "bad ciphertext must yield different (implicit-rejection) key",
                )
                report.add(
                    "implicit_rejection_not_zero",
                    ss_bad != bytes(self.p.ss_size),
                    "implicit rejection output must not be zero",
                )

                # Shared secret entropy (basic)
                entropy_ok = len(set(ss_enc)) > 16
                report.add(
                    "ss_entropy",
                    entropy_ok,
                    f"unique bytes in ss: {len(set(ss_enc))}",
                )

        except Exception as exc:
            report.add("oqs_error", False, str(exc))

    def _run_structural_tests(self, report: ConformanceReport) -> None:
        """Size-only checks when oqs is not available."""
        p = self.p
        report.add("params_defined", True, str(p))
        report.add(
            "ek_size_spec",
            p.ek_size in {800, 1184, 1568},
            f"ek_size={p.ek_size}",
        )
        report.add(
            "ct_size_spec",
            p.ct_size in {768, 1088, 1568},
            f"ct_size={p.ct_size}",
        )
        report.add("ss_size_spec", p.ss_size == 32, "ss must be 32 bytes")
