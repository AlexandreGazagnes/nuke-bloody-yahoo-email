# Yahoo Mail CLI

A Python command-line tool to manage Yahoo Mail at scale via IMAP — list folders, count emails, bulk-delete, move, purge spam/trash, and delete by sender.

## Requirements

- Python 3.12+
- A Yahoo **App Password** (not your regular Yahoo password)

### Get an App Password

1. Go to [myaccount.yahoo.com](https://myaccount.yahoo.com)
2. Security → Two-step verification (enable if not already)
3. Security → Generate app password
4. Copy the 16-character token — you will paste it on first run

## Setup

```bash
bash setup.sh          # creates .venv and installs dependencies
source .venv/bin/activate
pip install -e .       # registers the `yahoo-mail` shell command
```

## Usage

```bash
yahoo-mail --help
```

### Commands

| Command | Description |
|---|---|
| `yahoo-mail login` | Set or update credentials (saved to `PWD.txt`) |
| `yahoo-mail folders` | List all folders with message counts |
| `yahoo-mail count <folder>` | Count emails in a folder |
| `yahoo-mail stats` | Per-folder totals, unread counts, and sizes |
| `yahoo-mail purge <folder>` | Permanently delete all emails in a folder (single pass) |
| `yahoo-mail clean` | Permanently delete all Spam + Trash (single pass) |
| `yahoo-mail batch-nuke <folder>` | Loop-delete all emails in a folder, round by round |
| `yahoo-mail batch-clean` | Loop-delete Spam + Trash, round by round until empty |
| `yahoo-mail delete-from <folder> <sender>` | Delete all emails from a sender in one folder |
| `yahoo-mail nuke-sender <sender>` | Delete all emails from a sender across every folder |
| `yahoo-mail batch-nuke-sender <sender>` | Loop-delete all emails from a sender, round by round |
| `yahoo-mail move <src> <dst>` | Move all emails from one folder to another |
| `yahoo-mail rm-folder <folder>` | Delete folder and all its contents |
| `yahoo-mail request-status` | Connection health, latency, and server capabilities |

### Options for destructive commands

All destructive commands accept `--yes` / `-y` to skip the confirmation prompt.

`batch-nuke`, `batch-clean`, and `batch-nuke-sender` also accept:

| Option | Default | Description |
|---|---|---|
| `--batch` / `-b` | `1000` | UIDs processed per round |
| `--wait` / `-w` | `3.0` | Seconds to pause between rounds |

### Folder aliases

You can use short aliases instead of exact IMAP names:

| Alias | Resolves to |
|---|---|
| `spam` | `Bulk Mail` (Yahoo's internal IMAP name) |
| `trash` | `Trash` |
| `archive` | `Archive` |
| `sent` | `Sent` |
| `drafts` | `Draft` |
| `inbox` | `INBOX` |

### Examples

```bash
# See what you have
yahoo-mail folders
yahoo-mail stats --no-size

# Count spam
yahoo-mail count spam

# Nuke spam + trash — single pass, asks for confirmation
yahoo-mail clean

# Loop-delete spam + trash round by round (safer for very large mailboxes)
yahoo-mail batch-clean
yahoo-mail batch-clean --batch 5000 --wait 1

# Empty the Archive folder round by round
yahoo-mail batch-nuke Archive --batch 5000 --wait 1

# Delete all emails from a specific sender in your inbox
yahoo-mail delete-from inbox newsletters@example.com

# Delete all emails from a sender across every folder
yahoo-mail nuke-sender notifications@spam.com

# Move everything from Archive to Inbox
yahoo-mail move Archive INBOX

# Delete an old custom folder entirely
yahoo-mail rm-folder "Old Newsletter"
```

## Credentials

On first run, the CLI prompts for your Yahoo email and App Password, then writes them to `PWD.txt` with permissions `600` (owner read/write only). Subsequent runs read from `PWD.txt` automatically.

To update credentials at any time:

```bash
yahoo-mail login
```

## Yahoo IMAP notes

| Setting | Value |
|---|---|
| Host | `imap.mail.yahoo.com` |
| Port | `993` (SSL) |
| Auth | App Password required |

- Yahoo rate-limits IMAP connections — the tool adds a 0.5s delay between 1000-UID batches to stay under the limit.
- Yahoo calls Spam **"Bulk Mail"** internally over IMAP. The `spam` alias handles this automatically.
- The IMAP `MOVE` extension (RFC 6851) is used when available; falls back to COPY + DELETE otherwise.
- For very large mailboxes, prefer `batch-nuke` / `batch-clean` over `purge` / `clean` — they expunge after every round so progress is permanent even if the connection drops.

## Project structure

```
src/yahoo_mail/
    models.py        Data shapes (FolderInfo, callback types)
    constants.py     IMAP config, folder aliases
    credentials.py   PWD.txt I/O
    client.py        YahooMailClient — all IMAP logic
    benchmark.py     Dev tool: measures throughput per batch strategy
    __main__.py      python -m yahoo_mail entry point
    cli/             One file per command group
        folders.py   login, folders, count, stats
        delete.py    purge, clean, batch-nuke, batch-clean, delete-from, rm-folder
        sender.py    nuke-sender, batch-nuke-sender
        move.py      move
        status.py    request-status

pyproject.toml       Dependencies + yahoo-mail entry point
PWD.txt              Created on first run (never commit)
```

## Benchmark

To find the optimal batch size and wait time for your mailbox:

```bash
python -m yahoo_mail.benchmark --folder Bulk
python -m yahoo_mail.benchmark --folder Archive --estimate 200000
```

> **Warning:** the benchmark deletes real emails — one batch per strategy tested.
