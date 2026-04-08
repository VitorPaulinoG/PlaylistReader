from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from playlist_downloader.downloader import DownloadArtifact, DownloadError
from playlist_downloader.models import Playlist, Track
from playlist_downloader.services import DownloadOptions, PlaylistDownloadService


class FakeParser:
    def __init__(self, playlist: Playlist) -> None:
        self.playlist = playlist

    def parse(self, path: Path) -> Playlist:
        return self.playlist


class FakeDownloader:
    def __init__(self, failures: set[str] | None = None) -> None:
        self.failures = failures or set()
        self.calls: list[tuple[str, bool]] = []

    def download(self, track: Track, output_dir: Path, overwrite: bool = False) -> DownloadArtifact:
        self.calls.append((track.nome, overwrite))
        if track.nome in self.failures:
            raise DownloadError(f"failed {track.nome}")
        return DownloadArtifact(
            filepath=output_dir / f"{track.titulo_exibicao}.mp3",
            source_url=f"https://example.com/{track.nome}",
        )


class FakeMetadataWriter:
    def __init__(self, failures: set[str] | None = None) -> None:
        self.failures = failures or set()

    def write(self, filepath: Path, track: Track) -> None:
        if track.nome in self.failures:
            raise RuntimeError(f"metadata {track.nome}")


class FakeReporter:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []
        self.summary = None

    def on_collection_start(self, label: str, total_tracks: int) -> None:
        self.events.append(("collection_start", f"{label}:{total_tracks}"))

    def on_track_start(self, index: int, total_tracks: int, track: Track) -> None:
        self.events.append(("track_start", f"{index}/{total_tracks}:{track.nome}"))

    def on_track_success(self, index: int, total_tracks: int, track: Track, artifact: DownloadArtifact) -> None:
        self.events.append(("track_success", f"{index}/{total_tracks}:{artifact.filepath.name}"))

    def on_track_failure(self, index: int, total_tracks: int, track: Track, error: str) -> None:
        self.events.append(("track_failure", f"{index}/{total_tracks}:{error}"))

    def on_collection_finished(self, summary) -> None:
        self.summary = summary


class PlaylistDownloadServiceTest(unittest.TestCase):
    def test_run_playlist_applies_start_from_and_limit(self) -> None:
        playlist = Playlist(
            nome="Minha Playlist",
            musicas=[
                Track(nome="Faixa 1", artistas=["Artista 1"], posicao=1),
                Track(nome="Faixa 2", artistas=["Artista 2"], posicao=2),
                Track(nome="Faixa 3", artistas=["Artista 3"], posicao=3),
            ],
        )
        reporter = FakeReporter()
        downloader = FakeDownloader()
        service = PlaylistDownloadService(
            parser=FakeParser(playlist),
            downloader=downloader,
            metadata_writer=FakeMetadataWriter(),
            reporter=reporter,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            summary = service.run_playlist(
                Path("playlist.yaml"),
                Path(temp_dir),
                DownloadOptions(start_from=1, limit=1, overwrite=True),
            )

        self.assertEqual(["Faixa 2"], [name for name, _ in downloader.calls])
        self.assertEqual([("Faixa 2", True)], downloader.calls)
        self.assertEqual(1, summary.total_tracks)
        self.assertEqual(1, summary.downloaded_count)
        self.assertEqual(0, summary.failed_count)
        self.assertEqual("https://example.com/Faixa 2", summary.results[0].source_url)
        self.assertEqual(
            [
                ("collection_start", "Minha Playlist:1"),
                ("track_start", "1/1:Faixa 2"),
                ("track_success", "1/1:Faixa 2 - Artista 2.mp3"),
            ],
            reporter.events,
        )

    def test_run_search_creates_single_manual_track(self) -> None:
        reporter = FakeReporter()
        downloader = FakeDownloader()
        service = PlaylistDownloadService(
            parser=FakeParser(Playlist()),
            downloader=downloader,
            metadata_writer=FakeMetadataWriter(),
            reporter=reporter,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            summary = service.run_search(
                "Song",
                "Artist",
                "Album",
                Path(temp_dir),
                DownloadOptions(),
            )

        self.assertEqual([("Song", False)], downloader.calls)
        self.assertEqual(1, summary.total_tracks)
        self.assertEqual("Song - Artist", summary.label)
        self.assertEqual("search", summary.mode)

    def test_metadata_failure_is_reported_as_failed(self) -> None:
        reporter = FakeReporter()
        service = PlaylistDownloadService(
            parser=FakeParser(
                Playlist(nome="List", musicas=[Track(nome="Song", artistas=["Artist"], posicao=1)])
            ),
            downloader=FakeDownloader(),
            metadata_writer=FakeMetadataWriter(failures={"Song"}),
            reporter=reporter,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            summary = service.run_playlist(Path("playlist.yaml"), Path(temp_dir), DownloadOptions())

        self.assertEqual(0, summary.downloaded_count)
        self.assertEqual(1, summary.failed_count)
        self.assertIn("metadata update failed", summary.results[0].error or "")
        self.assertEqual("track_failure", reporter.events[-1][0])


if __name__ == "__main__":
    unittest.main()
