from typing import Protocol
from pathlib import Path

from playlist_downloader.models.playlist import Track

class MetadataWriter(Protocol):
    def write(self, filepath: Path, track: Track) -> None: ...