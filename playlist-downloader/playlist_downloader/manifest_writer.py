from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from playlist_downloader.models import Track


@dataclass(slots=True)
class ManifestWriter:
    def write(self, output_dir: Path, playlist_name: str, tracks: list[Track], manifest_type: str) -> Path | None:
        if not tracks:
            return None

        manifest_dir = output_dir / ".playlist-downloader" / manifest_type
        manifest_dir.mkdir(parents=True, exist_ok=True)

        target_path = manifest_dir / self._build_filename(manifest_dir, playlist_name, manifest_type)
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
    def _build_filename(manifest_dir: Path, playlist_name: str, manifest_type: str) -> str:
        stem = _sanitize_name(playlist_name) or "playlist"
        sequence = 1
        while True:
            filename = f"{stem}-{sequence:03d}.{manifest_type}.yaml"
            if not (manifest_dir / filename).exists():
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


def _sanitize_name(value: str) -> str:
    sanitized = value.strip()
    for char in '<>:"/\\|?*':
        sanitized = sanitized.replace(char, "")
    return sanitized
