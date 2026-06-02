"""
Yahoo Mail IMAP client.

Yahoo IMAP endpoint : imap.mail.yahoo.com:993 (SSL)
Auth               : App Password required (NOT your Yahoo account password)
                     myaccount.yahoo.com → Security → App passwords

Yahoo names its Spam folder "Bulk Mail" over IMAP — this module resolves
common aliases automatically (spam → Bulk Mail, trash → Trash, etc.).
"""

from __future__ import annotations

import time

from imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError

from yahoo_mail.constants import ALIASES, BATCH_SIZE, DELAY, IMAP_HOST, IMAP_PORT
from yahoo_mail.models import (
    BatchCB,
    FolderDelCB,
    FolderInfo,
    ProgressCB,
    SenderBatchCB,
)


class YahooMailClient:
    def __init__(self, email: str, password: str) -> None:
        self._imap = IMAPClient(IMAP_HOST, port=IMAP_PORT, ssl=True)
        self._imap.login(email, password)

    def logout(self) -> None:
        try:
            self._imap.logout()
        except Exception:
            pass

    # ── Folder listing ────────────────────────────────────────────────────────

    def list_folders(self) -> list[FolderInfo]:
        """Return all selectable folders with message counts."""
        raw    = self._imap.list_folders()
        result: list[FolderInfo] = []
        for flags, _delim, name in raw:
            if b"\\NoSelect" in flags:
                continue
            try:
                status = self._imap.folder_status(name, [b"MESSAGES"])
                count  = int(status.get(b"MESSAGES", 0))
            except Exception:
                count = -1
            result.append(FolderInfo(name=name, count=count, flags=tuple(flags)))
        return sorted(result, key=lambda f: f.name.lower())

    def resolve(self, name: str) -> str | None:
        """
        Resolve *name* to the real IMAP folder name.
        Accepts an exact name, a case-insensitive match, or a known alias
        (e.g. 'spam' → 'Bulk Mail').
        """
        available = {f.name.lower(): f.name for f in self.list_folders()}

        if name.lower() in available:
            return available[name.lower()]

        for candidate in ALIASES.get(name.lower(), []):
            if candidate.lower() in available:
                return available[candidate.lower()]

        return None

    # ── Counts ────────────────────────────────────────────────────────────────

    def count(self, folder: str) -> int:
        status = self._imap.folder_status(folder, [b"MESSAGES"])
        return int(status.get(b"MESSAGES", 0))

    def count_from_in(self, folder: str, sender: str) -> int:
        """Return the number of messages FROM *sender* in *folder*."""
        self._imap.select_folder(folder)
        return len(self._imap.search(["FROM", sender]))

    def count_from_sender(self, sender: str) -> list[tuple[str, int]]:
        """Return [(folder_name, count), ...] for folders that have mail FROM *sender*."""
        results = []
        for folder_info in self.list_folders():
            self._imap.select_folder(folder_info.name)
            uids = self._imap.search(["FROM", sender])
            if uids:
                results.append((folder_info.name, len(uids)))
        return results

    # ── Deletion ──────────────────────────────────────────────────────────────

    def purge(self, folder: str, progress: ProgressCB | None = None) -> int:
        """Permanently delete every message in *folder*. Returns count deleted."""
        self._imap.select_folder(folder)
        uids = self._imap.search(["ALL"])
        if not uids:
            return 0

        total   = len(uids)
        deleted = 0

        for i in range(0, total, BATCH_SIZE):
            batch = uids[i : i + BATCH_SIZE]
            self._imap.delete_messages(batch)
            deleted += len(batch)
            if progress:
                progress(deleted, total)
            time.sleep(DELAY)

        self._imap.expunge()
        return deleted

    def delete_from(
        self,
        folder: str,
        sender: str,
        progress: ProgressCB | None = None,
    ) -> int:
        """Permanently delete every message in *folder* FROM *sender*. Returns count deleted."""
        self._imap.select_folder(folder)
        uids = self._imap.search(["FROM", sender])
        if not uids:
            return 0

        total   = len(uids)
        deleted = 0

        for i in range(0, total, BATCH_SIZE):
            batch = uids[i : i + BATCH_SIZE]
            self._imap.delete_messages(batch)
            deleted += len(batch)
            if progress:
                progress(deleted, total)
            time.sleep(DELAY)

        self._imap.expunge()
        return deleted

    def batch_nuke(
        self,
        folder: str,
        batch: int = BATCH_SIZE,
        wait: float = 3.0,
        on_round: BatchCB | None = None,
    ) -> int:
        """
        Loop: SELECT → SEARCH ALL → take first *batch* UIDs → STORE \\Deleted
              → EXPUNGE → sleep *wait*s → repeat until folder is empty.

        Expunges after every round so deletion is permanent incrementally.
        Returns total number of messages permanently deleted.
        """
        total_deleted = 0
        round_num     = 0

        while True:
            self._imap.select_folder(folder)
            uids = self._imap.search(["ALL"])

            if not uids:
                break

            chunk     = uids[:batch]
            remaining = max(0, len(uids) - len(chunk))

            self._imap.delete_messages(chunk)
            self._imap.expunge()

            round_num     += 1
            total_deleted += len(chunk)

            if on_round:
                on_round(round_num, len(chunk), total_deleted, remaining)

            if remaining == 0:
                break

            time.sleep(wait)

        return total_deleted

    def purge_from_sender(
        self,
        sender: str,
        batch_size: int = BATCH_SIZE,
        on_folder: FolderDelCB | None = None,
    ) -> int:
        """Permanently delete every message FROM *sender* across all folders."""
        total_deleted = 0
        for folder_info in self.list_folders():
            self._imap.select_folder(folder_info.name)
            uids = self._imap.search(["FROM", sender])
            if not uids:
                continue
            deleted = 0
            for i in range(0, len(uids), batch_size):
                batch = uids[i : i + batch_size]
                self._imap.delete_messages(batch)
                deleted += len(batch)
                time.sleep(DELAY)
            self._imap.expunge()
            total_deleted += deleted
            if on_folder:
                on_folder(folder_info.name, deleted)
        return total_deleted

    def batch_nuke_sender(
        self,
        sender: str,
        batch: int = BATCH_SIZE,
        wait: float = 12.0,
        on_round: SenderBatchCB | None = None,
    ) -> int:
        """Loop-delete all messages FROM *sender* across every folder, batch by batch."""
        total_deleted = 0
        for folder_info in self.list_folders():
            round_num = 0
            while True:
                self._imap.select_folder(folder_info.name)
                uids = self._imap.search(["FROM", sender])
                if not uids:
                    break
                chunk     = uids[:batch]
                remaining = max(0, len(uids) - len(chunk))
                self._imap.delete_messages(chunk)
                self._imap.expunge()
                round_num     += 1
                total_deleted += len(chunk)
                if on_round:
                    on_round(folder_info.name, round_num, len(chunk), total_deleted, remaining)
                if remaining == 0:
                    break
                time.sleep(wait)
        return total_deleted

    def delete_folder(self, folder: str) -> None:
        """Purge all messages then delete the folder itself."""
        self.purge(folder)
        self._imap.delete_folder(folder)

    # ── Move ──────────────────────────────────────────────────────────────────

    def move_all(
        self,
        src: str,
        dst: str,
        progress: ProgressCB | None = None,
    ) -> int:
        """
        Move every message from *src* to *dst*.
        Uses IMAP MOVE extension (RFC 6851) — falls back to COPY+DELETE if
        the server does not advertise MOVE capability.
        Returns number of messages moved.
        """
        self._imap.select_folder(src)
        uids = self._imap.search(["ALL"])
        if not uids:
            return 0

        total    = len(uids)
        moved    = 0
        use_move = b"MOVE" in self._imap.capabilities()

        for i in range(0, total, BATCH_SIZE):
            batch = uids[i : i + BATCH_SIZE]
            try:
                if use_move:
                    self._imap.move(batch, dst)
                else:
                    raise IMAPClientError("no MOVE")
            except IMAPClientError:
                self._imap.copy(batch, dst)
                self._imap.delete_messages(batch)
                self._imap.expunge()
            moved += len(batch)
            if progress:
                progress(moved, total)
            time.sleep(DELAY)

        return moved

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def check_status(self) -> dict:
        """NOOP ping — returns latency_ms, capabilities, and server alerts."""
        start = time.monotonic()
        self._imap._imap.noop()
        latency_ms = round((time.monotonic() - start) * 1000)

        caps = [
            c.decode() if isinstance(c, bytes) else c
            for c in self._imap.capabilities()
        ]

        untagged = self._imap._imap.untagged_responses
        alerts: list[tuple[str, str]] = []
        for key, values in untagged.items():
            tag  = key.decode() if isinstance(key, bytes) else key
            for v in values:
                text = v.decode() if isinstance(v, bytes) else str(v)
                alerts.append((tag, text))

        return {"latency_ms": latency_ms, "capabilities": caps, "alerts": alerts}
