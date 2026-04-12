from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Track:
    nome: str
    artistas: list[str] = field(default_factory=list)
    album: str = "Desconhecido"
    duracao: str = "0:00"
    data_lancamento: str = "Desconhecida"
    posicao: int = 0
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def primeiro_artista(self) -> str:
        return self.artistas[0] if self.artistas else "Desconhecido"

    @property
    def titulo_exibicao(self) -> str:
        return f"{self.nome} - {self.primeiro_artista}"

    def search_terms(self) -> list[str]:
        terms = [self.nome]
        if self.primeiro_artista:
            terms.append(self.primeiro_artista)
        if self.album:
            terms.append(self.album)
        return terms


@dataclass(frozen=True, slots=True)
class Playlist:
    nome: str = "Playlist"
    musicas: list[Track] = field(default_factory=list)