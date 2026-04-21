from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import typer

from playlist_downloader.models.download_options import DownloadOptions
from playlist_downloader.services.playlist_download_service import PlaylistDownloadService
from playlist_downloader.utils.file_utils import resolve_file


@dataclass(frozen=True, slots=True)
class DownloadCommandInput:
    paths: list[str]
    search: tuple[str, str, str, int] | None = None
    from_url: tuple[str, str, str, str, int] | None = None


class DownloadModeStrategy(Protocol):
    key: str

    def supports(self, command_input: DownloadCommandInput) -> bool: ...
    def validate(self, command_input: DownloadCommandInput, options: DownloadOptions) -> None: ...
    def execute(
        self,
        command_input: DownloadCommandInput,
        service: PlaylistDownloadService,
        options: DownloadOptions,
    ): ...


@dataclass(frozen=True, slots=True)
class PlaylistModeStrategy:
    key: str = "playlist"

    def supports(self, command_input: DownloadCommandInput) -> bool:
        return command_input.search is None and command_input.from_url is None

    def validate(self, command_input: DownloadCommandInput, options: DownloadOptions) -> None:
        if len(command_input.paths) != 2:
            raise typer.BadParameter(
                "download expects PLAYLIST_FILE OUTPUT_DIR when neither --search nor --from-url is used."
            )

    def execute(
        self,
        command_input: DownloadCommandInput,
        service: PlaylistDownloadService,
        options: DownloadOptions,
    ):
        playlist_file = resolve_file(command_input.paths[0])
        output_dir = Path(command_input.paths[1])
        output_dir.mkdir(parents=True, exist_ok=True)
        return service.run_playlist(playlist_file, output_dir, options)


@dataclass(frozen=True, slots=True)
class SearchModeStrategy:
    key: str = "search"

    def supports(self, command_input: DownloadCommandInput) -> bool:
        return command_input.search is not None

    def validate(self, command_input: DownloadCommandInput, options: DownloadOptions) -> None:
        if len(command_input.paths) != 1:
            raise typer.BadParameter("download expects only OUTPUT_DIR when --search is used.")
        if options.limit is not None or options.start_from != 0:
            raise typer.BadParameter("--limit and --start-from cannot be used with --search.")

    def execute(
        self,
        command_input: DownloadCommandInput,
        service: PlaylistDownloadService,
        options: DownloadOptions,
    ):
        output_dir = Path(command_input.paths[0])
        output_dir.mkdir(parents=True, exist_ok=True)
        title, artist, album, position = command_input.search  # type: ignore[misc]
        return service.run_search(title, artist, album, position, output_dir, options)


@dataclass(frozen=True, slots=True)
class FromUrlModeStrategy:
    key: str = "from_url"

    def supports(self, command_input: DownloadCommandInput) -> bool:
        return command_input.from_url is not None

    def validate(self, command_input: DownloadCommandInput, options: DownloadOptions) -> None:
        if len(command_input.paths) != 1:
            raise typer.BadParameter("download expects only OUTPUT_DIR when --from-url is used.")
        if options.limit is not None or options.start_from != 0:
            raise typer.BadParameter("--limit and --start-from cannot be used with --from-url.")
        if options.smart_search or options.review_search:
            raise typer.BadParameter("--smart-search and --review-search cannot be used with --from-url.")
        if options.prefer_official:
            raise typer.BadParameter("--prefer-official cannot be used with --from-url.")
        if options.candidate_count != 10:
            raise typer.BadParameter("--candidate-count cannot be used with --from-url.")

    def execute(
        self,
        command_input: DownloadCommandInput,
        service: PlaylistDownloadService,
        options: DownloadOptions,
    ):
        output_dir = Path(command_input.paths[0])
        output_dir.mkdir(parents=True, exist_ok=True)
        url, title, artist, album, position = command_input.from_url  # type: ignore[misc]
        return service.run_from_url(url, title, artist, album, position, output_dir, options)


@dataclass(slots=True)
class DownloadModeDispatcher:
    strategies: tuple[DownloadModeStrategy, ...]

    def dispatch(
        self,
        command_input: DownloadCommandInput,
        service: PlaylistDownloadService,
        options: DownloadOptions,
    ):
        selected_strategies = [strategy for strategy in self.strategies if strategy.supports(command_input)]
        if len(selected_strategies) != 1:
            raise typer.BadParameter("Choose exactly one input mode: playlist file, --search, or --from-url.")

        strategy = selected_strategies[0]
        strategy.validate(command_input, options)
        return strategy.execute(command_input, service, options)


def build_download_mode_dispatcher() -> DownloadModeDispatcher:
    return DownloadModeDispatcher(
        strategies=(
            PlaylistModeStrategy(),
            SearchModeStrategy(),
            FromUrlModeStrategy(),
        )
    )
