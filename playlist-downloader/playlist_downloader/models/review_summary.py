from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from playlist_downloader.models.track_review_result import TrackReviewResult


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    label: str
    total_tracks: int
    missing_count: int
    results: list[TrackReviewResult] = field(default_factory=list)
    missing_manifest_path: Path | None = None
