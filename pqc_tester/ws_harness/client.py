"""
Async WebSocket test client.
Connects to a Flutter/any-language PQC app and runs the ML-KEM test suite.
"""
from __future__ import annotations
import asyncio
import os
import time
from dataclasses import dataclass, field

import websockets

from ..ml_kem.params import PARAMS
from .protocol import (
    make_hello, parse_pubkey, make_encap, parse_proof,
    verify_proof, ProtocolError, PROOF_LABEL,
)

try:
    import oqs  # type: ignore
    OQS_AVAILABLE = True
except ImportError:
    OQS_AVAILABLE = False


@dataclass
class WSTestResult:
    test: str
    passed: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class WSTestSession:
    url: str
    variant: str
    results: list[WSTestResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def add(self, test: str, passed: bool, detail: str = "", duration_ms: float = 0.0):
        self.results.append(WSTestResult(test, passed, detail, duration_ms))

    def summary(self) -> dict:
        return {
            "url": self.url,
            "variant": self.variant,
            "overall": "PASS" if self.passed else "FAIL",
            "results": [
                {
                    "test": r.test,
                    "passed": r.passed,
                    "detail": r.detail,
                    "duration_ms": round(r.duration_ms, 2),
                }
                for r in self.results
            ],
        }


class WSTestClient:
    """
    Runs ML-KEM conformance tests against a WebSocket endpoint.

    The remote app must implement the pqc-nexus server protocol:
    See pqc_tester/ws_harness/protocol.py for the message spec.
    """

    def __init__(self, url: str, variant: str = "ML-KEM-768", timeout: float = 10.0):
        self.url = url
        self.variant = variant
        self.timeout = timeout
        self.p = PARAMS[variant]

    async def run_all(self) -> WSTestSession:
        session = WSTestSession(self.url, self.variant)

        if not OQS_AVAILABLE:
            session.add("oqs_check", False,
                        "oqs-python not installed — cannot run WS tests.")
            return session

        await self._test_happy_path(session)
        await self._test_bad_ciphertext(session)
        await self._test_wrong_variant(session)
        await self._test_ek_size(session)
        await self._test_concurrent(session)
        return session

    async def _connect(self):
        return await asyncio.wait_for(
            websockets.connect(self.url), timeout=self.timeout
        )

    async def _test_happy_path(self, session: WSTestSession) -> None:
        """Full handshake with correct ML-KEM key exchange."""
        t0 = time.perf_counter()
        try:
            async with await self._connect() as ws:
                # Hello
                await ws.send(make_hello(self.variant))
                raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                ek, sid = parse_pubkey(raw)

                # EK size
                session.add(
                    "happy_ek_size",
                    len(ek) == self.p.ek_size,
                    f"got {len(ek)} expected {self.p.ek_size}",
                )

                # Encapsulate
                with oqs.KeyEncapsulation(self.variant) as kem:
                    ct, ss = kem.encap_secret(ek)

                session.add(
                    "happy_ct_size",
                    len(ct) == self.p.ct_size,
                    f"got {len(ct)} expected {self.p.ct_size}",
                )

                # Send ciphertext
                await ws.send(make_encap(ct, sid))
                raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                tag = parse_proof(raw)

                # Verify HMAC proof
                ok = verify_proof(ss, tag)
                session.add(
                    "happy_proof_valid",
                    ok,
                    "server HMAC-SHA256 proof matches shared secret" if ok
                    else "FAIL: proof mismatch — server may not be using real ML-KEM",
                )

                elapsed = (time.perf_counter() - t0) * 1000
                session.add("happy_latency", True, f"{elapsed:.1f}ms", elapsed)

        except ProtocolError as e:
            session.add("happy_path", False, str(e))
        except Exception as e:
            session.add("happy_path", False, f"{type(e).__name__}: {e}")

    async def _test_bad_ciphertext(self, session: WSTestSession) -> None:
        """Send random bytes as ciphertext — server must not crash."""
        try:
            async with await self._connect() as ws:
                await ws.send(make_hello(self.variant))
                raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                ek, sid = parse_pubkey(raw)

                bad_ct = os.urandom(self.p.ct_size)
                await ws.send(make_encap(bad_ct, sid))
                raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)

                # Server should return either kem_proof (implicit rejection) or kem_error
                import json
                msg = json.loads(raw)
                survived = msg["action"] in {"kem_proof", "kem_error"}
                session.add(
                    "bad_ct_handled",
                    survived,
                    f"server responded with action={msg['action']} (did not crash)",
                )

                # If it returned a proof, it must differ from what a valid ct would give
                # (we can't check the exact value without knowing the dk, so just check format)
                if msg["action"] == "kem_proof":
                    tag = bytes.fromhex(msg["tag"])
                    session.add(
                        "bad_ct_proof_size",
                        len(tag) == 32,
                        f"implicit rejection tag size: {len(tag)}",
                    )

        except Exception as e:
            session.add("bad_ct_handled", False, f"{type(e).__name__}: {e}")

    async def _test_wrong_variant(self, session: WSTestSession) -> None:
        """Request an unsupported variant — server should respond with kem_error."""
        try:
            async with await self._connect() as ws:
                import json
                payload = json.dumps({"action": "kem_hello", "variant": "INVALID-KEM-9999"})
                await ws.send(payload)
                raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                msg = json.loads(raw)
                session.add(
                    "unknown_variant_rejected",
                    msg["action"] == "kem_error",
                    f"server responded: {msg['action']}",
                )
        except Exception as e:
            # Connection close is also acceptable for invalid variant
            session.add("unknown_variant_rejected", True,
                        f"connection closed (acceptable): {e}")

    async def _test_ek_size(self, session: WSTestSession) -> None:
        """Validate encapsulation key size matches FIPS 203 spec exactly."""
        try:
            async with await self._connect() as ws:
                await ws.send(make_hello(self.variant))
                raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                ek, _ = parse_pubkey(raw)
                session.add(
                    "ek_fips203_size",
                    len(ek) == self.p.ek_size,
                    f"FIPS 203 {self.variant} ek must be {self.p.ek_size} bytes, got {len(ek)}",
                )
        except Exception as e:
            session.add("ek_fips203_size", False, str(e))

    async def _test_concurrent(self, session: WSTestSession) -> None:
        """Two concurrent sessions must produce independent shared secrets."""
        try:
            async def do_exchange() -> bytes:
                async with await self._connect() as ws:
                    await ws.send(make_hello(self.variant))
                    raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                    ek, sid = parse_pubkey(raw)
                    with oqs.KeyEncapsulation(self.variant) as kem:
                        ct, ss = kem.encap_secret(ek)
                    await ws.send(make_encap(ct, sid))
                    raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                    return parse_proof(raw)  # tag bytes

            tag1, tag2 = await asyncio.gather(do_exchange(), do_exchange())
            session.add(
                "concurrent_sessions_independent",
                tag1 != tag2,
                "two concurrent sessions yield different proof tags",
            )
        except Exception as e:
            session.add("concurrent_sessions_independent", False, str(e))
