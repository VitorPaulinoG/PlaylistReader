from __future__ import annotations

from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class SearchCandidate:
    title: str
    webpage_url: str
    channel: str = ""
    uploader: str = ""
    duration: int | None = None
    album: str = ""
    artist: str = ""
    video_id: str = ""
    raw_data: dict = field(default_factory=dict)