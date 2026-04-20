"""Service-wide configuration."""
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PQC_", env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8888
    ws_timeout: float = 15.0       # seconds to wait for each WS response
    session_ttl: int = 3600        # seconds to keep completed sessions
    max_sessions: int = 500        # cap in-memory sessions
    version: str = "1.0.0"

    # CRITICAL tests — failing any gives NOT_READY regardless of score
    critical_tests: list[str] = [
        "happy_ek_size",
        "happy_ct_size",
        "happy_proof_valid",
        "bad_ct_handled",
        "bit_flip_ct_rejection",
    ]

    # IMPORTANT tests — affect score but not verdict
    important_tests: list[str] = [
        "timing_consistency",
        "ciphertext_freshness",
        "concurrent_sessions_independent",
        "all_zeros_ct_rejection",
        "deterministic_decap",
    ]


settings = Settings()
