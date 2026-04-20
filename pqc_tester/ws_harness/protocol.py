"""
pqc-nexus WebSocket test protocol.

Handshake sequence (JSON over WebSocket):

  C→S  {"action":"kem_hello","variant":"ML-KEM-768","session":"<uuid>"}
  S→C  {"action":"kem_pubkey","ek":"<hex>","session":"<uuid>"}
  C→S  {"action":"kem_encap","ct":"<hex>","session":"<uuid>"}
  S→C  {"action":"kem_proof","tag":"<hex>","session":"<uuid>"}
       tag = HMAC-SHA256(key=shared_secret, msg=b"pqc-nexus-v1")

  # Error path
  S→C  {"action":"kem_error","code":"<str>","detail":"<str>"}

The Flutter app must implement the SERVER side of this protocol.
This module provides the CLIENT side (test harness).
"""
from __future__ import annotations
import json
import hmac
import hashlib
import uuid


PROTOCOL_VERSION = "pqc-nexus-v1"
PROOF_LABEL = b"pqc-nexus-v1"


def make_hello(variant: str) -> str:
    return json.dumps({
        "action": "kem_hello",
        "variant": variant,
        "session": str(uuid.uuid4()),
        "protocol": PROTOCOL_VERSION,
    })


def parse_pubkey(raw: str) -> tuple[bytes, str]:
    """Parse kem_pubkey message. Returns (ek_bytes, session_id)."""
    msg = json.loads(raw)
    if msg.get("action") == "kem_error":
        raise ProtocolError(msg.get("code", "unknown"), msg.get("detail", ""))
    if msg["action"] != "kem_pubkey":
        raise ProtocolError("unexpected_action", f"expected kem_pubkey, got {msg['action']}")
    return bytes.fromhex(msg["ek"]), msg["session"]


def make_encap(ct: bytes, session: str) -> str:
    return json.dumps({
        "action": "kem_encap",
        "ct": ct.hex(),
        "session": session,
    })


def parse_proof(raw: str) -> bytes:
    """Parse kem_proof message. Returns tag bytes."""
    msg = json.loads(raw)
    if msg.get("action") == "kem_error":
        raise ProtocolError(msg.get("code", "unknown"), msg.get("detail", ""))
    if msg["action"] != "kem_proof":
        raise ProtocolError("unexpected_action", f"expected kem_proof, got {msg['action']}")
    return bytes.fromhex(msg["tag"])


def compute_proof(shared_secret: bytes) -> bytes:
    """HMAC-SHA256(key=shared_secret, msg=PROOF_LABEL)."""
    return hmac.new(shared_secret, PROOF_LABEL, hashlib.sha256).digest()


def verify_proof(shared_secret: bytes, tag: bytes) -> bool:
    expected = compute_proof(shared_secret)
    return hmac.compare_digest(expected, tag)


class ProtocolError(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"[{code}] {detail}")
