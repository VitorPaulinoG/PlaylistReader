from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console
from rich.table import Table

from playlist_downloader.downloader import DownloadArtifact
from playlist_downloader.models import Track
from playlist_downloader.services import DownloadSummary


@dataclass(slots=True)
class RichDownloadReporter:
    verbose: bool = False
    show_url: bool = False
    console: Console = field(default_factory=Console)

    def on_collection_start(self, label: str, total_tracks: int) -> None:
        if not self.verbose:
            return
        self.console.print(f"[bold]Collection:[/bold] {label}")
        self.console.print(f"[bold]Tracks to process:[/bold] {total_tracks}")

    def on_track_start(self, index: int, total_tracks: int, track: Track) -> None:
        if not self.verbose:
            return
        self.console.print(f"[{index}/{total_tracks}] Downloading: {track.titulo_exibicao}")

    def on_track_success(
        self,
        index: int,
        total_tracks: int,
        track: Track,
        artifact: DownloadArtifact,
    ) -> None:
        if not self.verbose:
            return
        self.console.print(f"  Saved: {artifact.filepath.name}")

    def on_track_skipped(
        self,
        index: int,
        total_tracks: int,
        track: Track,
        artifact: DownloadArtifact,
    ) -> None:
        self.console.print(
            f"[yellow]Skipped[/yellow] [{index}/{total_tracks}] {track.titulo_exibicao}: {artifact.filepath.name}"
        )

    def on_track_failure(self, index: int, total_tracks: int, track: Track, error: str) -> None:
        self.console.print(f"[red]Error[/red] [{index}/{total_tracks}] {track.titulo_exibicao}: {error}")

    def on_collection_finished(self, summary: DownloadSummary) -> None:
        table = Table(title="Download Summary")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Mode", summary.mode)
        table.add_row("Source", summary.label)
        table.add_row("Total", str(summary.total_tracks))
        table.add_row("Downloaded", str(summary.downloaded_count))
        table.add_row("Failed", str(summary.failed_count))
        table.add_row("Skipped", str(summary.skipped_count))
        self.console.print(table)

        if summary.skipped_manifest_path is not None:
            self.console.print(
                f"[bold]Skipped manifest:[/bold] {summary.skipped_manifest_path}"
            )

        if not self.show_url:
            return

        successful_results = [
            result for result in summary.results if result.success and result.source_url
        ]
        if not successful_results:
            return

        url_table = Table(title="Resolved URLs")
        url_table.add_column("Track")
        url_table.add_column("URL")
        for result in successful_results:
            url_table.add_row(result.track.titulo_exibicao, result.source_url or "")
        self.console.print(url_table)
