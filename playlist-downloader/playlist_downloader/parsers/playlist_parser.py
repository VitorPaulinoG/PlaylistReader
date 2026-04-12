from typing import Protocol
from pathlib import Path

from playlist_downloader.models.playlist import Playlist

class PlaylistParser(Protocol):
    def parse(self, path: Path) -> Playlist: ...