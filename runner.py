"""CLI entry point for pqc-nexus."""
from __future__ import annotations
from typing import Optional
import typer
from rich.console import Console

app = typer.Typer(
    name="pqc-nexus",
    help="Quantum algorithm runner + ML-KEM WebSocket compliance tester",
    add_completion=False,
)
console = Console()


@app.command("test-pqc")
def test_pqc(
    variant: str = typer.Option("ML-KEM-768", help="ML-KEM-512 | ML-KEM-768 | ML-KEM-1024"),
    url: Optional[str] = typer.Option(None, help="WebSocket URL of app under test"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON instead of tables"),
):
    """Run ML-KEM conformance + attack probes. Optionally connect to a live app via WebSocket."""
    from pqc_tester.runner import run_suite
    run_suite(variant=variant, ws_url=url, output_json=json_out)


@app.command("run-algo")
def run_algo(
    name: str = typer.Argument(help=(
        "Algorithm to run: grover | deutsch-jozsa | bernstein-vazirani | simon | "
        "shor | qft | qpe | teleport | bb84 | vqe | qaoa | hhl"
    )),
):
    """Run a single quantum algorithm with default parameters."""
    import json

    dispatch = {
        "grover": lambda: __import__("algorithms").grover_search(n=3, target=5),
        "deutsch-jozsa": lambda: __import__("algorithms").deutsch_jozsa(
            __import__("algorithms").balanced_oracle(3), 3
        ),
        "bernstein-vazirani": lambda: __import__("algorithms").bernstein_vazirani("10110"),
        "simon": lambda: __import__("algorithms").simon("110"),
        "shor": lambda: __import__("algorithms").shor_factor(15),
        "qft": lambda: {"circuit_depth": __import__("algorithms").qft_circuit(4).depth()},
        "qpe": lambda: __import__("algorithms").quantum_phase_estimation(0.25),
        "teleport": lambda: __import__("algorithms").teleport(),
        "bb84": lambda: __import__("algorithms").bb84_qkd(n_bits=64, rng_seed=1),
        "vqe": lambda: __import__("algorithms").vqe_h2(max_iter=100),
        "qaoa": lambda: __import__("algorithms").qaoa_maxcut(p=1),
        "hhl": lambda: __import__("algorithms").hhl_solve(),
    }

    if name not in dispatch:
        console.print(f"[red]Unknown algorithm:[/] {name}")
        console.print(f"Available: {', '.join(dispatch)}")
        raise typer.Exit(1)

    console.print(f"[cyan]Running {name}...[/]")
    result = dispatch[name]()
    console.print_json(json.dumps(result, default=str))


if __name__ == "__main__":
    app()
