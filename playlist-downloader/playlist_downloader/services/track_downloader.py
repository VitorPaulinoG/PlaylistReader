from typing import Protocol
from pathlib import Path

from playlist_downloader.models.playlist import Track
from playlist_downloader.models.download_artifact import DownloadArtifact
from playlist_downloader.models.search_candidate import SearchCandidate

class TrackDownloader(Protocol):
    def download(self, track: Track, output_dir: Path, overwrite: bool = False) -> DownloadArtifact: ...
    def search_candidates(self, track: Track, candidate_count: int) -> list[SearchCandidate]: ...
    def download_candidate(
        self,
        track: Track,
        candidate: SearchCandidate,
        output_dir: Path,
        overwrite: bool = False,
    ) -> DownloadArtifact: ...