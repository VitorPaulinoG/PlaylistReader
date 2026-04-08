from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TRCK

from playlist_downloader.models import Track


@dataclass(slots=True)
class Id3MetadataWriter:
    def write(self, filepath: Path, track: Track) -> None:
        tags = self._load_tags(filepath)
        tags["TIT2"] = TIT2(encoding=3, text=track.titulo_exibicao)
        tags["TPE1"] = TPE1(encoding=3, text=track.artistas)
        tags["TALB"] = TALB(encoding=3, text=track.album)
        tags["TRCK"] = TRCK(encoding=3, text=str(track.posicao))
        tags.save(str(filepath))

    @staticmethod
    def _load_tags(filepath: Path) -> ID3:
        try:
            return ID3(str(filepath))
        except ID3NoHeaderError:
            tags = ID3()
            tags.save(str(filepath))
            return ID3(str(filepath))


def set_metadata(filepath: Path, track: Track) -> None:
    Id3MetadataWriter().write(filepath, track)
