"""All Pydantic request/response models for pqc-nexus API v1."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, HttpUrl


# ── enums ─────────────────────────────────────────────────────────────────────

class Verdict(str, Enum):
    PQC_READY = "PQC_READY"   # all critical tests pass
    NOT_READY = "NOT_READY"   # one or more critical tests fail
    DEGRADED  = "DEGRADED"    # critical pass, important tests fail
    ERROR     = "ERROR"       # could not connect or fatal error


class SessionStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


class MLKEMVariant(str, Enum):
    KEM_512  = "ML-KEM-512"
    KEM_768  = "ML-KEM-768"
    KEM_1024 = "ML-KEM-1024"


class TestCategory(str, Enum):
    HANDSHAKE    = "handshake"
    CONFORMANCE  = "conformance"
    SECURITY     = "security"
    PROTOCOL     = "protocol"


class TestSeverity(str, Enum):
    CRITICAL    = "critical"
    IMPORTANT   = "important"
    INFORMATIONAL = "informational"


# ── requests ──────────────────────────────────────────────────────────────────

class SubmitRequest(BaseModel):
    """Submit a Flutter/any app for PQC readiness testing."""
    url: str = Field(
        ...,
        example="ws://localhost:9000/kem",
        description="WebSocket URL of the app's ML-KEM endpoint",
    )
    variant: MLKEMVariant = Field(
        MLKEMVariant.KEM_768,
        description="ML-KEM parameter set to test against",
    )
    label: str | None = Field(
        None,
        max_length=80,
        example="my-flutter-chat-app v1.2",
        description="Optional human-readable label for this test session",
    )
    include_local: bool = Field(
        True,
        description="Also run local FIPS 203 conformance + attack probes",
    )


class AlgorithmRequest(BaseModel):
    name: str = Field(..., example="grover")


# ── test result ───────────────────────────────────────────────────────────────

class TestResult(BaseModel):
    name: str
    category: TestCategory
    severity: TestSeverity
    passed: bool
    detail: str = ""
    duration_ms: float | None = None
    remediation: str | None = None   # what to fix if failed


# ── session ───────────────────────────────────────────────────────────────────

class SessionSummary(BaseModel):
    session_id: str
    status: SessionStatus
    label: str | None
    url: str
    variant: str
    created_at: datetime
    completed_at: datetime | None = None


class SessionReport(BaseModel):
    session_id: str
    label: str | None
    url: str
    variant: str
    status: SessionStatus
    verdict: Verdict | None = None
    score: int | None = Field(None, ge=0, le=100, description="0-100 PQC readiness score")
    created_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None

    # categorised results
    handshake:   list[TestResult] = []
    conformance: list[TestResult] = []
    security:    list[TestResult] = []
    protocol:    list[TestResult] = []

    # top-level counts
    total: int = 0
    passed: int = 0
    failed: int = 0
    critical_failures: list[str] = []
    summary_text: str = ""


# ── streaming events ──────────────────────────────────────────────────────────

class StreamEvent(BaseModel):
    event: str          # start | test_result | phase | done | error
    session_id: str | None = None
    phase: str | None = None          # present on "phase" events
    test: str | None = None
    category: str | None = None
    severity: str | None = None
    passed: bool | None = None
    detail: str = ""
    duration_ms: float | None = None
    remediation: str | None = None
    verdict: str | None = None        # present on "done"
    score: int | None = None          # present on "done"
    report: dict | None = None        # present on "done"


# ── algorithm ─────────────────────────────────────────────────────────────────

class AlgorithmResult(BaseModel):
    name: str
    success: bool
    metric: str
    duration_ms: float
    raw: dict[str, Any]


class AllAlgorithmsResult(BaseModel):
    results: list[AlgorithmResult]
    passed: int
    failed: int
    total_ms: float


# ── health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    oqs_available: bool
    qiskit_available: bool
    active_sessions: int
