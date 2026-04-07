from dataclasses import dataclass

import yaml


@dataclass
class Track:
    nome: str
    artistas: list[str]
    album: str
    duracao: str
    data_lancamento: str
    posicao: int

    @property
    def primeiro_artista(self) -> str:
        return self.artistas[0] if self.artistas else "Desconhecido"


@dataclass
class Playlist:
    nome: str
    musicas: list[Track]


def parse_playlist(path: str) -> Playlist:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    playlist = data["playlist"]
    tracks = []
    for item in playlist.get("musicas", []):
        tracks.append(Track(
            nome=item["nome"],
            artistas=item.get("artistas", []),
            album=item.get("album", "Desconhecido"),
            duracao=item.get("duracao", "0:00"),
            data_lancamento=item.get("data_lancamento", "Desconhecida"),
            posicao=item.get("posicao", 0),
        ))

    return Playlist(nome=playlist.get("nome", "Playlist"), musicas=tracks)
