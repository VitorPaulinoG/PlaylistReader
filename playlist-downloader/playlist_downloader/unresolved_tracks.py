from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from playlist_downloader.models import Track
from playlist_downloader.skipped_tracks import _sanitize_name


@dataclass(slots=True)
class UnresolvedTracksWriter:
    def write(self, output_dir: Path, playlist_name: str, tracks: list[Track]) -> Path | None:
        if not tracks:
            return None

        unresolved_dir = output_dir / ".playlist-downloader" / "unresolved"
        unresolved_dir.mkdir(parents=True, exist_ok=True)

        target_path = unresolved_dir / self._build_filename(unresolved_dir, playlist_name)
        payload = {
            "playlist": {
                "nome": playlist_name,
                "musicas": [track.raw_data or self._serialize_track(track) for track in tracks],
            }
        }
        with target_path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(payload, file, allow_unicode=True, sort_keys=False)
        return target_path

    @staticmethod
    def _build_filename(unresolved_dir: Path, playlist_name: str) -> str:
        stem = _sanitize_name(playlist_name) or "playlist"
        sequence = 1
        while True:
            filename = f"{stem}-{sequence:03d}.unresolved.yaml"
            if not (unresolved_dir / filename).exists():
                return filename
            sequence += 1

    @staticmethod
    def _serialize_track(track: Track) -> dict:
        return {
            "nome": track.nome,
            "artistas": track.artistas,
            "album": track.album,
            "duracao": track.duracao,
            "data_lancamento": track.data_lancamento,
            "posicao": track.posicao,
        }
