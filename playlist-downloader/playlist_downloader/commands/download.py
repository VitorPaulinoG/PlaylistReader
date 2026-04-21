from __future__ import annotations

from typing import Annotated

import typer

from playlist_downloader.commands.download_modes import DownloadCommandInput, build_download_mode_dispatcher
from playlist_downloader.models.download_options import DownloadOptions
from playlist_downloader.services.downloaders.ytdlp_track_downloader import YtDlpTrackDownloader
from playlist_downloader.services.writers.id3_metadata_writer import Id3MetadataWriter
from playlist_downloader.services.reporters.rich_download_reporter import RichDownloadReporter
from playlist_downloader.services.playlist_download_service import PlaylistDownloadService
from playlist_downloader.services.writers.skipped_tracks import SkippedTracksWriter
from playlist_downloader.services.writers.unresolved_tracks import UnresolvedTracksWriter
from playlist_downloader.services.writers.failed_tracks import FailedTracksWriter
from playlist_downloader.services.parsers.yaml_parser import YamlPlaylistParser

app = typer.Typer()

@app.command()
def download(
    paths: Annotated[
        list[str],
        typer.Argument(
            ...,
            metavar="[PLAYLIST_FILE] OUTPUT_DIR",
            help="Use PLAYLIST_FILE OUTPUT_DIR, or only OUTPUT_DIR with --search/--from-url.",
        ),
    ],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing files instead of creating numbered copies."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show per-track progress details."),
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option("--limit", min=1, help="Download at most this many tracks."),
    ] = None,
    start_from: Annotated[
        int,
        typer.Option("--start-from", min=0, help="Zero-based index in the YAML track array."),
    ] = 0,
    show_url: Annotated[
        bool,
        typer.Option("--show-url", help="Show the resolved source URL in the final summary."),
    ] = False,
    smart_search: Annotated[
        bool,
        typer.Option("--smart-search", help="Inspect multiple search results and auto-pick the best match."),
    ] = False,
    review_search: Annotated[
        bool,
        typer.Option("--review-search", help="Review search candidates interactively before downloading."),
    ] = False,
    candidate_count: Annotated[
        int,
        typer.Option("--candidate-count", min=1, help="Number of search candidates to inspect."),
    ] = 10,
    prefer_official: Annotated[
        bool,
        typer.Option("--prefer-official", help="Prefer candidates that look like official or auto-generated releases."),
    ] = False,
    search: Annotated[
        tuple[str, str, str, int] | None,
        typer.Option(
            "--search",
            help="Download a single track using TITLE ARTIST ALBUM POSITION instead of a playlist file.",
            metavar="TITLE ARTIST ALBUM POSITION",
        ),
    ] = None,
    from_url: Annotated[
        tuple[str, str, str, str, int] | None,
        typer.Option(
            "--from-url",
            help="Download a single track from URL using URL TITLE ARTIST ALBUM POSITION.",
            metavar="URL TITLE ARTIST ALBUM POSITION",
        ),
    ] = None,
) -> None:
    service = _build_download_service(verbose=verbose, show_url=show_url)
    options = _build_download_options(
        overwrite=overwrite,
        verbose=verbose,
        limit=limit,
        start_from=start_from,
        show_url=show_url,
        smart_search=smart_search,
        review_search=review_search,
        candidate_count=candidate_count,
        prefer_official=prefer_official,
    )
    dispatcher = build_download_mode_dispatcher()
    summary = dispatcher.dispatch(
        DownloadCommandInput(paths=paths, search=search, from_url=from_url),
        service=service,
        options=options,
    )
    if summary.failed_count:
        raise typer.Exit(code=4)

def _build_download_service(verbose: bool, show_url: bool) -> PlaylistDownloadService:
    return PlaylistDownloadService(
        parser=YamlPlaylistParser(),
        downloader=YtDlpTrackDownloader(),
        metadata_writer=Id3MetadataWriter(),
        reporter=RichDownloadReporter(verbose=verbose, show_url=show_url),
        skipped_tracks_writer=SkippedTracksWriter(),
        unresolved_tracks_writer=UnresolvedTracksWriter(),
        failed_tracks_writer=FailedTracksWriter(),
    )

def _build_download_options(
    overwrite: bool,
    verbose: bool,
    limit: int | None,
    start_from: int,
    show_url: bool,
    smart_search: bool,
    review_search: bool,
    candidate_count: int,
    prefer_official: bool,
) -> DownloadOptions:
    if limit is not None and limit <= 0:
        raise typer.BadParameter("--limit must be greater than zero.")
    if start_from < 0:
        raise typer.BadParameter("--start-from must be zero or greater.")
    if candidate_count <= 0:
        raise typer.BadParameter("--candidate-count must be greater than zero.")
    if smart_search and review_search:
        raise typer.BadParameter("--smart-search and --review-search cannot be used together.")

    return DownloadOptions(
        overwrite=overwrite,
        verbose=verbose,
        limit=limit,
        start_from=start_from,
        show_url=show_url,
        smart_search=smart_search,
        review_search=review_search,
        candidate_count=candidate_count,
        prefer_official=prefer_official,
    )
