from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from playlist_downloader.models.playlist import Track
from playlist_downloader.writers.manifest_writer import ManifestWriter

class FailedTracksWriter(ManifestWriter):
    def write(self, output_dir: Path, playlist_name: str, tracks: list[Track], manifest_type: str = "failed") -> Path | None:
        return super().write(output_dir, playlist_name, tracks, manifest_type)