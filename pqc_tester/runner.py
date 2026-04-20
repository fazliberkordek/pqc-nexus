"""Main test runner — conformance + attacks + optional WS harness."""
from __future__ import annotations
import asyncio
import json
from .ml_kem.conformance import ConformanceTester
from .ml_kem.attacks import AttackSuite
from .ws_harness.client import WSTestClient
from .ws_harness.reporter import HarnessReporter


def run_suite(
    variant: str = "ML-KEM-768",
    ws_url: str | None = None,
    output_json: bool = False,
) -> dict:
    """
    Run the full PQC test suite.

    Args:
        variant:     ML-KEM variant to test ('ML-KEM-512', 'ML-KEM-768', 'ML-KEM-1024')
        ws_url:      Optional WebSocket URL of the app under test
        output_json: If True, return raw dict instead of printing

    Returns dict with keys: conformance, attacks, ws (if url provided)
    """
    report: dict = {}

    # Conformance
    conformance = ConformanceTester(variant).run()
    report["conformance"] = conformance.summary()
    if not output_json:
        HarnessReporter.print_conformance(report["conformance"])

    # Attacks
    attacks = AttackSuite(variant).run()
    report["attacks"] = attacks.summary()
    if not output_json:
        HarnessReporter.print_attacks(report["attacks"])

    # WebSocket harness
    if ws_url:
        client = WSTestClient(ws_url, variant)
        ws_summary = asyncio.run(client.run_all()).summary()
        report["ws"] = ws_summary
        if not output_json:
            HarnessReporter.print_ws_session(ws_summary)

    if output_json:
        print(json.dumps(report, indent=2))

    return report
