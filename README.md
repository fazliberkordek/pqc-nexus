# pqc-nexus

> Quantum algorithm reference suite + ML-KEM / FIPS 203 compliance tester with a live TUI monitor and a FastAPI service callable from any app (Flutter, web, CLI).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![Qiskit](https://img.shields.io/badge/Qiskit-1.3%2B-6929c4)](https://qiskit.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688)](https://fastapi.tiangolo.com)
[![FIPS 203](https://img.shields.io/badge/FIPS%20203-ML--KEM-orange)](https://csrc.nist.gov/pubs/fips/203/final)
[![Open Source](https://img.shields.io/badge/open--source-100%25-brightgreen)](#open-source-stack)

---

## What is this?

**pqc-nexus** is a testing hub for two things:

1. **Quantum algorithms** — 12 reference implementations (Grover, Shor, QFT, VQE, QAOA, BB84, …) runnable via simulator, TUI, CLI, or REST API.
2. **Post-quantum cryptography (PQC)** — a compliance tester that connects to *your app* (Flutter, any language) over WebSocket, runs a live ML-KEM key exchange, and verifies every byte against FIPS 203.

```
Your Flutter app (PQC E2EE chat)
        │
        │  POST /test/harness  {"url":"ws://…/kem","variant":"ML-KEM-768"}
        ▼
  pqc-nexus API  :8888
        │
        │  connects back → runs ML-KEM handshake → checks FIPS 203
        ▼
  Your app's WebSocket KEM endpoint
        │
        └─→  JSON report  (or live-streamed events)
```

---

## Architecture

```
pqc-nexus/
│
├── algorithms/               12 quantum algorithms (Qiskit)
│   ├── grover.py             Grover's search
│   ├── shor.py               Shor's factoring
│   ├── qft.py                Quantum Fourier Transform
│   ├── qpe.py                Quantum Phase Estimation
│   ├── deutsch_jozsa.py      Deutsch-Jozsa
│   ├── bernstein_vazirani.py Bernstein-Vazirani
│   ├── simon.py              Simon's algorithm
│   ├── teleportation.py      Quantum teleportation
│   ├── bb84.py               BB84 QKD simulation
│   ├── vqe.py                VQE — H₂ ground state
│   ├── qaoa.py               QAOA — MaxCut
│   └── hhl.py                HHL linear solver
│
├── pqc_tester/
│   ├── ml_kem/
│   │   ├── params.py         FIPS 203 byte-size constants (512/768/1024)
│   │   ├── conformance.py    Full conformance suite (oqs-python)
│   │   ├── test_vectors.py   NIST KAT vectors
│   │   └── attacks.py        Bit-flip, zero-ct, replay, timing probes
│   └── ws_harness/
│       ├── protocol.py       JSON-over-WS message spec
│       ├── client.py         Async WS test client (connects to your app)
│       └── reporter.py       Rich terminal tables
│
├── api/
│   ├── main.py               FastAPI app — REST + WebSocket streaming
│   └── models.py             Pydantic request/response types
│
├── monitor.py                Textual TUI live dashboard
├── runner.py                 Typer CLI
└── tests/                    pytest suite
```

---

## Quantum Algorithms

| # | Algorithm | What it proves | Key result |
|---|-----------|---------------|------------|
| 1 | **Grover's Search** | Quadratic speedup for unstructured search | Target found in O(√N) |
| 2 | **Shor's Factoring** | Exponential speedup for integer factorization (breaks RSA/ECC) | Factors of N |
| 3 | **QFT** | Quantum Fourier Transform — building block for QPE & Shor's | Circuit depth |
| 4 | **QPE** | Quantum Phase Estimation — eigenphase of unitary | Phase θ ∈ [0,1) |
| 5 | **Deutsch-Jozsa** | Single query vs. classical O(2^n) | constant / balanced |
| 6 | **Bernstein-Vazirani** | Hidden bitstring in 1 query | recovered secret s |
| 7 | **Simon's Algorithm** | Exponential speedup for XOR-period finding | hidden period s |
| 8 | **Quantum Teleportation** | Transmit qubit state via 2 cbits + entanglement | Fidelity = 1 |
| 9 | **BB84 QKD** | Quantum key distribution with eavesdropping detection | QBER, sifted key |
| 10 | **VQE** | Variational ground state energy (H₂ molecule) | Energy in Hartree |
| 11 | **QAOA** | Quantum approximate optimisation — MaxCut | Cut value |
| 12 | **HHL** | Quantum linear systems solver | Solution vector |

---

## ML-KEM / FIPS 203 Parameter Sets

| Variant | Enc. Key | Ciphertext | Dec. Key | Security |
|---------|----------|------------|----------|----------|
| ML-KEM-512  | 800 B  | 768 B  | 1 632 B | NIST Level 1 |
| ML-KEM-768  | 1 184 B | 1 088 B | 2 400 B | NIST Level 3 |
| ML-KEM-1024 | 1 568 B | 1 568 B | 3 168 B | NIST Level 5 |

All shared secrets are 32 bytes. Implicit rejection on bad ciphertext (Fujisaki-Okamoto transform).

---

## Open-Source Stack

| Library | License | Role |
|---------|---------|------|
| [Qiskit](https://github.com/Qiskit/qiskit) | Apache 2.0 | Quantum circuit simulation |
| [Qiskit Aer](https://github.com/Qiskit/qiskit-aer) | Apache 2.0 | High-performance simulator |
| [oqs-python / liboqs](https://github.com/open-quantum-safe/liboqs-python) | MIT | ML-KEM key operations (NIST-validated) |
| [FastAPI](https://github.com/fastapi/fastapi) | MIT | REST + WebSocket API |
| [Uvicorn](https://github.com/encode/uvicorn) | BSD-3 | ASGI server |
| [websockets](https://github.com/python-websockets/websockets) | BSD-3 | WS harness client |
| [Textual](https://github.com/Textualize/textual) | MIT | TUI live monitor |
| [Rich](https://github.com/Textualize/rich) | MIT | Terminal formatting |
| [Typer](https://github.com/tiangolo/typer) | MIT | CLI |
| [NumPy](https://numpy.org) | BSD-3 | Numerical ops |
| [SciPy](https://scipy.org) | BSD-3 | Classical optimisers (VQE/QAOA) |
| [pytest](https://pytest.org) | MIT | Test suite |

---

## Installation

### 1. Clone & create environment

```bash
git clone https://github.com/fazliberkordek/pqc-nexus.git
cd pqc-nexus
python -m venv .venv && source .venv/bin/activate
pip install -e ".[oqs]"
```

### 2. Install liboqs (required for ML-KEM operations)

```bash
# macOS
brew install liboqs

# Ubuntu / Debian
sudo apt install liboqs-dev

# Windows — build from source:
# https://github.com/open-quantum-safe/liboqs#building
```

Then install the Python binding:
```bash
pip install oqs-python
```

> Without liboqs the API still runs — conformance tests fall back to structural (byte-size) checks only.

---

## Running

### Option A — Live TUI monitor

```bash
python monitor.py

# With a live Flutter WS target pre-filled:
python monitor.py --ws ws://localhost:9000/kem
```

| Tab | Contents |
|-----|----------|
| ⚛ Algorithms | All 12 algorithms — live ○◌✓✗ status badges, timing |
| 🔐 ML-KEM | Conformance + attack probes per variant |
| 🌐 WS Harness | URL input → connect to your app → live results |
| 📋 Logs | Timestamped coloured log of all events |

Keybindings: `Ctrl+R` run all algos · `Ctrl+P` run PQC suite · `Ctrl+L` clear log · `q` quit

---

### Option B — REST / WebSocket API service

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8888 --reload
```

Interactive docs (auto-generated): **http://localhost:8888/docs**

---

### Option C — CLI

```bash
# Run one algorithm
python runner.py run-algo grover

# Run PQC suite (no live app)
python runner.py test-pqc --variant ML-KEM-768

# Run PQC suite against a live app
python runner.py test-pqc --variant ML-KEM-768 --url ws://localhost:9000/kem

# JSON output
python runner.py test-pqc --json
```

---

## API Reference

### REST Endpoints

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| `GET` | `/health` | — | Service status, oqs/qiskit availability |
| `GET` | `/algorithms` | — | Run all 12 algorithms (parallel) |
| `GET` | `/algorithms/{name}` | — | Run one algorithm |
| `POST` | `/test/conformance` | `{"variant":"ML-KEM-768"}` | FIPS 203 conformance checks |
| `POST` | `/test/attacks` | `{"variant":"ML-KEM-768"}` | Attack probe suite |
| `POST` | `/test/harness` | `{"url":"ws://…","variant":"ML-KEM-768"}` | Connect to app, run full test suite |

### WebSocket Streaming — `WS /ws/test`

Flutter connects once, sends a config message, receives a stream of events.

**Send (once):**
```json
{
  "mode":    "harness",
  "url":     "ws://localhost:9000/kem",
  "variant": "ML-KEM-768"
}
```

`mode` options: `harness` · `conformance` · `attacks` · `algorithms`

**Receive (stream):**
```json
{"event": "start",       "detail": "ML-KEM-768 harness starting…"}
{"event": "test_result", "test": "happy_ek_size",     "passed": true,  "detail": "got 1184 expected 1184", "duration_ms": 12.3}
{"event": "test_result", "test": "happy_proof_valid",  "passed": true,  "detail": "server HMAC-SHA256 proof matches shared secret"}
{"event": "test_result", "test": "bad_ct_handled",     "passed": true,  "detail": "server responded with action=kem_error"}
{"event": "test_result", "test": "concurrent_sessions_independent", "passed": true}
{"event": "done",        "passed": true, "summary": { "overall": "PASS", "results": […] }}
```

---

## Flutter Integration

### Install dependencies

```yaml
# pubspec.yaml
dependencies:
  http: ^1.2.0
  web_socket_channel: ^3.0.0
```

### REST — single JSON response

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<Map<String, dynamic>> testMyApp() async {
  final res = await http.post(
    Uri.parse('http://localhost:8888/test/harness'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'url':     'ws://localhost:9000/kem',
      'variant': 'ML-KEM-768',
    }),
  );
  return jsonDecode(res.body) as Map<String, dynamic>;
  // {"overall":"PASS","results":[{"name":"happy_ek_size","passed":true,...},...]}
}
```

### WebSocket — live streaming results

```dart
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

void runLiveTest() {
  final channel = WebSocketChannel.connect(
    Uri.parse('ws://localhost:8888/ws/test'),
  );

  // Send config once
  channel.sink.add(jsonEncode({
    'mode':    'harness',
    'url':     'ws://localhost:9000/kem',
    'variant': 'ML-KEM-768',
  }));

  // Listen for streaming events
  channel.stream.listen((raw) {
    final event = jsonDecode(raw as String) as Map<String, dynamic>;
    switch (event['event']) {
      case 'start':
        print('Test started: ${event['detail']}');
      case 'test_result':
        final ok = event['passed'] as bool;
        print('[${ok ? "✓" : "✗"}] ${event['test']}: ${event['detail']}');
      case 'done':
        final passed = event['passed'] as bool;
        print('RESULT: ${passed ? "PASS ✓" : "FAIL ✗"}');
        channel.sink.close();
      case 'error':
        print('ERROR: ${event['detail']}');
        channel.sink.close();
    }
  });
}
```

---

## WebSocket Protocol (Server Side)

Your Flutter app's KEM endpoint must implement:

```
C → S  {"action":"kem_hello",  "variant":"ML-KEM-768", "session":"<uuid>"}
S → C  {"action":"kem_pubkey", "ek":"<hex 1184 bytes>", "session":"<uuid>"}
C → S  {"action":"kem_encap",  "ct":"<hex 1088 bytes>", "session":"<uuid>"}
S → C  {"action":"kem_proof",  "tag":"<hex 32 bytes>",  "session":"<uuid>"}
       tag = HMAC-SHA256(key=shared_secret, msg=b"pqc-nexus-v1")
```

Error response (any step):
```
S → C  {"action":"kem_error", "code":"<str>", "detail":"<str>"}
```

See `pqc_tester/ws_harness/protocol.py` for the full spec.

---

## Tests

```bash
pytest                          # full suite
pytest tests/test_algorithms.py # quantum algorithms only
pytest tests/test_pqc.py        # ML-KEM parameter checks
pytest -v                       # verbose
```

---

## Contributing

1. Fork → branch → PR
2. All deps must remain open-source (MIT / Apache-2 / BSD)
3. New algorithms go in `algorithms/`, export from `algorithms/__init__.py`
4. New PQC tests go in `pqc_tester/ml_kem/`

---

## License

MIT — see [LICENSE](LICENSE).

All third-party dependencies are open-source (Apache 2.0 / MIT / BSD-3).
See [LICENSE](LICENSE) for the full dependency list.
