from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TRCK

from playlist_downloader.models.playlist import Track

@dataclass(slots=True)
class Id3MetadataReader:
    def read(self, filepath: Path) -> Track:
        tags = self._load_tags(filepath)
        nome = tags["TIT2"].text[0]
        artitas = tags["TPE1"].text
        album = tags["TALB"].text[0]
        posicao = tags["TRCK"].text[0]
        
        return Track(nome, artitas, album, posicao)


    @staticmethod
    def _load_tags(filepath: Path) -> ID3:
        try:
            return ID3(str(filepath))
        except ID3NoHeaderError:
            tags = ID3()
            tags.save(str(filepath))
            return ID3(str(filepath))


