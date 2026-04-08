from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from playlist_downloader.downloader import DownloadArtifact, DownloadError
from playlist_downloader.models import Playlist, Track
from playlist_downloader.skipped_tracks import SkippedTracksWriter
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

    def on_track_skipped(self, index: int, total_tracks: int, track: Track, artifact: DownloadArtifact) -> None:
        self.events.append(("track_skipped", f"{index}/{total_tracks}:{artifact.filepath.name}"))

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
            skipped_tracks_writer=SkippedTracksWriter(),
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

    def test_search_skip_writes_search_manifest(self) -> None:
        reporter = FakeReporter()

        class SkipDownloader:
            def download(self, track: Track, output_dir: Path, overwrite: bool = False) -> DownloadArtifact:
                return DownloadArtifact(filepath=output_dir / "Song - Artist.mp3", skipped=True)

        service = PlaylistDownloadService(
            parser=FakeParser(Playlist()),
            downloader=SkipDownloader(),
            metadata_writer=FakeMetadataWriter(),
            reporter=reporter,
            skipped_tracks_writer=SkippedTracksWriter(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            summary = service.run_search("Song", "Artist", "Album", output_dir, DownloadOptions())
            manifest_path = output_dir / ".playlist-downloader" / "skipped" / "Song - Artist-001.skipped.yaml"
            manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(1, summary.skipped_count)
        self.assertEqual(manifest_path, summary.skipped_manifest_path)
        self.assertEqual(
            {
                "playlist": {
                    "nome": "Song - Artist",
                    "musicas": [
                        {
                            "nome": "Song",
                            "artistas": ["Artist"],
                            "album": "Album",
                            "duracao": "0:00",
                            "data_lancamento": "Desconhecida",
                            "posicao": 1,
                        }
                    ],
                }
            },
            manifest_data,
        )

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

    def test_existing_track_is_skipped_and_manifest_is_written(self) -> None:
        skipped_track = Track(
            nome="Song",
            artistas=["Artist"],
            album="Album",
            duracao="3:00",
            data_lancamento="2020",
            posicao=7,
            raw_data={
                "nome": "Song",
                "artistas": ["Artist"],
                "album": "Album",
                "duracao": "3:00",
                "data_lancamento": "2020",
                "posicao": 7,
            },
        )
        reporter = FakeReporter()

        class SkipDownloader:
            def download(self, track: Track, output_dir: Path, overwrite: bool = False) -> DownloadArtifact:
                return DownloadArtifact(filepath=output_dir / "Song - Artist.mp3", skipped=True)

        service = PlaylistDownloadService(
            parser=FakeParser(Playlist(nome="List", musicas=[skipped_track])),
            downloader=SkipDownloader(),
            metadata_writer=FakeMetadataWriter(),
            reporter=reporter,
            skipped_tracks_writer=SkippedTracksWriter(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            source_path = output_dir / "input.yaml"
            source_path.write_text("playlist:\n  nome: List\n  musicas: []\n", encoding="utf-8")
            summary = service.run_playlist(source_path, output_dir, DownloadOptions())
            manifest_path = output_dir / ".playlist-downloader" / "skipped" / "List-001.skipped.yaml"
            manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(0, summary.downloaded_count)
        self.assertEqual(1, summary.skipped_count)
        self.assertEqual(0, summary.failed_count)
        self.assertTrue(summary.results[0].skipped)
        self.assertEqual(manifest_path, summary.skipped_manifest_path)
        self.assertEqual("track_skipped", reporter.events[-1][0])
        self.assertEqual(
            {
                "playlist": {
                    "nome": "List",
                    "musicas": [
                        {
                            "nome": "Song",
                            "artistas": ["Artist"],
                            "album": "Album",
                            "duracao": "3:00",
                            "data_lancamento": "2020",
                            "posicao": 7,
                        }
                    ],
                }
            },
            manifest_data,
        )


if __name__ == "__main__":
    unittest.main()
