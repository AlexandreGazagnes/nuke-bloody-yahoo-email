from __future__ import annotations

import typer

from yahoo_mail.cli import _get_client, _resolve_or_exit, app, console


@app.command()
def purge(
    folder: str  = typer.Argument(..., help="Folder to empty (name or alias)"),
    yes:    bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Permanently delete ALL emails in a folder."""
    client = _get_client()
    try:
        real = _resolve_or_exit(client, folder)
        n    = client.count(real)

        if n == 0:
            console.print(f"[cyan]{real}[/cyan] is already empty.")
            return

        if not yes:
            typer.confirm(f"Permanently delete all {n} message(s) in '{real}'?", abort=True)

        with console.status(f"Deleting {n} messages from [cyan]{real}[/cyan] …"):
            deleted = client.purge(real)
    finally:
        client.logout()

    console.print(
        f"[green]✓[/green] Permanently deleted [bold]{deleted}[/bold] message(s) "
        f"from [cyan]{real}[/cyan]."
    )


@app.command()
def clean(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Permanently delete all emails in Spam and Trash."""
    client = _get_client()
    try:
        targets: list[tuple[str, int]] = []
        for alias in ("spam", "trash"):
            real = client.resolve(alias)
            if real:
                targets.append((real, client.count(real)))
            else:
                console.print(f"[yellow]Could not find '{alias}' folder — skipping.[/yellow]")

        if not targets:
            console.print("Nothing to clean.")
            return

        console.print("[bold]Folders to clean:[/bold]")
        for name, n in targets:
            console.print(f"  [cyan]{name}[/cyan]: {n} message(s)")

        if not yes:
            typer.confirm("\nPermanently delete all the above?", abort=True)

        total = 0
        for name, _ in targets:
            with console.status(f"Purging [cyan]{name}[/cyan] …"):
                total += client.purge(name)
    finally:
        client.logout()

    console.print(f"\n[green]✓ Done.[/green] {total} message(s) permanently deleted.")


@app.command(name="batch-nuke")
def batch_nuke(
    folder: str   = typer.Argument(..., help="Folder to nuke (name or alias)"),
    yes:    bool  = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    batch:  int   = typer.Option(1000,  "--batch", "-b", help="UIDs per round (default 1000)"),
    wait:   float = typer.Option(3.0,   "--wait",  "-w", help="Seconds between rounds (default 3)"),
) -> None:
    """Loop-delete all emails in a folder batch by batch until empty. Permanent after each round."""
    client = _get_client()
    try:
        real = _resolve_or_exit(client, folder)
        n    = client.count(real)

        if n == 0:
            console.print(f"[cyan]{real}[/cyan] is already empty.")
            return

        console.print(f"[bold red]Batch-nuke[/bold red] [cyan]{real}[/cyan]")
        console.print(f"  Messages  : [bold]{n}[/bold]")
        console.print(f"  Batch size: [bold]{batch}[/bold] UIDs/round")
        console.print(f"  Wait      : [bold]{wait}s[/bold] between rounds")
        console.print(f"  Rounds    : ~[bold]{-(-n // batch)}[/bold]\n")

        if not yes:
            typer.confirm("Permanently delete all messages in loop?", abort=True)

        console.print()

        def on_round(round_num: int, deleted: int, total: int, remaining: int) -> None:
            remaining_str = str(remaining) if remaining else "[green]0 — folder empty[/green]"
            console.print(
                f"  Round [bold]{round_num:>4}[/bold] │ "
                f"deleted [yellow]{deleted:>5}[/yellow] │ "
                f"total [magenta]{total:>8}[/magenta] │ "
                f"remaining {remaining_str}"
                + (f" │ waiting {wait}s …" if remaining else "")
            )

        total = client.batch_nuke(real, batch=batch, wait=wait, on_round=on_round)
    finally:
        client.logout()

    console.print(
        f"\n[green]✓ Done.[/green] [bold]{total}[/bold] messages permanently deleted "
        f"from [cyan]{real}[/cyan]."
    )


@app.command(name="batch-clean")
def batch_clean(
    yes:   bool  = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    batch: int   = typer.Option(1000,  "--batch", "-b", help="UIDs per round (default 1000)"),
    wait:  float = typer.Option(3.0,   "--wait",  "-w", help="Seconds between rounds (default 3)"),
) -> None:
    """Batch-nuke Spam AND Trash — loop until both are completely empty."""
    client = _get_client()
    try:
        targets: list[tuple[str, int]] = []
        for alias in ("spam", "trash"):
            real = client.resolve(alias)
            if real:
                targets.append((real, client.count(real)))
            else:
                console.print(f"[yellow]Could not find '{alias}' folder — skipping.[/yellow]")

        if not targets:
            console.print("Nothing to clean.")
            return

        console.print("[bold red]Batch-clean targets:[/bold red]")
        for name, n in targets:
            console.print(f"  [cyan]{name}[/cyan]: {n} messages (~{-(-n // batch)} rounds)")
        console.print(f"\n  Batch: {batch} UIDs/round │ Wait: {wait}s between rounds\n")

        if not yes:
            typer.confirm("Permanently delete all the above in loop?", abort=True)

        grand_total = 0
        for name, _ in targets:
            console.print(f"\n[bold]── {name} ──[/bold]")

            def on_round(round_num: int, deleted: int, total: int, remaining: int) -> None:
                remaining_str = str(remaining) if remaining else "[green]0 — folder empty[/green]"
                console.print(
                    f"  Round [bold]{round_num:>4}[/bold] │ "
                    f"deleted [yellow]{deleted:>5}[/yellow] │ "
                    f"total [magenta]{total:>8}[/magenta] │ "
                    f"remaining {remaining_str}"
                    + (f" │ waiting {wait}s …" if remaining else "")
                )

            grand_total += client.batch_nuke(name, batch=batch, wait=wait, on_round=on_round)
    finally:
        client.logout()

    console.print(f"\n[green]✓ Done.[/green] [bold]{grand_total}[/bold] messages permanently deleted.")


@app.command(name="delete-from")
def delete_from_folder(
    folder: str  = typer.Argument(..., help="Folder to search in (name or alias)"),
    sender: str  = typer.Argument(..., help="Sender address to delete (e.g. noreply@spam.com)"),
    yes:    bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete all emails from a specific sender in one folder."""
    client = _get_client()
    try:
        real = _resolve_or_exit(client, folder)
        n    = client.count_from_in(real, sender)

        if n == 0:
            console.print(f"No emails from [cyan]{sender}[/cyan] found in [cyan]{real}[/cyan].")
            return

        console.print(
            f"Found [bold]{n}[/bold] email(s) from [cyan]{sender}[/cyan] in [cyan]{real}[/cyan]."
        )

        if not yes:
            typer.confirm(f"Permanently delete all {n} message(s)?", abort=True)

        with console.status("Deleting …"):
            deleted = client.delete_from(real, sender)
    finally:
        client.logout()

    console.print(
        f"[green]✓[/green] Deleted [bold]{deleted}[/bold] message(s) from "
        f"[cyan]{sender}[/cyan] in [cyan]{real}[/cyan]."
    )


@app.command(name="rm-folder")
def rm_folder(
    folder: str  = typer.Argument(..., help="Folder to delete entirely (name or alias)"),
    yes:    bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a folder AND permanently remove all its contents."""
    client = _get_client()
    try:
        real = _resolve_or_exit(client, folder)
        n    = client.count(real)

        if not yes:
            typer.confirm(
                f"Delete folder '{real}' and its {n} message(s) permanently?", abort=True
            )

        with console.status(f"Deleting folder [cyan]{real}[/cyan] …"):
            client.delete_folder(real)
    finally:
        client.logout()

    console.print(f"[green]✓[/green] Folder [cyan]{real}[/cyan] deleted.")
