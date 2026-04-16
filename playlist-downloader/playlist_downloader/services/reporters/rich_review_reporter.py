from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console
from rich.table import Table

from playlist_downloader.models.playlist import Track
from playlist_downloader.models.review_summary import ReviewSummary


@dataclass(slots=True)
class RichReviewReporter:
    console: Console = field(default_factory=Console)

    def on_collection_start(self, label: str, total_tracks: int) -> None:
        self.console.print(f"[bold]Reviewing playlist:[/bold] {label}")
        self.console.print(f"[bold]Tracks to review:[/bold] {total_tracks}")

    def on_track_missing(self, index: int, total_tracks: int, track: Track) -> None:
        self.console.print(
            "[yellow]Missing[/yellow] "
            f"[{index}/{total_tracks}] "
            f"posicao={track.posicao} nome={track.nome} artista={track.primeiro_artista} album={track.album}"
        )

    def on_collection_finished(self, summary: ReviewSummary) -> None:
        table = Table(title="Review Summary")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Playlist", summary.label)
        table.add_row("Total", str(summary.total_tracks))
        table.add_row("Missing", str(summary.missing_count))
        self.console.print(table)

        if summary.missing_manifest_path is not None:
            self.console.print(
                f"[bold]Missing manifest:[/bold] {summary.missing_manifest_path}"
            )
