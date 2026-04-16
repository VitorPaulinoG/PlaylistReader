from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from playlist_downloader.models.playlist import Track
from playlist_downloader.models.review_summary import ReviewSummary
from playlist_downloader.models.track_review_result import TrackReviewResult
from playlist_downloader.services.metadata_reader import MetadataReader
from playlist_downloader.services.playlist_parser import PlaylistParser
from playlist_downloader.services.review_reporter import ReviewReporter
from playlist_downloader.services.writers.manifest_writer import ManifestWriter


@dataclass(frozen=True, slots=True)
class _PlaylistFolderEntry:
    filepath: Path
    track: Track


@dataclass(slots=True)
class PlaylistReviewService:
    metadata_reader: MetadataReader
    parser: PlaylistParser
    reporter: ReviewReporter
    manifest_writer: ManifestWriter = field(default_factory=ManifestWriter)

    def review_playlist(self, playlist_file: Path, playlist_folder: Path) -> ReviewSummary:
        playlist = self.parser.parse(playlist_file)
        tracks = sorted(playlist.musicas, key=lambda track: track.posicao)
        available_tracks = self._load_playlist_folder_entries(playlist_folder)
        total_tracks = len(tracks)

        self.reporter.on_collection_start(playlist.nome, total_tracks)

        results: list[TrackReviewResult] = []
        for index, track in enumerate(tracks, start=1):
            matched_entry = self._find_match(track, available_tracks)
            if matched_entry is not None:
                entry, matched_by = matched_entry
                available_tracks.pop(entry.filepath, None)
                results.append(
                    TrackReviewResult(
                        track=track,
                        index=index,
                        total_tracks=total_tracks,
                        found=True,
                        matched_by=matched_by,
                        filepath=entry.filepath,
                    )
                )
                continue

            message = (
                f"Track not found in playlist folder: posicao={track.posicao} "
                f"nome={track.nome} artista={track.primeiro_artista} album={track.album}"
            )
            self.reporter.on_track_missing(index, total_tracks, track)
            results.append(
                TrackReviewResult(
                    track=track,
                    index=index,
                    total_tracks=total_tracks,
                    found=False,
                    error=message,
                )
            )

        missing_tracks = [result.track for result in results if not result.found]
        summary = ReviewSummary(
            label=playlist.nome,
            total_tracks=total_tracks,
            missing_count=len(missing_tracks),
            results=results,
            missing_manifest_path=self.manifest_writer.write(
                playlist_folder,
                playlist.nome,
                missing_tracks,
                "missing",
            ),
        )
        self.reporter.on_collection_finished(summary)
        return summary

    def _load_playlist_folder_entries(self, playlist_folder: Path) -> dict[Path, _PlaylistFolderEntry]:
        entries: dict[Path, _PlaylistFolderEntry] = {}
        for filepath in sorted(path for path in playlist_folder.iterdir() if path.is_file()):
            try:
                track = self.metadata_reader.read(filepath)
            except Exception:
                continue
            entries[filepath] = _PlaylistFolderEntry(filepath=filepath, track=track)
        return entries

    def _find_match(
        self,
        expected_track: Track,
        available_tracks: dict[Path, _PlaylistFolderEntry],
    ) -> tuple[_PlaylistFolderEntry, str] | None:
        for entry in available_tracks.values():
            if self._positions_match(expected_track, entry.track):
                return entry, "position"

        for entry in available_tracks.values():
            if self._metadata_match(expected_track, entry.track):
                return entry, "metadata"

        return None

    @staticmethod
    def _positions_match(expected_track: Track, actual_track: Track) -> bool:
        return expected_track.posicao > 0 and actual_track.posicao == expected_track.posicao

    @staticmethod
    def _metadata_match(expected_track: Track, actual_track: Track) -> bool:
        return (
            _normalize_text(actual_track.nome) == _normalize_text(expected_track.nome)
            and _normalize_text(actual_track.primeiro_artista) == _normalize_text(expected_track.primeiro_artista)
            and _normalize_text(actual_track.album) == _normalize_text(expected_track.album)
        )


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())
