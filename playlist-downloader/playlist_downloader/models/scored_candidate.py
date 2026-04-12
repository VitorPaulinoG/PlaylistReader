from __future__ import annotations

from dataclasses import dataclass
from playlist_downloader.models.search_candidate import SearchCandidate

@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    candidate: SearchCandidate
    score: int
    reasons: list[str]
    title_match: bool