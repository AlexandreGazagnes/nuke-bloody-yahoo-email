#!/usr/bin/env python3
"""
benchmark.py — find the fastest batch-nuke strategy for your inbox.

Runs ONE real batch per strategy (this DELETES real emails!), measures the
raw IMAP operation time, then extrapolates the total time for various inbox
sizes and picks the winner.

Usage:
    python -m yahoo_mail.benchmark
    python -m yahoo_mail.benchmark --folder Archive
    python -m yahoo_mail.benchmark --estimate 200000
"""

from __future__ import annotations

import argparse
import sys
import time

from rich import box
from rich.console import Console
from rich.table import Table

from yahoo_mail.client import YahooMailClient
from yahoo_mail.credentials import read_credentials

console = Console()

STRATEGIES: list[tuple[int, float]] = [
    (1_000,   0.3),
    (5_000,   1.0),
    (10_000,  3.0),
    (15_000,  5.0),
    (50_000, 30.0),
]

DEFAULT_ESTIMATES = [10_000, 50_000, 100_000]


def fmt_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m = seconds / 60
    if m < 60:
        return f"{m:.1f}m"
    return f"{m / 60:.1f}h"


def ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark batch-nuke strategies")
    parser.add_argument("--folder",   default="spam",
                        help="Folder to test against (default: spam)")
    parser.add_argument("--estimate", type=int, default=None,
                        help="Extra inbox size to estimate, e.g. 200000")
    args = parser.parse_args()

    estimates = DEFAULT_ESTIMATES[:]
    if args.estimate and args.estimate not in estimates:
        estimates.append(args.estimate)
        estimates.sort()

    email, password = read_credentials()
    if not email or not password:
        console.print("[red]PWD.txt not found or incomplete. Run: yahoo-mail login[/red]")
        sys.exit(1)

    console.print()
    console.print("[bold cyan]Yahoo Mail — Batch Nuke Benchmark[/bold cyan]")
    console.print(f"  Folder : [cyan]{args.folder}[/cyan]")
    console.print(f"  Account: [cyan]{email}[/cyan]")
    console.print()

    console.print("Connecting …", end=" ")
    try:
        client = YahooMailClient(email, password)
        console.print("[green]OK[/green]\n")
    except Exception as exc:
        console.print(f"[red]FAILED[/red]: {exc}")
        sys.exit(1)

    try:
        resolved = client.resolve(args.folder)
        if not resolved:
            console.print(f"[red]Folder not found:[/red] {args.folder!r}")
            sys.exit(1)

        available = client.count(resolved)
        console.print(
            f"[cyan]{resolved}[/cyan]: [bold]{available:,}[/bold] messages available\n"
        )

        if available == 0:
            console.print("[yellow]Folder is empty — nothing to benchmark.[/yellow]")
            sys.exit(0)

        console.rule("[bold yellow]! WARNING !")
        console.print(
            f"  This benchmark permanently deletes emails from [cyan]{resolved}[/cyan].\n"
            "  It runs one real batch per strategy to measure IMAP speed.\n"
            "  Press [bold]Ctrl-C[/bold] now to abort.\n"
        )
        console.rule()
        console.print()

        results: list[dict] = []

        for batch_size, wait_time in STRATEGIES:
            remaining = client.count(resolved)

            if remaining == 0:
                console.print(
                    f"[yellow]batch={batch_size:>6,}  wait={wait_time}s[/yellow]  "
                    "[dim]— folder empty, skipped[/dim]"
                )
                results.append({"batch": batch_size, "wait": wait_time,
                                 "tested": 0, "op_time": None})
                continue

            test_size = min(batch_size, remaining)
            label = f"batch=[yellow]{batch_size:>6,}[/yellow]  wait=[yellow]{wait_time:>4}s[/yellow]"
            console.print(f"  Testing {label}  ({test_size:,} emails) …", end=" ")

            # One timed round using raw sequence-number STORE — avoids both
            # SEARCH ALL and UID FETCH which Yahoo rejects on very large folders.
            # Sub-batched to 1000 per command (Yahoo MESSAGELIMIT).
            client._imap.select_folder(resolved)
            seq_end = min(test_size, remaining)

            t0 = time.perf_counter()
            for sub_start in range(1, seq_end + 1, 1000):
                sub_end = min(sub_start + 999, seq_end)
                typ, _data = client._imap._imap.store(
                    f"{sub_start}:{sub_end}", "+FLAGS.SILENT", "(\\Deleted)"
                )
                if typ != "OK":
                    raise RuntimeError(f"STORE {sub_start}:{sub_end} failed: {_data}")
            client._imap.expunge()
            op_time = time.perf_counter() - t0

            eps         = test_size / op_time
            round_total = op_time + wait_time

            console.print(
                f"[green]{op_time:.2f}s[/green] IMAP  "
                f"([dim]{eps:.0f} e/s, round total {fmt_time(round_total)}[/dim])"
            )
            results.append({
                "batch":       batch_size,
                "wait":        wait_time,
                "tested":      test_size,
                "op_time":     op_time,
                "eps":         eps,
                "round_total": round_total,
            })

    finally:
        client.logout()

    valid = [r for r in results if r.get("op_time") is not None]

    if not valid:
        console.print("\n[red]No valid measurements (folder had too few emails).[/red]")
        sys.exit(1)

    ref_n = max(estimates)

    def estimated_total(r: dict, n: int) -> float:
        rounds       = ceil_div(n, r["batch"])
        op_per_round = r["batch"] / r["eps"]
        return rounds * (op_per_round + r["wait"])

    scores   = [estimated_total(r, ref_n) for r in valid]
    best_idx = scores.index(min(scores))

    console.print()
    table = Table(
        title=f"[bold]Benchmark Results[/bold]  (extrapolated for {ref_n:,} emails)",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
        highlight=True,
    )
    table.add_column("Batch",       justify="right")
    table.add_column("Wait",        justify="right")
    table.add_column("Tested",      justify="right")
    table.add_column("IMAP time",   justify="right")
    table.add_column("Speed",       justify="right")
    table.add_column("Round total", justify="right")
    for n in estimates:
        label = f"{n // 1000}k" if n < 1_000_000 else f"{n / 1_000_000:.1f}M"
        table.add_column(f"Est. {label}", justify="right")
    table.add_column("Rank", justify="center")

    ranked   = sorted(range(len(valid)), key=lambda i: scores[i])
    rank_map = {idx: pos + 1 for pos, idx in enumerate(ranked)}

    for i, r in enumerate(valid):
        is_best  = (i == best_idx)
        est_cols = [fmt_time(estimated_total(r, n)) for n in estimates]
        rank_str = "[bold green]#1 BEST[/bold green]" if is_best else f"#{rank_map[i]}"
        table.add_row(
            f"{r['batch']:,}",
            f"{r['wait']}s",
            f"{r['tested']:,}",
            f"{r['op_time']:.2f}s",
            f"{r['eps']:.0f} e/s",
            fmt_time(r["round_total"]),
            *est_cols,
            rank_str,
            style="bold green" if is_best else "",
        )

    console.print(table)

    best = valid[best_idx]
    console.print()
    console.print(
        f"[bold green]Best strategy:[/bold green]  "
        f"batch=[bold]{best['batch']:,}[/bold]  wait=[bold]{best['wait']}s[/bold]  "
        f"(processes {ref_n:,} emails in ~[bold]{fmt_time(scores[best_idx])}[/bold])"
    )
    console.print()
    console.print(
        "[dim]Run command:[/dim]\n"
        f"  [bold]yahoo-mail batch-nuke {args.folder} "
        f"--batch {best['batch']} --wait {best['wait']} --yes[/bold]"
    )
    console.print()


if __name__ == "__main__":
    main()
