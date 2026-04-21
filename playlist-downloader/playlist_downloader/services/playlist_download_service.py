from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from playlist_downloader.models.download_artifact import DownloadArtifact
from playlist_downloader.models.track_download_result import TrackDownloadResult
from playlist_downloader.models.download_options import DownloadOptions
from playlist_downloader.models.download_summary import DownloadSummary
from playlist_downloader.models.playlist import Track
from playlist_downloader.models.search_candidate import SearchCandidate
from playlist_downloader.errors.download_error import DownloadError
from playlist_downloader.services.search_resolution import choose_best_candidate, rank_candidates
from playlist_downloader.services.metadata_writer import MetadataWriter
from playlist_downloader.services.writers.skipped_tracks import SkippedTracksWriter
from playlist_downloader.services.writers.unresolved_tracks import UnresolvedTracksWriter
from playlist_downloader.services.writers.failed_tracks import FailedTracksWriter
from playlist_downloader.services.playlist_parser import PlaylistParser
from playlist_downloader.services.track_downloader import TrackDownloader
from playlist_downloader.services.download_reporter import DownloadReporter

@dataclass(slots=True)
class PlaylistDownloadService:
    parser: PlaylistParser
    downloader: TrackDownloader
    metadata_writer: MetadataWriter
    reporter: DownloadReporter
    skipped_tracks_writer: SkippedTracksWriter | None = None
    unresolved_tracks_writer: UnresolvedTracksWriter | None = None
    failed_tracks_writer: FailedTracksWriter | None = None

    def run_playlist(self, yaml_path: Path, output_dir: Path, options: DownloadOptions) -> DownloadSummary:
        playlist = self.parser.parse(yaml_path)
        selected_tracks = self._select_tracks(playlist.musicas, options)
        return self._run_collection(
            label=playlist.nome,
            mode="playlist",
            tracks=selected_tracks,
            output_dir=output_dir,
            options=options,
        )
    
    def run_search(
        self,
        title: str,
        artist: str,
        album: str,
        position: int,
        output_dir: Path,
        options: DownloadOptions,
    ) -> DownloadSummary:
        track = Track(
            nome=title,
            artistas=[artist],
            album=album,
            posicao=position,
        )
        return self._run_collection(
            label=track.titulo_exibicao,
            mode="search",
            tracks=[track],
            output_dir=output_dir,
            options=options,
        )

    def run_from_url(
        self,
        url: str,
        title: str,
        artist: str,
        album: str,
        position: int,
        output_dir: Path,
        options: DownloadOptions,
    ) -> DownloadSummary:
        track = Track(
            nome=title,
            artistas=[artist],
            album=album,
            posicao=position,
        )
        return self._run_direct_url(
            track=track,
            url=url,
            output_dir=output_dir,
            options=options,
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
    ) -> DownloadSummary:
        total_tracks = len(tracks)
        self.reporter.on_collection_start(label, total_tracks)

        results: list[TrackDownloadResult] = []
        for index, track in enumerate(tracks, start=1):
            self.reporter.on_track_start(index, total_tracks, track)
            result = self._process_track(index, total_tracks, track, output_dir, options)
            if result.error == "__abort__":
                break
            results.append(result)

        skipped_tracks = [result.track for result in results if result.skipped]
        unresolved_tracks = [result.track for result in results if result.unresolved]
        failed_tracks = [result.track for result in results if not result.success and not result.unresolved]

        summary = DownloadSummary(
            label=label,
            mode=mode,
            total_tracks=total_tracks,
            downloaded_count=sum(1 for result in results if result.success and not result.skipped),
            failed_count=sum(1 for result in results if not result.success and not result.unresolved),
            skipped_count=len(skipped_tracks),
            unresolved_count=len(unresolved_tracks),
            results=results,
            skipped_manifest_path=self.skipped_tracks_writer.write(output_dir, label, skipped_tracks)
            if self.skipped_tracks_writer is not None
            else None,
            unresolved_manifest_path=self.unresolved_tracks_writer.write(output_dir, label, unresolved_tracks)
            if self.unresolved_tracks_writer is not None
            else None,
            failed_manifest_path=self.failed_tracks_writer.write(output_dir, label, failed_tracks)
            if self.failed_tracks_writer is not None
            else None,
        )
        self.reporter.on_collection_finished(summary)
        return summary

    def _run_direct_url(
        self,
        track: Track,
        url: str,
        output_dir: Path,
        options: DownloadOptions,
    ) -> DownloadSummary:
        self.reporter.on_collection_start(track.titulo_exibicao, 1)
        self.reporter.on_track_start(1, 1, track)

        result = self._process_direct_url_track(track, url, output_dir, options)
        results = [] if result.error == "__abort__" else [result]

        summary = DownloadSummary(
            label=track.titulo_exibicao,
            mode="from_url",
            total_tracks=1,
            downloaded_count=sum(1 for current in results if current.success and not current.skipped),
            failed_count=sum(1 for current in results if not current.success and not current.unresolved),
            skipped_count=sum(1 for current in results if current.skipped),
            unresolved_count=sum(1 for current in results if current.unresolved),
            results=results,
            skipped_manifest_path=self.skipped_tracks_writer.write(output_dir, track.titulo_exibicao, [track])
            if self.skipped_tracks_writer is not None and result.skipped
            else None,
            unresolved_manifest_path=None,
            failed_manifest_path=self.failed_tracks_writer.write(output_dir, track.titulo_exibicao, [track])
            if self.failed_tracks_writer is not None and results and not result.success and not result.unresolved
            else None,
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
        return self._process_download(
            index=index,
            total_tracks=total_tracks,
            track=track,
            artifact_loader=lambda: self._resolve_and_download(track, output_dir, options),
        )

    def _process_direct_url_track(
        self,
        track: Track,
        url: str,
        output_dir: Path,
        options: DownloadOptions,
    ) -> TrackDownloadResult:
        return self._process_download(
            index=1,
            total_tracks=1,
            track=track,
            artifact_loader=lambda: self.downloader.download_from_url(
                track=track,
                url=url,
                output_dir=output_dir,
                overwrite=options.overwrite,
            ),
        )

    def _process_download(
        self,
        index: int,
        total_tracks: int,
        track: Track,
        artifact_loader: Callable[[], DownloadArtifact],
    ) -> TrackDownloadResult:
        try:
            artifact = artifact_loader()
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
            if artifact.filepath is None:
                message = artifact.source_url or "No suitable video was found."
                self.reporter.on_track_unresolved(index, total_tracks, track, message)
                return TrackDownloadResult(
                    track=track,
                    index=index,
                    total_tracks=total_tracks,
                    success=False,
                    unresolved=True,
                    error=message,
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
        except KeyboardInterrupt:
            return TrackDownloadResult(
                track=track,
                index=index,
                total_tracks=total_tracks,
                success=False,
                error="__abort__",
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

    def _resolve_and_download(self, track: Track, output_dir: Path, options: DownloadOptions) -> DownloadArtifact:
        if not options.smart_search and not options.review_search:
            return self.downloader.download(track, output_dir, overwrite=options.overwrite)

        candidates = self.downloader.search_candidates(track, options.candidate_count)
        if not candidates:
            return DownloadArtifact(filepath=None, source_url="No candidates were returned by the search API.")  # type: ignore[arg-type]

        if options.review_search:
            return self._download_after_manual_review(track, candidates, output_dir, options)

        selected = choose_best_candidate(
            track=track,
            candidates=candidates,
            prefer_official=options.prefer_official,
        )
        if selected is None:
            return DownloadArtifact(
                filepath=None,  # type: ignore[arg-type]
                source_url=f"No suitable video was found among the top {options.candidate_count} candidates.",
            )
        return self.downloader.download_candidate(
            track=track,
            candidate=selected.candidate,
            output_dir=output_dir,
            overwrite=options.overwrite,
        )

    def _download_after_manual_review(
        self,
        track: Track,
        candidates: list[SearchCandidate],
        output_dir: Path,
        options: DownloadOptions,
    ) -> DownloadArtifact:
        ranked_candidates = rank_candidates(
            track=track,
            candidates=candidates,
            prefer_official=options.prefer_official,
        )
        total_candidates = len(ranked_candidates)
        for candidate_index, scored_candidate in enumerate(ranked_candidates, start=1):
            action = self.reporter.review_candidate(
                track=track,
                candidate_index=candidate_index,
                total_candidates=total_candidates,
                scored_candidate=scored_candidate,
            )
            if action == "download":
                return self.downloader.download_candidate(
                    track=track,
                    candidate=scored_candidate.candidate,
                    output_dir=output_dir,
                    overwrite=options.overwrite,
                )
            if action == "skip":
                return DownloadArtifact(
                    filepath=None,  # type: ignore[arg-type]
                    source_url=f"Track skipped by user after reviewing {candidate_index} candidate(s).",
                )
            if action == "abort":
                raise KeyboardInterrupt()

        return DownloadArtifact(
            filepath=None,  # type: ignore[arg-type]
            source_url=f"No suitable video was confirmed among the top {options.candidate_count} candidates.",
        )
