from __future__ import annotations

import typer

from pathlib import Path
from typing import Annotated
from playlist_downloader.utils.file_utils import resolve_file, resolve_folder
from playlist_downloader.services.playlist_review_service import PlaylistReviewService
from playlist_downloader.services.readers.id3_metadata_reader import Id3MetadataReader
from playlist_downloader.services.parsers.yaml_parser import YamlPlaylistParser
from playlist_downloader.services.reporters.rich_review_reporter import RichReviewReporter

app = typer.Typer()

@app.command()
def review(
    path: Annotated[
        list[str],
        typer.Argument(
            ...,
            metavar="YAML_FILE PLAYLIST_FOLDER",
            help="Use YAML_FILE and PLAYLIST_FOLDER to review the entire downloaded playlist comparing to the related yaml file.",
        ),
    ],
) -> None:
    if len(path) != 2:
        raise typer.BadParameter("review expects YAML_FILE PLAYLIST_FOLDER.")
    playlist_file, playlist_folder = [resolve_file(path[0]), resolve_folder(path[1])]

    service = _build_review_service()
    service.review_playlist(playlist_file, playlist_folder)


def _build_review_service() -> PlaylistReviewService: 
    return PlaylistReviewService(
        metadata_reader=Id3MetadataReader(),
        parser=YamlPlaylistParser(),
        reporter=RichReviewReporter(),
    )
    
