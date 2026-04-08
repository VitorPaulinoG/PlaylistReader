from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from playlist_downloader.downloader import DownloadArtifact, DownloadError
from playlist_downloader.models import Playlist, Track
from playlist_downloader.skipped_tracks import SkippedTracksWriter


class PlaylistParser(Protocol):
    def parse(self, path: Path) -> Playlist: ...


class TrackDownloader(Protocol):
    def download(self, track: Track, output_dir: Path, overwrite: bool = False) -> DownloadArtifact: ...


class MetadataWriter(Protocol):
    def write(self, filepath: Path, track: Track) -> None: ...


class DownloadReporter(Protocol):
    def on_collection_start(self, label: str, total_tracks: int) -> None: ...
    def on_track_start(self, index: int, total_tracks: int, track: Track) -> None: ...
    def on_track_skipped(
        self,
        index: int,
        total_tracks: int,
        track: Track,
        artifact: DownloadArtifact,
    ) -> None: ...
    def on_track_success(
        self,
        index: int,
        total_tracks: int,
        track: Track,
        artifact: DownloadArtifact,
    ) -> None: ...
    def on_track_failure(self, index: int, total_tracks: int, track: Track, error: str) -> None: ...
    def on_collection_finished(self, summary: "DownloadSummary") -> None: ...


@dataclass(frozen=True, slots=True)
class DownloadOptions:
    overwrite: bool = False
    verbose: bool = False
    limit: int | None = None
    start_from: int = 0
    show_url: bool = False


@dataclass(frozen=True, slots=True)
class TrackDownloadResult:
    track: Track
    index: int
    total_tracks: int
    success: bool
    skipped: bool = False
    output_path: Path | None = None
    source_url: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class DownloadSummary:
    label: str
    mode: str
    total_tracks: int
    downloaded_count: int
    failed_count: int
    skipped_count: int
    results: list[TrackDownloadResult] = field(default_factory=list)
    skipped_manifest_path: Path | None = None


@dataclass(slots=True)
class PlaylistDownloadService:
    parser: PlaylistParser
    downloader: TrackDownloader
    metadata_writer: MetadataWriter
    reporter: DownloadReporter
    skipped_tracks_writer: SkippedTracksWriter | None = None

    def run_playlist(self, yaml_path: Path, output_dir: Path, options: DownloadOptions) -> DownloadSummary:
        playlist = self.parser.parse(yaml_path)
        selected_tracks = self._select_tracks(playlist.musicas, options)
        return self._run_collection(
            label=playlist.nome,
            mode="playlist",
            tracks=selected_tracks,
            output_dir=output_dir,
            options=options,
            source_path=yaml_path,
        )

    def run_search(
        self,
        title: str,
        artist: str,
        album: str,
        output_dir: Path,
        options: DownloadOptions,
    ) -> DownloadSummary:
        track = Track(
            nome=title,
            artistas=[artist],
            album=album,
            posicao=1,
        )
        return self._run_collection(
            label=track.titulo_exibicao,
            mode="search",
            tracks=[track],
            output_dir=output_dir,
            options=options,
            source_path=Path("search.yaml"),
        )

    @staticmethod
    def _select_tracks(tracks: list[Track], options: DownloadOptions) -> list[Track]:
        selected_tracks = tracks[options.start_from :]
        if options.limit is not None:
            selected_tracks = selected_tracks[: options.limit]
        return selected_tracks

    def _run_collection(
        self,
        label: str,
        mode: str,
        tracks: list[Track],
        output_dir: Path,
        options: DownloadOptions,
        source_path: Path | None,
    ) -> DownloadSummary:
        total_tracks = len(tracks)
        self.reporter.on_collection_start(label, total_tracks)

        results: list[TrackDownloadResult] = []
        for index, track in enumerate(tracks, start=1):
            self.reporter.on_track_start(index, total_tracks, track)
            results.append(self._process_track(index, total_tracks, track, output_dir, options))

        summary = DownloadSummary(
            label=label,
            mode=mode,
            total_tracks=total_tracks,
            downloaded_count=sum(1 for result in results if result.success and not result.skipped),
            failed_count=sum(1 for result in results if not result.success),
            skipped_count=sum(1 for result in results if result.skipped),
            results=results,
        )
        if self.skipped_tracks_writer is not None and source_path is not None:
            skipped_tracks = [result.track for result in results if result.skipped]
            summary = DownloadSummary(
                label=summary.label,
                mode=summary.mode,
                total_tracks=summary.total_tracks,
                downloaded_count=summary.downloaded_count,
                failed_count=summary.failed_count,
                skipped_count=summary.skipped_count,
                results=summary.results,
                skipped_manifest_path=self.skipped_tracks_writer.write(
                    output_dir=output_dir,
                    playlist_name=label,
                    source_path=source_path,
                    tracks=skipped_tracks,
                ),
            )
        self.reporter.on_collection_finished(summary)
        return summary

    def _process_track(
        self,
        index: int,
        total_tracks: int,
        track: Track,
        output_dir: Path,
        options: DownloadOptions,
    ) -> TrackDownloadResult:
        try:
            artifact = self.downloader.download(track, output_dir, overwrite=options.overwrite)
            if artifact.skipped:
                self.reporter.on_track_skipped(index, total_tracks, track, artifact)
                return TrackDownloadResult(
                    track=track,
                    index=index,
                    total_tracks=total_tracks,
                    success=True,
                    skipped=True,
                    output_path=artifact.filepath,
                )
            self.metadata_writer.write(artifact.filepath, track)
        except DownloadError as error:
            message = str(error)
            self.reporter.on_track_failure(index, total_tracks, track, message)
            return TrackDownloadResult(
                track=track,
                index=index,
                total_tracks=total_tracks,
                success=False,
                error=message,
            )
        except Exception as error:
            message = f"metadata update failed for '{track.nome}': {error}"
            self.reporter.on_track_failure(index, total_tracks, track, message)
            return TrackDownloadResult(
                track=track,
                index=index,
                total_tracks=total_tracks,
                success=False,
                output_path=artifact.filepath,
                source_url=artifact.source_url,
                error=message,
            )

        self.reporter.on_track_success(index, total_tracks, track, artifact)
        return TrackDownloadResult(
            track=track,
            index=index,
            total_tracks=total_tracks,
            success=True,
            output_path=artifact.filepath,
            source_url=artifact.source_url,
        )
