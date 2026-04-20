"""Rich terminal reporter for WS harness and conformance results."""
from __future__ import annotations
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


class HarnessReporter:
    @staticmethod
    def print_ws_session(summary: dict) -> None:
        status = "[bold green]PASS[/]" if summary["overall"] == "PASS" else "[bold red]FAIL[/]"
        console.print(Panel(
            f"[bold]{summary['variant']}[/] @ {summary['url']}\nOverall: {status}",
            title="pqc-nexus WS Harness",
            border_style="cyan",
        ))

        table = Table(box=box.SIMPLE_HEAD, show_header=True)
        table.add_column("Test", style="cyan", no_wrap=True)
        table.add_column("Result", justify="center")
        table.add_column("Detail")
        table.add_column("ms", justify="right", style="dim")

        for r in summary["results"]:
            badge = "[green]✓[/]" if r["passed"] else "[red]✗[/]"
            table.add_row(
                r["test"], badge, r["detail"],
                f"{r['duration_ms']:.1f}" if r["duration_ms"] else "",
            )
        console.print(table)

    @staticmethod
    def print_conformance(summary: dict) -> None:
        status = "[bold green]PASS[/]" if summary["passed"] else "[bold red]FAIL[/]"
        console.print(Panel(
            f"[bold]{summary['variant']}[/] — {summary['total']} checks — {status}",
            title="ML-KEM Conformance",
            border_style="magenta",
        ))

        table = Table(box=box.SIMPLE_HEAD)
        table.add_column("Check", style="magenta")
        table.add_column("Result", justify="center")
        table.add_column("Detail")

        for d in summary["details"]:
            badge = "[green]✓[/]" if d["passed"] else "[red]✗[/]"
            table.add_row(d["name"], badge, d["detail"])
        console.print(table)

    @staticmethod
    def print_attacks(summary: dict) -> None:
        status = "[bold green]PASS[/]" if summary["all_passed"] else "[bold red]FAIL[/]"
        console.print(Panel(
            f"[bold]{summary['variant']}[/] attack probes — {status}",
            title="Attack Suite",
            border_style="yellow",
        ))

        table = Table(box=box.SIMPLE_HEAD)
        table.add_column("Probe", style="yellow")
        table.add_column("Result", justify="center")
        table.add_column("Detail")
        table.add_column("ms", justify="right", style="dim")

        for p in summary["probes"]:
            badge = "[green]✓[/]" if p["passed"] else "[red]✗[/]"
            table.add_row(
                p["name"], badge, p["detail"],
                f"{p['timing_ms']:.2f}" if p.get("timing_ms") else "",
            )
        console.print(table)
