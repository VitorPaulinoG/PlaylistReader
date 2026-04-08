from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from playlist_downloader.downloader import YtDlpTrackDownloader, build_search_query
from playlist_downloader.models import Track


class DownloaderTest(unittest.TestCase):
    def test_build_search_query_keeps_expected_order(self) -> None:
        track = Track(
            nome="Quando Eu Me Chamar Saudade",
            artistas=["Nelson Cavaquinho"],
            album="Serie Documento - Nelson Cavaquinho",
        )

        query = build_search_query(track)

        self.assertEqual(
            "ytsearch1:Quando Eu Me Chamar Saudade, Nelson Cavaquinho, Serie Documento - Nelson Cavaquinho",
            query,
        )

    def test_download_renames_file_and_avoids_overwrite(self) -> None:
        track = Track(nome="Faixa", artistas=["Artista"], album="Album", posicao=1)
        downloader = YtDlpTrackDownloader(python_executable="python-test")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            source_path = output_dir / "video-id.mp3"
            source_path.write_bytes(b"mp3")
            existing_destination = output_dir / "Faixa - Artista.mp3"
            existing_destination.write_bytes(b"existing")

            completed_process = CompletedProcess(
                args=[],
                returncode=0,
                stdout=f"https://youtube.test/watch?v=123\n{source_path}\n",
                stderr="",
            )

            with patch("playlist_downloader.downloader.subprocess.run", return_value=completed_process) as run_mock:
                result = downloader.download(track, output_dir)
                self.assertEqual("Faixa - Artista (2).mp3", result.filepath.name)
                self.assertTrue(result.filepath.exists())
                self.assertTrue(existing_destination.exists())
                self.assertEqual("https://youtube.test/watch?v=123", result.source_url)
                run_mock.assert_called_once()
                command = run_mock.call_args.args[0]
                self.assertEqual("python-test", command[0])
                self.assertIn("ytsearch1:Faixa, Artista, Album", command)

    def test_download_overwrites_existing_file_when_requested(self) -> None:
        track = Track(nome="Faixa", artistas=["Artista"], album="Album", posicao=1)
        downloader = YtDlpTrackDownloader(python_executable="python-test")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            source_path = output_dir / "video-id.mp3"
            source_path.write_bytes(b"new")
            destination = output_dir / "Faixa - Artista.mp3"
            destination.write_bytes(b"old")

            completed_process = CompletedProcess(
                args=[],
                returncode=0,
                stdout=f"{source_path}\n",
                stderr="",
            )

            with patch("playlist_downloader.downloader.subprocess.run", return_value=completed_process):
                result = downloader.download(track, output_dir, overwrite=True)
                final_bytes = destination.read_bytes()

        self.assertEqual(destination, result.filepath)
        self.assertEqual(b"new", final_bytes)


if __name__ == "__main__":
    unittest.main()
