from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from playlist_downloader.models.download_artifact import DownloadArtifact
from playlist_downloader.models.download_options import DownloadOptions
from playlist_downloader.models.playlist import Playlist, Track
from playlist_downloader.models.search_candidate import SearchCandidate
from playlist_downloader.services.playlist_download_service import PlaylistDownloadService
from playlist_downloader.services.playlist_review_service import PlaylistReviewService
from playlist_downloader.services.writers.skipped_tracks import SkippedTracksWriter
from playlist_downloader.services.writers.unresolved_tracks import UnresolvedTracksWriter
from playlist_downloader.errors.download_error import DownloadError


class FakeParser:
    def __init__(self, playlist: Playlist) -> None:
        self.playlist = playlist

    def parse(self, path: Path) -> Playlist:
        return self.playlist


class FakeDownloader:
    def __init__(self, failures: set[str] | None = None, candidates: list[SearchCandidate] | None = None) -> None:
        self.failures = failures or set()
        self.candidates = candidates or []
        self.download_calls: list[tuple[str, bool]] = []
        self.download_from_url_calls: list[tuple[str, str, bool]] = []
        self.candidate_downloads: list[str] = []

    def download(self, track: Track, output_dir: Path, overwrite: bool = False) -> DownloadArtifact:
        self.download_calls.append((track.nome, overwrite))
        if track.nome in self.failures:
            raise DownloadError(f"failed {track.nome}")
        return DownloadArtifact(
            filepath=output_dir / f"{track.titulo_exibicao}.mp3",
            source_url=f"https://example.com/{track.nome}",
        )

    def download_from_url(self, track: Track, url: str, output_dir: Path, overwrite: bool = False) -> DownloadArtifact:
        self.download_from_url_calls.append((track.nome, url, overwrite))
        if track.nome in self.failures:
            raise DownloadError(f"failed {track.nome}")
        return DownloadArtifact(
            filepath=output_dir / f"{track.titulo_exibicao}.mp3",
            source_url=url,
        )

    def search_candidates(self, track: Track, candidate_count: int) -> list[SearchCandidate]:
        return self.candidates[:candidate_count]

    def download_candidate(
        self,
        track: Track,
        candidate: SearchCandidate,
        output_dir: Path,
        overwrite: bool = False,
    ) -> DownloadArtifact:
        self.candidate_downloads.append(candidate.webpage_url)
        return DownloadArtifact(
            filepath=output_dir / f"{track.titulo_exibicao}.mp3",
            source_url=candidate.webpage_url,
        )


class FakeMetadataWriter:
    def __init__(self, failures: set[str] | None = None) -> None:
        self.failures = failures or set()

    def write(self, filepath: Path, track: Track) -> None:
        if track.nome in self.failures:
            raise RuntimeError(f"metadata {track.nome}")


class FakeMetadataReader:
    def __init__(self, tracks_by_path: dict[Path, Track]) -> None:
        self.tracks_by_path = tracks_by_path

    def read(self, filepath: Path) -> Track:
        return self.tracks_by_path[filepath]


class FakeReporter:
    def __init__(self, review_actions: list[str] | None = None) -> None:
        self.events: list[tuple[str, str]] = []
        self.summary = None
        self.review_actions = review_actions or []

    def on_collection_start(self, label: str, total_tracks: int) -> None:
        self.events.append(("collection_start", f"{label}:{total_tracks}"))

    def on_track_start(self, index: int, total_tracks: int, track: Track) -> None:
        self.events.append(("track_start", f"{index}/{total_tracks}:{track.nome}"))

    def on_track_success(self, index: int, total_tracks: int, track: Track, artifact: DownloadArtifact) -> None:
        self.events.append(("track_success", f"{index}/{total_tracks}:{artifact.filepath.name if artifact.filepath else 'n/a'}"))

    def on_track_skipped(self, index: int, total_tracks: int, track: Track, artifact: DownloadArtifact) -> None:
        self.events.append(("track_skipped", f"{index}/{total_tracks}:{artifact.filepath.name if artifact.filepath else 'n/a'}"))

    def on_track_failure(self, index: int, total_tracks: int, track: Track, error: str) -> None:
        self.events.append(("track_failure", f"{index}/{total_tracks}:{error}"))

    def on_track_unresolved(self, index: int, total_tracks: int, track: Track, message: str) -> None:
        self.events.append(("track_unresolved", f"{index}/{total_tracks}:{message}"))

    def review_candidate(self, track: Track, candidate_index: int, total_candidates: int, scored_candidate) -> str:
        return self.review_actions.pop(0)

    def on_collection_finished(self, summary) -> None:
        self.summary = summary


class FakeReviewReporter:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []
        self.summary = None

    def on_collection_start(self, label: str, total_tracks: int) -> None:
        self.events.append(("collection_start", f"{label}:{total_tracks}"))

    def on_track_missing(self, index: int, total_tracks: int, track: Track) -> None:
        self.events.append(
            (
                "track_missing",
                f"{index}/{total_tracks}:posicao={track.posicao}:nome={track.nome}:artista={track.primeiro_artista}:album={track.album}",
            )
        )

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

        self.assertEqual([("Faixa 2", True)], downloader.download_calls)
        self.assertEqual(1, summary.total_tracks)
        self.assertEqual(1, summary.downloaded_count)
        self.assertEqual(0, summary.failed_count)
        self.assertEqual("https://example.com/Faixa 2", summary.results[0].source_url)

    def test_smart_search_downloads_best_candidate(self) -> None:
        candidates = [
            SearchCandidate(
                title="Song analysis",
                webpage_url="https://example.com/analysis",
                channel="Music Reviews",
                duration=180,
            ),
            SearchCandidate(
                title="Song",
                webpage_url="https://example.com/song",
                channel="Artist - Topic",
                duration=180,
            ),
        ]
        service = PlaylistDownloadService(
            parser=FakeParser(Playlist()),
            downloader=FakeDownloader(candidates=candidates),
            metadata_writer=FakeMetadataWriter(),
            reporter=FakeReporter(),
            skipped_tracks_writer=SkippedTracksWriter(),
            unresolved_tracks_writer=UnresolvedTracksWriter(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            summary = service.run_search(
                "Song",
                "Artist",
                "Album",
                10,
                Path(temp_dir),
                DownloadOptions(smart_search=True, candidate_count=10, prefer_official=True),
            )

        self.assertEqual(1, summary.downloaded_count)
        self.assertEqual("https://example.com/song", summary.results[0].source_url)

    def test_smart_search_marks_track_as_unresolved_when_no_candidate_matches(self) -> None:
        candidates = [
            SearchCandidate(
                title="Different song live",
                webpage_url="https://example.com/live",
                channel="Someone",
                duration=180,
            )
        ]
        reporter = FakeReporter()
        service = PlaylistDownloadService(
            parser=FakeParser(
                Playlist(nome="List", musicas=[Track(nome="Song", artistas=["Artist"], album="Album", posicao=1)])
            ),
            downloader=FakeDownloader(candidates=candidates),
            metadata_writer=FakeMetadataWriter(),
            reporter=reporter,
            skipped_tracks_writer=SkippedTracksWriter(),
            unresolved_tracks_writer=UnresolvedTracksWriter(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            summary = service.run_playlist(
                Path("playlist.yaml"),
                output_dir,
                DownloadOptions(smart_search=True, candidate_count=10),
            )
            manifest_data = yaml.safe_load(summary.unresolved_manifest_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]

        self.assertEqual(1, summary.unresolved_count)
        self.assertEqual(0, summary.failed_count)
        self.assertIn("No suitable video was found", summary.results[0].error or "")
        self.assertEqual("track_unresolved", reporter.events[-1][0])
        self.assertEqual("List", manifest_data["playlist"]["nome"])

    def test_review_search_uses_user_choice(self) -> None:
        candidates = [
            SearchCandidate(
                title="Song analysis",
                webpage_url="https://example.com/analysis",
                channel="Reviews",
                duration=180,
            ),
            SearchCandidate(
                title="Song",
                webpage_url="https://example.com/song",
                channel="Artist - Topic",
                duration=180,
            ),
        ]
        downloader = FakeDownloader(candidates=candidates)
        reporter = FakeReporter(review_actions=["next", "download"])
        service = PlaylistDownloadService(
            parser=FakeParser(Playlist()),
            downloader=downloader,
            metadata_writer=FakeMetadataWriter(),
            reporter=reporter,
            skipped_tracks_writer=SkippedTracksWriter(),
            unresolved_tracks_writer=UnresolvedTracksWriter(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            summary = service.run_search(
                "Song",
                "Artist",
                "Album",
                10,
                Path(temp_dir),
                DownloadOptions(review_search=True),
            )

        self.assertEqual(1, summary.downloaded_count)
        self.assertEqual(["https://example.com/analysis"], downloader.candidate_downloads)

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

    def test_run_from_url_downloads_track_with_provided_metadata(self) -> None:
        downloader = FakeDownloader()
        service = PlaylistDownloadService(
            parser=FakeParser(Playlist()),
            downloader=downloader,
            metadata_writer=FakeMetadataWriter(),
            reporter=FakeReporter(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            summary = service.run_from_url(
                "https://example.com/song",
                "Song",
                "Artist",
                "Album",
                7,
                Path(temp_dir),
                DownloadOptions(overwrite=True),
            )

        self.assertEqual([("Song", "https://example.com/song", True)], downloader.download_from_url_calls)
        self.assertEqual("from_url", summary.mode)
        self.assertEqual(1, summary.downloaded_count)
        self.assertEqual("https://example.com/song", summary.results[0].source_url)


class PlaylistReviewServiceTest(unittest.TestCase):
    def test_review_playlist_uses_position_then_metadata_and_writes_missing_manifest(self) -> None:
        playlist = Playlist(
            nome="Minha Playlist",
            musicas=[
                Track(nome="Faixa B", artistas=["Artista B"], album="Album B", posicao=2),
                Track(nome="Faixa A", artistas=["Artista A"], album="Album A", posicao=1),
                Track(nome="Faixa C", artistas=["Artista C"], album="Album C", posicao=3),
            ],
        )
        reporter = FakeReviewReporter()

        with tempfile.TemporaryDirectory() as temp_dir:
            playlist_folder = Path(temp_dir)
            faixa_por_posicao = playlist_folder / "track-01.mp3"
            faixa_por_metadados = playlist_folder / "track-b.mp3"
            faixa_sem_match = playlist_folder / "other.mp3"
            for filepath in [faixa_por_posicao, faixa_por_metadados, faixa_sem_match]:
                filepath.write_bytes(b"")

            metadata_reader = FakeMetadataReader(
                {
                    faixa_por_posicao: Track(
                        nome="Qualquer Nome",
                        artistas=["Outro Artista"],
                        album="Outro Album",
                        posicao=1,
                    ),
                    faixa_por_metadados: Track(
                        nome="Faixa B",
                        artistas=["Artista B"],
                        album="Album B",
                        posicao=77,
                    ),
                    faixa_sem_match: Track(
                        nome="Outra",
                        artistas=["Pessoa"],
                        album="Nada",
                        posicao=99,
                    ),
                }
            )
            service = PlaylistReviewService(
                metadata_reader=metadata_reader,
                parser=FakeParser(playlist),
                reporter=reporter,
            )

            summary = service.review_playlist(Path("playlist.yaml"), playlist_folder)
            manifest_data = yaml.safe_load(summary.missing_manifest_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]

        self.assertEqual(3, summary.total_tracks)
        self.assertEqual(1, summary.missing_count)
        self.assertEqual(["position", "metadata", None], [result.matched_by for result in summary.results])
        self.assertEqual("Faixa C", summary.results[-1].track.nome)
        self.assertIn("track_missing", [event[0] for event in reporter.events])
        self.assertEqual("Faixa C", manifest_data["playlist"]["musicas"][0]["nome"])
        self.assertEqual(3, manifest_data["playlist"]["musicas"][0]["posicao"])


if __name__ == "__main__":
    unittest.main()
