from typing import Protocol

from playlist_downloader.models.playlist import Track
from playlist_downloader.models.review_summary import ReviewSummary


class ReviewReporter(Protocol):
    def on_collection_start(self, label: str, total_tracks: int) -> None: ...
    def on_track_missing(self, index: int, total_tracks: int, track: Track) -> None: ...
    def on_collection_finished(self, summary: ReviewSummary) -> None: ...
