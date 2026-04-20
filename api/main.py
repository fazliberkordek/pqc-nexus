"""
pqc-nexus REST + WebSocket API
Start: uvicorn api.main:app --host 0.0.0.0 --port 8888 --reload

Open-source stack: FastAPI (MIT) · Uvicorn (BSD-3) · Qiskit (Apache-2) · oqs-python (MIT)
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    AlgorithmResponse, AllAlgorithmsResponse,
    AttackResponse, ConformanceResponse,
    HarnessRequest, HarnessResponse,
    HealthResponse, PQCRequest,
    StreamEvent, TestItem,
)

# ── app setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="pqc-nexus",
    description=(
        "Quantum algorithm reference runner + ML-KEM/FIPS-203 compliance tester.\n\n"
        "**All dependencies are open-source** (MIT / Apache-2 / BSD-3).\n\n"
        "WebSocket endpoint `/ws/test` streams live results to Flutter."
    ),
    version="0.1.0",
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    contact={"name": "pqc-nexus", "url": "https://github.com/fazliberkordek/pqc-nexus"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Flutter on any host
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _check_oqs() -> bool:
    try:
        import oqs  # noqa: F401
        return True
    except ImportError:
        return False


def _check_qiskit() -> bool:
    try:
        import qiskit  # noqa: F401
        return True
    except ImportError:
        return False


def _run_algo_sync(name: str) -> AlgorithmResponse:
    """Run one quantum algorithm synchronously (called in thread pool)."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from runner import _dispatch_algo, _result_metric, _algo_succeeded  # type: ignore

    t0 = time.perf_counter()
    raw = _dispatch_algo(name)
    ms = round((time.perf_counter() - t0) * 1000, 2)
    return AlgorithmResponse(
        name=name,
        success=_algo_succeeded(name, raw),
        metric=_result_metric(name, raw),
        duration_ms=ms,
        raw={k: str(v) for k, v in raw.items()},
    )


ALGO_KEYS = [
    "grover", "deutsch-jozsa", "bernstein-vazirani", "simon",
    "shor", "qft", "qpe", "teleport", "bb84", "vqe", "qaoa", "hhl",
]

# ── health ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    """Service liveness + dependency availability."""
    return HealthResponse(
        status="ok",
        oqs_available=_check_oqs(),
        qiskit_available=_check_qiskit(),
        version="0.1.0",
    )


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "service": "pqc-nexus",
        "docs": "/docs",
        "endpoints": {
            "health":      "GET  /health",
            "algorithms":  "GET  /algorithms  |  GET /algorithms/{name}",
            "conformance": "POST /test/conformance",
            "attacks":     "POST /test/attacks",
            "harness":     "POST /test/harness",
            "streaming":   "WS   /ws/test",
        },
        "license": "MIT",
        "open_source": True,
    }


# ── quantum algorithms ────────────────────────────────────────────────────────

@app.get("/algorithms", response_model=AllAlgorithmsResponse, tags=["algorithms"])
async def run_all_algorithms() -> AllAlgorithmsResponse:
    """
    Run all 12 quantum algorithms and return aggregated results.
    Runs in FastAPI's thread pool (CPU-bound Qiskit circuits).
    """
    loop = asyncio.get_event_loop()
    t0 = time.perf_counter()

    tasks = [
        loop.run_in_executor(None, _run_algo_sync, key)
        for key in ALGO_KEYS
    ]
    results: list[AlgorithmResponse] = await asyncio.gather(*tasks, return_exceptions=False)
    total_ms = round((time.perf_counter() - t0) * 1000, 2)

    return AllAlgorithmsResponse(
        results=results,
        passed=sum(1 for r in results if r.success),
        failed=sum(1 for r in results if not r.success),
        total_ms=total_ms,
    )


@app.get("/algorithms/{name}", response_model=AlgorithmResponse, tags=["algorithms"])
async def run_algorithm(name: str) -> AlgorithmResponse:
    """
    Run a single quantum algorithm by name.

    Valid names: grover, deutsch-jozsa, bernstein-vazirani, simon,
    shor, qft, qpe, teleport, bb84, vqe, qaoa, hhl
    """
    if name not in ALGO_KEYS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown algorithm '{name}'. Valid: {ALGO_KEYS}",
        )
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_algo_sync, name)


# ── ML-KEM conformance ────────────────────────────────────────────────────────

@app.post("/test/conformance", response_model=ConformanceResponse, tags=["pqc"])
async def test_conformance(req: PQCRequest) -> ConformanceResponse:
    """
    Run FIPS 203 conformance checks for the given ML-KEM variant.
    Requires oqs-python (liboqs) for full checks; structural checks run without it.
    """
    from pqc_tester.ml_kem.conformance import ConformanceTester

    def _run():
        return ConformanceTester(req.variant).run().summary()

    loop = asyncio.get_event_loop()
    summary = await loop.run_in_executor(None, _run)

    return ConformanceResponse(
        variant=summary["variant"],
        passed=summary["passed"],
        total=summary["total"],
        failures=summary["failures"],
        checks=[
            TestItem(name=d["name"], passed=d["passed"], detail=d["detail"])
            for d in summary["details"]
        ],
    )


# ── ML-KEM attack suite ───────────────────────────────────────────────────────

@app.post("/test/attacks", response_model=AttackResponse, tags=["pqc"])
async def test_attacks(req: PQCRequest) -> AttackResponse:
    """
    Run attack probe suite against the local ML-KEM implementation.
    Probes: bit-flip, zero-ct, replay, timing consistency, ciphertext freshness.
    Requires oqs-python.
    """
    from pqc_tester.ml_kem.attacks import AttackSuite

    def _run():
        return AttackSuite(req.variant).run().summary()

    loop = asyncio.get_event_loop()
    summary = await loop.run_in_executor(None, _run)

    return AttackResponse(
        variant=summary["variant"],
        all_passed=summary["all_passed"],
        probes=[
            TestItem(
                name=p["name"],
                passed=p["passed"],
                detail=p["detail"],
                duration_ms=p.get("timing_ms"),
            )
            for p in summary["probes"]
        ],
    )


# ── WebSocket harness (REST variant) ──────────────────────────────────────────

@app.post("/test/harness", response_model=HarnessResponse, tags=["harness"])
async def test_harness(req: HarnessRequest) -> HarnessResponse:
    """
    Connect to the app's WebSocket endpoint and run the full ML-KEM handshake
    test suite. Returns a complete report once all tests finish.

    Use `POST /test/harness` when you need a single JSON response.
    Use `WS /ws/test` when you want live streaming results.
    """
    from pqc_tester.ws_harness.client import WSTestClient

    client = WSTestClient(req.url, req.variant)
    session = await client.run_all()
    summary = session.summary()

    return HarnessResponse(
        url=summary["url"],
        variant=summary["variant"],
        overall=summary["overall"],
        results=[
            TestItem(
                name=r["test"],
                passed=r["passed"],
                detail=r["detail"],
                duration_ms=r["duration_ms"] or None,
            )
            for r in summary["results"]
        ],
    )


# ── WebSocket streaming endpoint ──────────────────────────────────────────────

@app.websocket("/ws/test")
async def ws_streaming_test(websocket: WebSocket) -> None:
    """
    Streaming WebSocket endpoint.

    Flutter connects, sends one JSON config message, then receives a stream
    of events as each test completes.

    ┌─ Flutter sends (once) ──────────────────────────────────────────────────┐
    │  {                                                                       │
    │    "mode":    "harness" | "conformance" | "attacks" | "algorithms",     │
    │    "url":     "ws://host:port/path",   // required for harness mode      │
    │    "variant": "ML-KEM-768"             // optional, default ML-KEM-768   │
    │  }                                                                       │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─ pqc-nexus streams back ────────────────────────────────────────────────┐
    │  {"event":"start",       "detail":"ML-KEM-768 harness starting…"}       │
    │  {"event":"test_result", "test":"happy_ek_size", "passed":true, …}      │
    │  {"event":"test_result", "test":"happy_proof_valid", "passed":true, …}  │
    │  …                                                                       │
    │  {"event":"done", "passed":true, "summary":{…}}                         │
    └─────────────────────────────────────────────────────────────────────────┘
    """
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
        cfg = json.loads(raw)
    except Exception as exc:
        await websocket.send_json({"event": "error", "detail": str(exc)})
        await websocket.close()
        return

    mode    = cfg.get("mode", "harness")
    variant = cfg.get("variant", "ML-KEM-768")
    url     = cfg.get("url", "")

    await websocket.send_json({
        "event": "start",
        "detail": f"{variant} {mode} starting…",
    })

    try:
        async for event in _stream_events(mode, variant, url):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json({"event": "error", "detail": str(exc)})
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


async def _stream_events(
    mode: str, variant: str, url: str
) -> AsyncGenerator[dict, None]:
    """Yield streaming event dicts for each completed test."""

    if mode == "harness":
        from pqc_tester.ws_harness.client import WSTestClient, WSTestResult

        client = WSTestClient(url, variant)
        # Patch run_all to yield per-result events
        session = await client.run_all()
        all_passed = True
        for r in session.results:
            if not r.passed:
                all_passed = False
            yield {
                "event":       "test_result",
                "test":        r.test,
                "passed":      r.passed,
                "detail":      r.detail,
                "duration_ms": round(r.duration_ms, 2),
            }
            await asyncio.sleep(0)  # yield control

        yield {
            "event":   "done",
            "passed":  all_passed,
            "summary": session.summary(),
        }

    elif mode == "conformance":
        from pqc_tester.ml_kem.conformance import ConformanceTester
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(
            None, lambda: ConformanceTester(variant).run()
        )
        summary = report.summary()
        for item in summary["details"]:
            yield {
                "event":  "test_result",
                "test":   item["name"],
                "passed": item["passed"],
                "detail": item["detail"],
            }
            await asyncio.sleep(0)
        yield {"event": "done", "passed": summary["passed"], "summary": summary}

    elif mode == "attacks":
        from pqc_tester.ml_kem.attacks import AttackSuite
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(
            None, lambda: AttackSuite(variant).run()
        )
        summary = report.summary()
        for probe in summary["probes"]:
            yield {
                "event":       "test_result",
                "test":        probe["name"],
                "passed":      probe["passed"],
                "detail":      probe["detail"],
                "duration_ms": probe.get("timing_ms"),
            }
            await asyncio.sleep(0)
        yield {"event": "done", "passed": summary["all_passed"], "summary": summary}

    elif mode == "algorithms":
        loop = asyncio.get_event_loop()
        total_passed = 0
        results = []
        for key in ALGO_KEYS:
            result = await loop.run_in_executor(None, _run_algo_sync, key)
            if result.success:
                total_passed += 1
            results.append(result)
            yield {
                "event":       "test_result",
                "test":        key,
                "passed":      result.success,
                "detail":      result.metric,
                "duration_ms": result.duration_ms,
            }
            await asyncio.sleep(0)
        yield {
            "event":  "done",
            "passed": total_passed == len(ALGO_KEYS),
            "summary": {
                "total": len(ALGO_KEYS),
                "passed": total_passed,
                "failed": len(ALGO_KEYS) - total_passed,
            },
        }
    else:
        yield {"event": "error", "detail": f"Unknown mode: {mode}"}
