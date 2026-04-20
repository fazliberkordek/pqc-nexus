"""
PQC attack probe suite.
Tests whether an ML-KEM implementation correctly handles adversarial inputs.
These are protocol-level and structural probes — not key-recovery attacks.
"""
from __future__ import annotations
import os
import time
import statistics
from dataclasses import dataclass, field
from .params import PARAMS

try:
    import oqs  # type: ignore
    OQS_AVAILABLE = True
except ImportError:
    OQS_AVAILABLE = False


@dataclass
class ProbeResult:
    name: str
    passed: bool
    detail: str = ""
    timing_ms: float | None = None


@dataclass
class AttackReport:
    variant: str
    probes: list[ProbeResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(p.passed for p in self.probes)

    def summary(self) -> dict:
        return {
            "variant": self.variant,
            "all_passed": self.passed,
            "probes": [
                {
                    "name": p.name,
                    "passed": p.passed,
                    "detail": p.detail,
                    "timing_ms": p.timing_ms,
                }
                for p in self.probes
            ],
        }


class AttackSuite:
    def __init__(self, variant: str = "ML-KEM-768"):
        self.variant = variant
        self.p = PARAMS[variant]

    def run(self) -> AttackReport:
        report = AttackReport(self.variant)
        if not OQS_AVAILABLE:
            report.probes.append(ProbeResult(
                "oqs_required", False,
                "oqs-python required for attack probes. pip install oqs-python",
            ))
            return report

        with oqs.KeyEncapsulation(self.variant) as kem:
            ek = kem.generate_keypair()
            ct_valid, ss_valid = kem.encap_secret(ek)

            self._probe_wrong_size_ct(kem, report)
            self._probe_all_zeros_ct(kem, ct_valid, ss_valid, report)
            self._probe_bit_flip_ct(kem, ct_valid, ss_valid, report)
            self._probe_replay(kem, ct_valid, ss_valid, report)
            self._probe_timing_consistency(kem, ct_valid, report)
            self._probe_ss_reuse(kem, ek, report)

        return report

    def _probe_wrong_size_ct(self, kem, report: AttackReport) -> None:
        """Wrong-size ciphertext must not crash or return valid-looking output."""
        for bad_size in [0, self.p.ct_size - 1, self.p.ct_size + 1, 32]:
            bad_ct = os.urandom(bad_size) if bad_size > 0 else b""
            try:
                ss = kem.decap_secret(bad_ct)
                passed = len(ss) == self.p.ss_size  # implicit rejection
                report.probes.append(ProbeResult(
                    f"wrong_size_ct_{bad_size}B", passed,
                    "implicit rejection with correct ss size" if passed else "unexpected output",
                ))
            except Exception as exc:
                report.probes.append(ProbeResult(
                    f"wrong_size_ct_{bad_size}B", True,
                    f"raised exception (acceptable): {type(exc).__name__}",
                ))

    def _probe_all_zeros_ct(self, kem, ct_valid: bytes, ss_valid: bytes,
                            report: AttackReport) -> None:
        """All-zero ciphertext must yield implicit-rejection key (not the real ss)."""
        zero_ct = bytes(self.p.ct_size)
        ss_zero = kem.decap_secret(zero_ct)
        report.probes.append(ProbeResult(
            "all_zeros_ct_rejection",
            ss_zero != ss_valid,
            "all-zero ct correctly rejected" if ss_zero != ss_valid else "FAIL: same ss returned!",
        ))

    def _probe_bit_flip_ct(self, kem, ct_valid: bytes, ss_valid: bytes,
                           report: AttackReport) -> None:
        """Single bit-flip must trigger implicit rejection."""
        ct_list = bytearray(ct_valid)
        ct_list[0] ^= 0x01
        ss_flipped = kem.decap_secret(bytes(ct_list))
        report.probes.append(ProbeResult(
            "bit_flip_ct_rejection",
            ss_flipped != ss_valid,
            "bit-flip correctly rejected" if ss_flipped != ss_valid else "FAIL: same ss!",
        ))

    def _probe_replay(self, kem, ct_valid: bytes, ss_valid: bytes,
                      report: AttackReport) -> None:
        """Replayed ciphertext should still decapsulate to same ss (KEM is deterministic)."""
        ss_replay = kem.decap_secret(ct_valid)
        report.probes.append(ProbeResult(
            "deterministic_decap",
            ss_replay == ss_valid,
            "decap is deterministic (expected for Fujisaki-Okamoto transform)",
        ))

    def _probe_timing_consistency(self, kem, ct_valid: bytes,
                                  report: AttackReport, samples: int = 20) -> None:
        """Timing of valid vs. invalid decap should not differ by >10x (side-channel check)."""
        times_valid, times_invalid = [], []
        for _ in range(samples):
            t0 = time.perf_counter()
            kem.decap_secret(ct_valid)
            times_valid.append((time.perf_counter() - t0) * 1000)

            bad_ct = os.urandom(self.p.ct_size)
            t0 = time.perf_counter()
            kem.decap_secret(bad_ct)
            times_invalid.append((time.perf_counter() - t0) * 1000)

        mean_v = statistics.mean(times_valid)
        mean_i = statistics.mean(times_invalid)
        ratio = max(mean_v, mean_i) / max(min(mean_v, mean_i), 0.001)
        report.probes.append(ProbeResult(
            "timing_consistency",
            ratio < 10.0,
            f"valid={mean_v:.2f}ms invalid={mean_i:.2f}ms ratio={ratio:.2f}x",
            timing_ms=mean_v,
        ))

    def _probe_ss_reuse(self, kem, ek: bytes, report: AttackReport) -> None:
        """Two encapsulations with the same ek must produce different ciphertexts."""
        ct1, ss1 = kem.encap_secret(ek)
        ct2, ss2 = kem.encap_secret(ek)
        report.probes.append(ProbeResult(
            "ciphertext_freshness",
            ct1 != ct2,
            "different cts from same ek (randomized encap)" if ct1 != ct2 else "FAIL: deterministic encap!",
        ))
        report.probes.append(ProbeResult(
            "different_encaps_different_ss",
            ss1 != ss2,
            "different shared secrets per encap",
        ))
