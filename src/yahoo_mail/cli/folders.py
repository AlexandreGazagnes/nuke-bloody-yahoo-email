from __future__ import annotations

import typer
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from yahoo_mail.cli import _get_client, _resolve_or_exit, app, console
from yahoo_mail.credentials import prompt_credentials


@app.command()
def login() -> None:
    """Set or update Yahoo credentials (saved to PWD.txt)."""
    prompt_credentials(console)


@app.command()
def folders() -> None:
    """List all folders with their message count."""
    client = _get_client()
    try:
        flist = client.list_folders()
    finally:
        client.logout()

    table = Table(title="Yahoo Mail — Folders", show_lines=True)
    table.add_column("#",        style="dim",     justify="right", no_wrap=True)
    table.add_column("Folder",   style="cyan",    no_wrap=True)
    table.add_column("Messages", style="magenta", justify="right")

    for idx, f in enumerate(flist, 1):
        count_str = str(f.count) if f.count >= 0 else "[dim]?[/dim]"
        table.add_row(str(idx), f.name, count_str)

    console.print(table)
    console.print(f"\n[dim]{len(flist)} folder(s) total.[/dim]")


@app.command()
def count(
    folder: str = typer.Argument(..., help="Folder name or alias (spam, trash, archive …)")
) -> None:
    """Count emails in a folder."""
    client = _get_client()
    try:
        real = _resolve_or_exit(client, folder)
        n    = client.count(real)
    finally:
        client.logout()

    console.print(f"[cyan]{real}[/cyan]: [bold magenta]{n}[/bold magenta] message(s)")


@app.command()
def stats(
    no_size: bool = typer.Option(False, "--no-size", help="Skip per-folder size scan (faster)"),
) -> None:
    """Show per-folder message count, unread count, and size."""
    client = _get_client()
    try:
        rows: list[tuple[str, int, int, int]] = []
        flist = client.list_folders()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description:<30}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
            transient=True,
        ) as bar:
            task = bar.add_task("Scanning …", total=len(flist))
            for folder_info in flist:
                bar.update(task, description=f"[cyan]{folder_info.name}[/cyan]")
                try:
                    status = client._imap.folder_status(
                        folder_info.name, [b"MESSAGES", b"UNSEEN"]
                    )
                    total  = int(status.get(b"MESSAGES", 0))
                    unseen = int(status.get(b"UNSEEN",   0))
                except Exception:
                    total, unseen = -1, -1

                if not no_size and total > 0:
                    try:
                        client._imap.select_folder(folder_info.name, readonly=True)
                        uids = client._imap.search(["ALL"])
                        size = 0
                        for i in range(0, len(uids), 1000):
                            batch = uids[i : i + 1000]
                            data  = client._imap.fetch(batch, ["RFC822.SIZE"])
                            size += sum(msg[b"RFC822.SIZE"] for msg in data.values())
                    except Exception:
                        size = -1
                else:
                    size = -1 if no_size else 0

                rows.append((folder_info.name, total, unseen, size))
                bar.advance(task)
    finally:
        client.logout()

    def fmt_size(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024  # type: ignore[assignment]
        return f"{n:.1f} TB"

    with_size = not no_size
    table = Table(
        title="Yahoo Mail — Folder Stats",
        show_lines=True,
        caption="[dim]use --no-size to skip size scan[/dim]" if with_size else "[dim]size scan skipped[/dim]",
    )
    table.add_column("#",      style="dim",    justify="right", no_wrap=True)
    table.add_column("Folder", style="cyan",   no_wrap=True)
    table.add_column("Total",  style="white",  justify="right")
    table.add_column("Unread", style="yellow", justify="right")
    if with_size:
        table.add_column("Size",     style="magenta", justify="right")
        table.add_column("Avg/mail", style="blue",    justify="right")

    grand_msgs = grand_unread = grand_size = 0

    for idx, (name, total, unseen, size) in enumerate(rows, 1):
        t_str = str(total)  if total  >= 0 else "[dim]?[/dim]"
        u_raw = str(unseen) if unseen >= 0 else "?"
        u_str = f"[bold yellow]{u_raw}[/bold yellow]" if unseen > 0 else f"[dim]{u_raw}[/dim]"
        row   = [str(idx), name, t_str, u_str]
        if with_size:
            s_str = fmt_size(size) if size >= 0 else "[dim]—[/dim]"
            a_str = fmt_size(size // total) if (size >= 0 and total > 0) else "[dim]—[/dim]"
            row  += [s_str, a_str]
        table.add_row(*row)
        if total  >= 0: grand_msgs   += total
        if unseen >= 0: grand_unread += unseen
        if size   >= 0: grand_size   += size

    grand_avg = fmt_size(grand_size // grand_msgs) if grand_msgs > 0 else "—"
    table.add_section()
    totals = ["", "[bold]TOTAL[/bold]",
              f"[bold]{grand_msgs}[/bold]",
              f"[bold yellow]{grand_unread}[/bold yellow]"]
    if with_size:
        totals += [f"[bold magenta]{fmt_size(grand_size)}[/bold magenta]",
                   f"[bold blue]{grand_avg}[/bold blue]"]
    table.add_row(*totals)
    console.print(table)
