from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TRCK

from playlist_downloader.models.playlist import Track

@dataclass(slots=True)
class Id3MetadataReader:
    def read(self, filepath: Path) -> Track:
        tags = self._load_tags(filepath)
        nome = self._get_text(tags, "TIT2", default=filepath.stem)
        artistas = self._get_text_list(tags, "TPE1", default=["Desconhecido"])
        album = self._get_text(tags, "TALB", default="Desconhecido")
        posicao = self._parse_track_number(self._get_text(tags, "TRCK", default="0"))

        return Track(
            nome=nome,
            artistas=artistas,
            album=album,
            posicao=posicao,
        )


    @staticmethod
    def _load_tags(filepath: Path) -> ID3:
        try:
            return ID3(str(filepath))
        except ID3NoHeaderError:
            tags = ID3()
            tags.save(str(filepath))
            return ID3(str(filepath))

    @staticmethod
    def _get_text(tags: ID3, frame_id: str, default: str) -> str:
        frame = tags.get(frame_id)
        if frame is None or not getattr(frame, "text", None):
            return default
        return str(frame.text[0]).strip() or default

    @staticmethod
    def _get_text_list(tags: ID3, frame_id: str, default: list[str]) -> list[str]:
        frame = tags.get(frame_id)
        if frame is None or not getattr(frame, "text", None):
            return default
        values = [str(item).strip() for item in frame.text if str(item).strip()]
        return values or default

    @staticmethod
    def _parse_track_number(value: str) -> int:
        number = value.split("/", maxsplit=1)[0].strip()
        if not number:
            return 0
        try:
            return int(number)
        except ValueError:
            return 0

