from __future__ import annotations

import typer

from playlist_downloader.commands.download import download as download_command
from playlist_downloader.commands.review import review as review_command

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Download playlist tracks as MP3 files with ID3 metadata.",
)

app.command(name="download")(download_command)
app.command(name="review")(review_command)

@app.callback()
def entrypoint() -> None:
    """Playlist downloader CLI."""


def main() -> None:
    app()


if __name__ == "__main__":
    main()
