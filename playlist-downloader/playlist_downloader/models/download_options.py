from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class DownloadOptions:
    overwrite: bool = False
    verbose: bool = False
    limit: int | None = None
    start_from: int = 0
    show_url: bool = False
    smart_search: bool = False
    review_search: bool = False
    candidate_count: int = 10
    prefer_official: bool = False