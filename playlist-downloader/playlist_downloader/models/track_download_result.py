from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from playlist_downloader.models.playlist import Track

@dataclass(frozen=True, slots=True)
class TrackDownloadResult:
    track: Track
    index: int
    total_tracks: int
    success: bool
    skipped: bool = False
    unresolved: bool = False
    output_path: Path | None = None
    source_url: str | None = None
    error: str | None = None