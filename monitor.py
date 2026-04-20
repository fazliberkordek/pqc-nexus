"""
pqc-nexus TUI monitor
Run: python monitor.py
Run with WS target: python monitor.py --ws ws://localhost:8080/kem
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from typing import Any

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Log,
    Select,
    Static,
    TabbedContent,
    TabPane,
    Rule,
    Sparkline,
    ProgressBar,
    Digits,
)

# ── constants ──────────────────────────────────────────────────────────────────

ALGO_ROWS: list[tuple[str, str, str]] = [
    ("grover",             "Grover's Search",           "n=3 target=5"),
    ("deutsch-jozsa",      "Deutsch-Jozsa",             "balanced n=3"),
    ("bernstein-vazirani", "Bernstein-Vazirani",        "secret=10110"),
    ("simon",              "Simon's Algorithm",         "s=110"),
    ("shor",               "Shor's Factoring",          "N=15"),
    ("qft",                "Quantum Fourier Transform", "n=4"),
    ("qpe",                "Quantum Phase Estimation",  "phase=0.25"),
    ("teleport",           "Quantum Teleportation",     "α=β=1/√2"),
    ("bb84",               "BB84 QKD",                  "64 bits no-Eve"),
    ("vqe",                "VQE — H₂ Molecule",         "COBYLA iter=100"),
    ("qaoa",               "QAOA — MaxCut",             "p=1 4-cycle"),
    ("hhl",                "HHL Linear Solver",         "2×2 diagonal"),
]

VARIANTS = ["ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"]

_STATUS_ICON  = {"idle": "○", "running": "◌", "pass": "✓", "fail": "✗"}
_STATUS_COLOR = {"idle": "dim", "running": "yellow bold", "pass": "green bold", "fail": "red bold"}


def _badge(status: str) -> Text:
    t = Text(_STATUS_ICON[status])
    t.stylize(_STATUS_COLOR[status])
    return t


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ── algo dispatcher ────────────────────────────────────────────────────────────

def _dispatch_algo(key: str) -> dict:
    """Run a quantum algorithm by key. Returns result dict."""
    import algorithms as A

    match key:
        case "grover":
            return A.grover_search(n=3, target=5, shots=2048)
        case "deutsch-jozsa":
            return A.deutsch_jozsa(A.balanced_oracle(3), 3)
        case "bernstein-vazirani":
            return A.bernstein_vazirani("10110")
        case "simon":
            return A.simon("110", shots=1024)
        case "shor":
            return A.shor_factor(15)
        case "qft":
            circ = A.qft_circuit(4)
            return {"circuit_depth": circ.depth(), "n_qubits": 4}
        case "qpe":
            return A.quantum_phase_estimation(0.25, n_counting=4)
        case "teleport":
            return A.teleport()
        case "bb84":
            return A.bb84_qkd(n_bits=64, rng_seed=1)
        case "vqe":
            return A.vqe_h2(max_iter=100)
        case "qaoa":
            return A.qaoa_maxcut(p=1)
        case "hhl":
            return A.hhl_solve()
        case _:
            raise ValueError(f"Unknown algo: {key}")


def _result_metric(key: str, res: dict) -> str:
    """Extract the single most interesting metric from a result dict."""
    match key:
        case "grover":
            return f"found={res.get('found')} prob={res.get('top_probability', 0):.0%}"
        case "deutsch-jozsa":
            return res.get("verdict", "")
        case "bernstein-vazirani":
            return f"secret={'✓' if res.get('success') else '✗'} got={res.get('found')}"
        case "simon":
            return f"period={res.get('recovered')} ok={'✓' if res.get('success') else '✗'}"
        case "shor":
            return f"factors={res.get('factors')} via={res.get('method')}"
        case "qft":
            return f"depth={res.get('circuit_depth')}"
        case "qpe":
            return f"est={res.get('estimated_phase'):.4f} err={res.get('error'):.4f}"
        case "teleport":
            return "teleported ✓" if res.get("teleported") else "✗"
        case "bb84":
            return f"QBER={res.get('qber'):.3f} eve={'✓' if res.get('eavesdropping_detected') else '✗'}"
        case "vqe":
            return f"E={res.get('estimated_energy_hartree'):.4f} Ha chem_acc={'✓' if res.get('chemical_accuracy') else '✗'}"
        case "qaoa":
            return f"cut={res.get('cut_value')} bits={res.get('best_cut_bitstring')}"
        case "hhl":
            return f"cond={res.get('condition_number')} depth={res.get('circuit_depth')}"
        case _:
            return str(res)[:40]


def _algo_succeeded(key: str, res: dict) -> bool:
    match key:
        case "grover":           return res.get("success", False)
        case "deutsch-jozsa":    return res.get("verdict") in {"constant", "balanced"}
        case "bernstein-vazirani": return res.get("success", False)
        case "simon":            return res.get("success", False)
        case "shor":             return res.get("factors") is not None
        case "qft":              return res.get("circuit_depth", 0) > 0
        case "qpe":              return res.get("error", 1) < 0.1
        case "teleport":         return res.get("teleported", False)
        case "bb84":             return not res.get("eavesdropping_detected", True)
        case "vqe":              return res.get("chemical_accuracy", False)
        case "qaoa":             return res.get("cut_value", 0) > 0
        case "hhl":              return res.get("circuit_depth", 0) > 0
        case _:                  return True


# ── main app ───────────────────────────────────────────────────────────────────

class PQCMonitor(App):
    """pqc-nexus — Quantum Algorithm + PQC/ML-KEM Live Monitor"""

    TITLE = "pqc-nexus monitor"
    SUB_TITLE = "Quantum Algorithms · ML-KEM FIPS 203 · WebSocket Harness"

    CSS = """
    Screen {
        background: $surface;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 0 1;
    }

    /* ── algo tab ── */
    #algo-table {
        height: 1fr;
        border: solid $primary-darken-2;
        margin-bottom: 1;
    }

    #algo-btn-row {
        height: 3;
        align: left middle;
        padding: 0 1;
    }

    #algo-btn-row Button {
        margin-right: 1;
    }

    /* ── pqc tab ── */
    #pqc-controls {
        height: 3;
        align: left middle;
        padding: 0 1;
    }

    #pqc-controls Select {
        width: 20;
        margin-right: 1;
    }

    #conf-table {
        height: 18;
        border: solid $success-darken-2;
    }

    #attack-table {
        height: 1fr;
        border: solid $warning-darken-2;
    }

    .section-label {
        color: $text-muted;
        text-style: bold;
        padding: 0 0 0 1;
        margin-top: 1;
    }

    /* ── ws tab ── */
    #ws-input-row {
        height: 3;
        align: left middle;
        padding: 0 1;
    }

    #ws-url {
        width: 40;
        margin-right: 1;
    }

    #ws-variant {
        width: 18;
        margin-right: 1;
    }

    #ws-table {
        height: 1fr;
        border: solid $accent-darken-2;
        margin-top: 1;
    }

    #ws-status {
        padding: 0 1;
        color: $text-muted;
        height: 1;
    }

    /* ── log tab ── */
    #live-log {
        height: 1fr;
        border: solid $surface-lighten-1;
    }

    /* ── shared ── */
    .run-btn    { background: $primary;   color: $text; }
    .clear-btn  { background: $surface-darken-2; }
    .stop-btn   { background: $error-darken-1; }
    """

    BINDINGS = [
        Binding("ctrl+r", "run_all_algos",  "Run All Algos",  show=True),
        Binding("ctrl+p", "run_pqc",        "Run PQC Suite",  show=True),
        Binding("ctrl+l", "clear_log",      "Clear Log",      show=True),
        Binding("q",      "quit",           "Quit",           show=True),
    ]

    # reactive state
    _algo_status: dict[str, str] = {}
    _running_count: reactive[int] = reactive(0)

    def __init__(self, ws_url: str = ""):
        super().__init__()
        self._ws_url = ws_url
        self._algo_status = {key: "idle" for key, *_ in ALGO_ROWS}

    # ── compose ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("⚛  Algorithms", id="tab-algos"):
                yield self._compose_algo_tab()
            with TabPane("🔐 ML-KEM", id="tab-pqc"):
                yield self._compose_pqc_tab()
            with TabPane("🌐 WS Harness", id="tab-ws"):
                yield self._compose_ws_tab()
            with TabPane("📋 Logs", id="tab-logs"):
                yield Log(id="live-log", highlight=True, markup=True)
        yield Footer()

    def _compose_algo_tab(self) -> ComposeResult:
        yield DataTable(id="algo-table", cursor_type="row")
        with Horizontal(id="algo-btn-row"):
            yield Button("▶  Run All",      id="btn-run-all",   classes="run-btn")
            yield Button("▶  Run Selected", id="btn-run-sel",   classes="run-btn")
            yield Button("⏹  Stop",         id="btn-stop-algos",classes="stop-btn")
            yield Button("✕  Clear",         id="btn-clear-algos",classes="clear-btn")

    def _compose_pqc_tab(self) -> ComposeResult:
        with Horizontal(id="pqc-controls"):
            yield Select(
                [(v, v) for v in VARIANTS],
                value="ML-KEM-768",
                id="pqc-variant",
            )
            yield Button("▶  Conformance", id="btn-conf",    classes="run-btn")
            yield Button("⚔  Attack Suite",id="btn-attacks", classes="run-btn")
            yield Button("▶▶ Both",         id="btn-pqc-all", classes="run-btn")
        yield Label("Conformance Results", classes="section-label")
        yield DataTable(id="conf-table",   cursor_type="row")
        yield Label("Attack Probes",       classes="section-label")
        yield DataTable(id="attack-table", cursor_type="row")

    def _compose_ws_tab(self) -> ComposeResult:
        with Horizontal(id="ws-input-row"):
            yield Input(
                value=self._ws_url or "ws://localhost:8080/kem",
                placeholder="ws://host:port/path",
                id="ws-url",
            )
            yield Select(
                [(v, v) for v in VARIANTS],
                value="ML-KEM-768",
                id="ws-variant",
            )
            yield Button("▶  Connect & Test", id="btn-ws-run",  classes="run-btn")
            yield Button("✕  Clear",           id="btn-ws-clear",classes="clear-btn")
        yield Static("", id="ws-status")
        yield DataTable(id="ws-table", cursor_type="row")

    # ── on_mount ───────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._init_algo_table()
        self._init_conf_table()
        self._init_attack_table()
        self._init_ws_table()
        self._log("pqc-nexus monitor started.")

    def _init_algo_table(self) -> None:
        t: DataTable = self.query_one("#algo-table")
        t.add_columns("", "Algorithm", "Params", "Result", "ms", "Last Run")
        for key, label, params in ALGO_ROWS:
            t.add_row(_badge("idle"), label, params, "—", "—", "—", key=key)

    def _init_conf_table(self) -> None:
        t: DataTable = self.query_one("#conf-table")
        t.add_columns("", "Check", "Detail")

    def _init_attack_table(self) -> None:
        t: DataTable = self.query_one("#attack-table")
        t.add_columns("", "Probe", "Detail", "ms")

    def _init_ws_table(self) -> None:
        t: DataTable = self.query_one("#ws-table")
        t.add_columns("", "Test", "Detail", "ms")

    # ── button handlers ────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-run-all":    self._run_all_algos()
            case "btn-run-sel":    self._run_selected_algo()
            case "btn-stop-algos": self._stop_workers()
            case "btn-clear-algos":self._reset_algo_table()
            case "btn-conf":       self._run_conformance()
            case "btn-attacks":    self._run_attacks()
            case "btn-pqc-all":    self._run_conformance(); self._run_attacks()
            case "btn-ws-run":     self._run_ws()
            case "btn-ws-clear":   self._reset_ws_table()

    def action_run_all_algos(self) -> None:
        self._run_all_algos()

    def action_run_pqc(self) -> None:
        self._run_conformance()
        self._run_attacks()

    def action_clear_log(self) -> None:
        self.query_one("#live-log", Log).clear()

    # ── algo execution ─────────────────────────────────────────────────────────

    def _run_all_algos(self) -> None:
        for key, *_ in ALGO_ROWS:
            self._launch_algo(key)

    def _run_selected_algo(self) -> None:
        t: DataTable = self.query_one("#algo-table")
        if t.cursor_row < 0:
            return
        key = ALGO_ROWS[t.cursor_row][0]
        self._launch_algo(key)

    def _launch_algo(self, key: str) -> None:
        self._set_algo_status(key, "running")
        self._algo_worker(key)

    @work(thread=True, exclusive=False)
    def _algo_worker(self, key: str) -> None:
        t0 = time.perf_counter()
        try:
            result = _dispatch_algo(key)
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            success = _algo_succeeded(key, result)
            metric  = _result_metric(key, result)
            self.call_from_thread(self._update_algo_row, key, success, metric, elapsed)
            self.call_from_thread(
                self._log,
                f"[{'green' if success else 'red'}]{key}[/] → {metric} ({elapsed}ms)"
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            self.call_from_thread(self._update_algo_row, key, False, str(exc)[:60], elapsed)
            self.call_from_thread(self._log, f"[red]{key} ERROR:[/] {exc}")

    def _update_algo_row(self, key: str, success: bool, metric: str, elapsed: float) -> None:
        status = "pass" if success else "fail"
        self._set_algo_status(key, status)
        t: DataTable = self.query_one("#algo-table")
        t.update_cell(key, "Result",   metric,         update_width=True)
        t.update_cell(key, "ms",       f"{elapsed}",   update_width=False)
        t.update_cell(key, "Last Run", _now(),         update_width=False)

    def _set_algo_status(self, key: str, status: str) -> None:
        self._algo_status[key] = status
        t: DataTable = self.query_one("#algo-table")
        t.update_cell(key, "", _badge(status))

    def _reset_algo_table(self) -> None:
        t: DataTable = self.query_one("#algo-table")
        for key, *_ in ALGO_ROWS:
            t.update_cell(key, "",        _badge("idle"))
            t.update_cell(key, "Result",  "—")
            t.update_cell(key, "ms",      "—")
            t.update_cell(key, "Last Run","—")
        self._log("Algorithm table cleared.")

    def _stop_workers(self) -> None:
        self.workers.cancel_all()
        for key, *_ in ALGO_ROWS:
            if self._algo_status.get(key) == "running":
                self._set_algo_status(key, "idle")
        self._log("[yellow]All workers cancelled.[/]")

    # ── PQC conformance ────────────────────────────────────────────────────────

    def _run_conformance(self) -> None:
        variant = str(self.query_one("#pqc-variant", Select).value)
        self._log(f"[cyan]Conformance:[/] {variant} …")
        self._conf_worker(variant)

    @work(thread=True, exclusive=False)
    def _conf_worker(self, variant: str) -> None:
        from pqc_tester.ml_kem.conformance import ConformanceTester
        t0 = time.perf_counter()
        report = ConformanceTester(variant).run()
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        summary = report.summary()
        self.call_from_thread(self._populate_conf_table, variant, summary, elapsed)

    def _populate_conf_table(self, variant: str, summary: dict, elapsed: float) -> None:
        t: DataTable = self.query_one("#conf-table")
        t.clear()
        overall = "pass" if summary["passed"] else "fail"
        self._log(
            f"[cyan]Conformance[/] {variant} → "
            f"[{'green' if summary['passed'] else 'red'}]{overall.upper()}[/] ({elapsed}ms)"
        )
        for item in summary["details"]:
            status = "pass" if item["passed"] else "fail"
            t.add_row(_badge(status), item["name"], item["detail"])

    # ── PQC attacks ────────────────────────────────────────────────────────────

    def _run_attacks(self) -> None:
        variant = str(self.query_one("#pqc-variant", Select).value)
        self._log(f"[yellow]Attack suite:[/] {variant} …")
        self._attack_worker(variant)

    @work(thread=True, exclusive=False)
    def _attack_worker(self, variant: str) -> None:
        from pqc_tester.ml_kem.attacks import AttackSuite
        t0 = time.perf_counter()
        report = AttackSuite(variant).run()
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        summary = report.summary()
        self.call_from_thread(self._populate_attack_table, variant, summary, elapsed)

    def _populate_attack_table(self, variant: str, summary: dict, elapsed: float) -> None:
        t: DataTable = self.query_one("#attack-table")
        t.clear()
        overall = "pass" if summary["all_passed"] else "fail"
        self._log(
            f"[yellow]Attacks[/] {variant} → "
            f"[{'green' if summary['all_passed'] else 'red'}]{overall.upper()}[/] ({elapsed}ms)"
        )
        for probe in summary["probes"]:
            status = "pass" if probe["passed"] else "fail"
            ms = f"{probe['timing_ms']:.2f}" if probe.get("timing_ms") else "—"
            t.add_row(_badge(status), probe["name"], probe["detail"], ms)

    # ── WS harness ─────────────────────────────────────────────────────────────

    def _run_ws(self) -> None:
        url     = self.query_one("#ws-url",     Input).value.strip()
        variant = str(self.query_one("#ws-variant", Select).value)
        if not url:
            self._log("[red]WS URL is empty.[/]")
            return
        self.query_one("#ws-status", Static).update(f"[yellow]Connecting to {url} …[/]")
        self._log(f"[cyan]WS harness:[/] {variant} → {url}")
        self._ws_worker(url, variant)

    @work(exclusive=True)
    async def _ws_worker(self, url: str, variant: str) -> None:
        from pqc_tester.ws_harness.client import WSTestClient
        t0 = time.perf_counter()
        try:
            client = WSTestClient(url, variant, timeout=10.0)
            session = await client.run_all()
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            self._populate_ws_table(session.summary(), elapsed)
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            self.query_one("#ws-status", Static).update(f"[red]Error: {exc}[/]")
            self._log(f"[red]WS error:[/] {exc}")

    def _populate_ws_table(self, summary: dict, elapsed: float) -> None:
        t: DataTable = self.query_one("#ws-table")
        t.clear()
        overall = summary["overall"]
        color = "green" if overall == "PASS" else "red"
        self.query_one("#ws-status", Static).update(
            f"[{color}]{overall}[/]  {summary['variant']} @ {summary['url']}  ({elapsed}ms total)"
        )
        self._log(
            f"[cyan]WS[/] {summary['variant']} → [{color}]{overall}[/] ({elapsed}ms)"
        )
        for r in summary["results"]:
            status = "pass" if r["passed"] else "fail"
            ms = f"{r['duration_ms']:.1f}" if r["duration_ms"] else "—"
            t.add_row(_badge(status), r["test"], r["detail"], ms)

    def _reset_ws_table(self) -> None:
        self.query_one("#ws-table").clear()
        self.query_one("#ws-status", Static).update("")
        self._log("WS table cleared.")

    # ── log helper ─────────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.query_one("#live-log", Log).write_line(f"[dim]{ts}[/]  {msg}")


# ── entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ws = ""
    if "--ws" in sys.argv:
        idx = sys.argv.index("--ws")
        if idx + 1 < len(sys.argv):
            ws = sys.argv[idx + 1]
    PQCMonitor(ws_url=ws).run()
