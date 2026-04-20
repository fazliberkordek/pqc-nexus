"""Pydantic request/response models for pqc-nexus API."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


# ── requests ──────────────────────────────────────────────────────────────────

class HarnessRequest(BaseModel):
    url: str = Field(..., example="ws://localhost:9000/kem",
                     description="WebSocket URL of the app under test")
    variant: str = Field("ML-KEM-768", example="ML-KEM-768",
                          description="ML-KEM-512 | ML-KEM-768 | ML-KEM-1024")


class PQCRequest(BaseModel):
    variant: str = Field("ML-KEM-768", example="ML-KEM-768")


# ── responses ─────────────────────────────────────────────────────────────────

class TestItem(BaseModel):
    name: str
    passed: bool
    detail: str = ""
    duration_ms: float | None = None


class ConformanceResponse(BaseModel):
    variant: str
    passed: bool
    total: int
    failures: list[str]
    checks: list[TestItem]


class AttackResponse(BaseModel):
    variant: str
    all_passed: bool
    probes: list[TestItem]


class HarnessResponse(BaseModel):
    url: str
    variant: str
    overall: str          # "PASS" | "FAIL"
    results: list[TestItem]


class AlgorithmResponse(BaseModel):
    name: str
    success: bool
    metric: str
    duration_ms: float
    raw: dict[str, Any]


class AllAlgorithmsResponse(BaseModel):
    results: list[AlgorithmResponse]
    passed: int
    failed: int
    total_ms: float


class HealthResponse(BaseModel):
    status: str
    oqs_available: bool
    qiskit_available: bool
    version: str


# ── streaming events (WebSocket) ──────────────────────────────────────────────

class StreamEvent(BaseModel):
    """One event pushed over the streaming WebSocket."""
    event: str          # "start" | "test_result" | "done" | "error"
    test: str | None = None
    passed: bool | None = None
    detail: str = ""
    duration_ms: float | None = None
    summary: dict | None = None   # present only on "done"
