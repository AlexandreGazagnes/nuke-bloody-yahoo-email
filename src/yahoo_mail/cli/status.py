from __future__ import annotations

from rich.table import Table

from yahoo_mail.cli import _get_client, app, console


@app.command(name="request-status")
def request_status() -> None:
    """Check connection health, server latency, capabilities, and rate-limit alerts."""
    client = _get_client()
    try:
        info = client.check_status()
    finally:
        client.logout()

    latency       = info["latency_ms"]
    latency_style = "green" if latency < 300 else ("yellow" if latency < 1000 else "red")
    console.print(f"NOOP latency : [{latency_style}]{latency} ms[/{latency_style}]")

    rate_caps  = [c for c in info["capabilities"] if any(k in c.upper() for k in ("LIMIT", "QUOTA", "THROTTL"))]
    other_caps = [c for c in info["capabilities"] if c not in rate_caps]

    cap_table = Table(title="Server capabilities", show_header=False, box=None, padding=(0, 2))
    cap_table.add_column("cap")
    for c in rate_caps:
        cap_table.add_row(f"[bold yellow]{c}[/bold yellow]")
    for c in other_caps:
        cap_table.add_row(f"[dim]{c}[/dim]")
    console.print(cap_table)

    if info["alerts"]:
        console.print("\n[bold red]Server alerts / untagged responses:[/bold red]")
        for tag, text in info["alerts"]:
            console.print(f"  [yellow]{tag}[/yellow]  {text}")
    else:
        console.print("\n[green]No server alerts.[/green] No rate-limit signals detected.")
