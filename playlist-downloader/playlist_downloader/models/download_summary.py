from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from playlist_downloader.models.track_download_result import TrackDownloadResult

@dataclass(frozen=True, slots=True)
class DownloadSummary:
    label: str
    mode: str
    total_tracks: int
    downloaded_count: int
    failed_count: int
    skipped_count: int
    unresolved_count: int
    results: list[TrackDownloadResult] = field(default_factory=list)
    skipped_manifest_path: Path | None = None
    unresolved_manifest_path: Path | None = None
    failed_manifest_path: Path | None = None