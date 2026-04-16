from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playlist_downloader.models.playlist import Track


@dataclass(frozen=True, slots=True)
class TrackReviewResult:
    track: Track
    index: int
    total_tracks: int
    found: bool
    matched_by: str | None = None
    filepath: Path | None = None
    error: str | None = None
