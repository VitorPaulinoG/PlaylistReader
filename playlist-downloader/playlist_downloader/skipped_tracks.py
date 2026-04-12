from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from playlist_downloader.models import Track
from playlist_downloader.manifest_writer import ManifestWriter

class SkippedTracksWriter(ManifestWriter):
    def write(self, output_dir: Path, playlist_name: str, tracks: list[Track], manifest_type: str = "skipped") -> Path | None:
        return super().write(output_dir, playlist_name, tracks, manifest_type)