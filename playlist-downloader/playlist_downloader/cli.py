from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from playlist_downloader.downloader import YtDlpTrackDownloader
from playlist_downloader.metadata import Id3MetadataWriter
from playlist_downloader.reporters import RichDownloadReporter
from playlist_downloader.skipped_tracks import SkippedTracksWriter
from playlist_downloader.services import DownloadOptions, PlaylistDownloadService
from playlist_downloader.unresolved_tracks import UnresolvedTracksWriter
from playlist_downloader.yaml_parser import YamlPlaylistParser

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Download playlist tracks as MP3 files with ID3 metadata.",
)


@app.callback()
def entrypoint() -> None:
    """Playlist downloader CLI."""


def _build_service(verbose: bool, show_url: bool) -> PlaylistDownloadService:
    return PlaylistDownloadService(
        parser=YamlPlaylistParser(),
        downloader=YtDlpTrackDownloader(),
        metadata_writer=Id3MetadataWriter(),
        reporter=RichDownloadReporter(verbose=verbose, show_url=show_url),
        skipped_tracks_writer=SkippedTracksWriter(),
        unresolved_tracks_writer=UnresolvedTracksWriter(),
    )


def _build_options(
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


def _resolve_paths(paths: list[str], search: tuple[str, str, str] | None) -> tuple[Path | None, Path]:
    if search is None:
        if len(paths) != 2:
            raise typer.BadParameter(
                "download expects PLAYLIST_FILE OUTPUT_DIR when --search is not used."
            )
        playlist_file = Path(paths[0])
        if not playlist_file.is_file():
            raise typer.BadParameter(f"Playlist file '{playlist_file}' was not found.")
        return playlist_file, Path(paths[1])

    if len(paths) != 1:
        raise typer.BadParameter(
            "download expects only OUTPUT_DIR when --search is used."
        )
    return None, Path(paths[0])


@app.command()
def download(
    paths: Annotated[
        list[str],
        typer.Argument(
            ...,
            metavar="[PLAYLIST_FILE] OUTPUT_DIR",
            help="Use PLAYLIST_FILE OUTPUT_DIR, or only OUTPUT_DIR with --search.",
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
        tuple[str, str, str] | None,
        typer.Option(
            "--search",
            help="Download a single track using TITLE ARTIST ALBUM instead of a playlist file.",
            metavar="TITLE ARTIST ALBUM",
        ),
    ] = None,
) -> None:
    playlist_file, output_dir = _resolve_paths(paths, search)
    output_dir.mkdir(parents=True, exist_ok=True)

    if search is not None and (limit is not None or start_from != 0):
        raise typer.BadParameter("--limit and --start-from cannot be used with --search.")

    service = _build_service(verbose=verbose, show_url=show_url)
    options = _build_options(
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

    if search is None:
        summary = service.run_playlist(playlist_file, output_dir, options)
    else:
        title, artist, album = search
        summary = service.run_search(title, artist, album, output_dir, options)

    if summary.failed_count:
        raise typer.Exit(code=4)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
