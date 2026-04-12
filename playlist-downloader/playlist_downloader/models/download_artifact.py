from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class DownloadArtifact:
    filepath: Path | None
    source_url: str | None = None
    skipped: bool = False