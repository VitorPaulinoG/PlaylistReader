from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from playlist_downloader.downloader import DownloadError
from playlist_downloader.models import Playlist, Track
from playlist_downloader.services import PlaylistDownloadService


class FakeParser:
    def __init__(self, playlist: Playlist) -> None:
        self.playlist = playlist

    def parse(self, path: Path) -> Playlist:
        return self.playlist


class FakeDownloader:
    def __init__(self, paths: list[Path], failures: set[int] | None = None) -> None:
        self.paths = list(paths)
        self.failures = failures or set()
        self.calls = 0

    def download(self, track: Track, output_dir: Path) -> Path:
        self.calls += 1
        if track.posicao in self.failures:
            raise DownloadError(f"falhou {track.nome}")
        return self.paths[track.posicao - 1]


class FakeMetadataWriter:
    def __init__(self, failures: set[int] | None = None) -> None:
        self.failures = failures or set()

    def write(self, filepath: Path, track: Track) -> None:
        if track.posicao in self.failures:
            raise RuntimeError(f"metadata {track.nome}")


class PlaylistDownloadServiceTest(unittest.TestCase):
    def test_run_preserves_user_facing_output(self) -> None:
        playlist = Playlist(
            nome="Minha Playlist",
            musicas=[
                Track(nome="Faixa 1", artistas=["Artista 1"], posicao=1),
                Track(nome="Faixa 2", artistas=["Artista 2"], posicao=2),
                Track(nome="Faixa 3", artistas=["Artista 3"], posicao=3),
            ],
        )
        stdout = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            downloaded_paths = [
                output_dir / "Faixa 1 - Artista 1.mp3",
                output_dir / "Faixa 2 - Artista 2.mp3",
                output_dir / "Faixa 3 - Artista 3.mp3",
            ]
            service = PlaylistDownloadService(
                parser=FakeParser(playlist),
                downloader=FakeDownloader(downloaded_paths, failures={2}),
                metadata_writer=FakeMetadataWriter(failures={3}),
                output=stdout,
            )

            service.run(Path("playlist.yaml"), output_dir)

        self.assertEqual(
            "\n".join(
                [
                    "[Playlist] Minha Playlist - 3 faixa(s)",
                    "",
                    "[1/3] Baixando: Faixa 1 - Artista 1",
                    "  Editando metadados...",
                    "  Salvo: Faixa 1 - Artista 1.mp3",
                    "",
                    "[2/3] Baixando: Faixa 2 - Artista 2",
                    "  Erro ao baixar: falhou Faixa 2",
                    "",
                    "[3/3] Baixando: Faixa 3 - Artista 3",
                    "  Editando metadados...",
                    "  Erro ao editar metadados: metadata Faixa 3",
                    "",
                    "Concluído.",
                    "",
                ]
            ),
            stdout.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
