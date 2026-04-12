from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from playlist_downloader.cli import app
from playlist_downloader.services import DownloadSummary


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_download_playlist_mode_uses_yaml_and_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            playlist_file = root / "playlist.yaml"
            playlist_file.write_text(
                textwrap.dedent(
                    """
                    playlist:
                      nome: "List"
                      musicas: []
                    """
                ),
                encoding="utf-8",
            )
            output_dir = root / "out"

            with patch("playlist_downloader.cli._build_service") as build_service:
                build_service.return_value.run_playlist.return_value = DownloadSummary(
                    label="List",
                    mode="playlist",
                    total_tracks=0,
                    downloaded_count=0,
                    failed_count=0,
                    skipped_count=0,
                    unresolved_count=0,
                    results=[],
                )
                result = self.runner.invoke(app, ["download", str(playlist_file), str(output_dir)])

        self.assertEqual(0, result.exit_code, result.output)
        build_service.return_value.run_playlist.assert_called_once()

    def test_download_search_mode_uses_output_dir_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "out"

            with patch("playlist_downloader.cli._build_service") as build_service:
                build_service.return_value.run_search.return_value = DownloadSummary(
                    label="Song - Artist",
                    mode="search",
                    total_tracks=1,
                    downloaded_count=1,
                    failed_count=0,
                    skipped_count=0,
                    unresolved_count=0,
                    results=[],
                )
                result = self.runner.invoke(
                    app,
                    [
                        "download",
                        str(output_dir),
                        "--search",
                        "Song",
                        "Artist",
                        "Album",
                        "10",
                        "--smart-search",
                        "--candidate-count",
                        "5",
                        "--prefer-official",
                    ],
                )
        self.assertEqual(0, result.exit_code, result.output)
        _, _, _, _, output_dir_arg, options = build_service.return_value.run_search.call_args.args
        self.assertEqual(output_dir, output_dir_arg)
        self.assertTrue(options.smart_search)
        self.assertEqual(5, options.candidate_count)
        self.assertTrue(options.prefer_official)

    def test_download_rejects_limit_with_search(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "out"
            result = self.runner.invoke(
                app,
                [
                    "download",
                    str(output_dir),
                    "--search",
                    "Song",
                    "Artist",
                    "Album",
                    "10",
                    "--limit",
                    "1",
                ],
            )

        self.assertNotEqual(0, result.exit_code)
        self.assertIn("--limit and --start-from cannot be used with --search.", result.output)

    def test_download_rejects_conflicting_search_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            playlist_file = root / "playlist.yaml"
            playlist_file.write_text("playlist:\n  nome: List\n  musicas: []\n", encoding="utf-8")
            output_dir = root / "out"
            result = self.runner.invoke(
                app,
                [
                    "download",
                    str(playlist_file),
                    str(output_dir),
                    "--smart-search",
                    "--review-search",
                ],
            )

        self.assertNotEqual(0, result.exit_code)
        self.assertIn("--smart-search and --review-search cannot be used together.", result.output)


if __name__ == "__main__":
    unittest.main()
