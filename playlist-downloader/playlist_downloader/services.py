from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TextIO

from playlist_downloader.downloader import DownloadError
from playlist_downloader.models import Playlist, Track


class PlaylistParser(Protocol):
    def parse(self, path: Path) -> Playlist: ...


class TrackDownloader(Protocol):
    def download(self, track: Track, output_dir: Path) -> Path: ...


class MetadataWriter(Protocol):
    def write(self, filepath: Path, track: Track) -> None: ...


@dataclass(slots=True)
class PlaylistDownloadService:
    parser: PlaylistParser
    downloader: TrackDownloader
    metadata_writer: MetadataWriter
    output: TextIO

    def run(self, yaml_path: Path, output_dir: Path) -> None:
        playlist = self.parser.parse(yaml_path)
        total_tracks = len(playlist.musicas)

        print(f"[Playlist] {playlist.nome} - {total_tracks} faixa(s)", file=self.output)
        print(file=self.output)

        for track in playlist.musicas:
            self._process_track(track, total_tracks, output_dir)

        print("Concluído.", file=self.output)

    def _process_track(self, track: Track, total_tracks: int, output_dir: Path) -> None:
        print(
            f"[{track.posicao}/{total_tracks}] Baixando: {track.titulo_exibicao}",
            file=self.output,
        )

        try:
            output_path = self.downloader.download(track, output_dir)
        except DownloadError as error:
            print(f"  Erro ao baixar: {error}", file=self.output)
            print(file=self.output)
            return

        print("  Editando metadados...", file=self.output)
        try:
            self.metadata_writer.write(output_path, track)
        except Exception as error:
            print(f"  Erro ao editar metadados: {error}", file=self.output)
        else:
            print(f"  Salvo: {output_path.name}", file=self.output)

        print(file=self.output)
