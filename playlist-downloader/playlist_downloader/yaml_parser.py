from __future__ import annotations

from pathlib import Path

import yaml

from playlist_downloader.models import Playlist, Track


class YamlPlaylistParser:
    def parse(self, path: Path) -> Playlist:
        with path.open(encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        playlist_data = data["playlist"]
        tracks = [
            self._build_track(item)
            for item in playlist_data.get("musicas", [])
        ]
        return Playlist(nome=playlist_data.get("nome", "Playlist"), musicas=tracks)

    @staticmethod
    def _build_track(item: dict) -> Track:
        return Track(
            nome=item["nome"],
            artistas=item.get("artistas", []),
            album=item.get("album", "Desconhecido"),
            duracao=item.get("duracao", "0:00"),
            data_lancamento=item.get("data_lancamento", "Desconhecida"),
            posicao=item.get("posicao", 0),
        )


def parse_playlist(path: str) -> Playlist:
    return YamlPlaylistParser().parse(Path(path))
