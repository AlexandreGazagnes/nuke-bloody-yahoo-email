from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class FolderInfo:
    name:  str
    count: int
    flags: tuple


# Callback signatures used by YahooMailClient methods
ProgressCB    = Callable[[int, int], None]                   # (done, total)
BatchCB       = Callable[[int, int, int, int], None]         # (round, deleted, total, remaining)
FolderDelCB   = Callable[[str, int], None]                   # (folder_name, deleted_count)
SenderBatchCB = Callable[[str, int, int, int, int], None]    # (folder, round, deleted, total, remaining)
