from typing import Protocol
from pathlib import Path

from playlist_downloader.models.playlist import Track

class MetadataReader(Protocol):
    def read(self, filepath: Path, track: Track) -> None: ...