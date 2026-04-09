from __future__ import annotations

import json
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
            "Quando Eu Me Chamar Saudade, Nelson Cavaquinho, Serie Documento - Nelson Cavaquinho",
            query,
        )

    def test_search_candidates_parses_json_results(self) -> None:
        track = Track(nome="Song", artistas=["Artist"], album="Album")
        downloader = YtDlpTrackDownloader(python_executable="python-test")
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "id": "abc",
                        "title": "Song - Artist",
                        "channel": "Artist - Topic",
                        "duration": 180,
                        "webpage_url": "https://www.youtube.com/watch?v=abc",
                    }
                ),
                json.dumps(
                    {
                        "id": "def",
                        "title": "Song (Cover)",
                        "uploader": "Someone",
                        "duration": 181,
                        "url": "def",
                    }
                ),
            ]
        )
        with patch(
            "playlist_downloader.downloader.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=0, stdout=stdout, stderr=""),
        ):
            candidates = downloader.search_candidates(track, 2)

        self.assertEqual(2, len(candidates))
        self.assertEqual("Song - Artist", candidates[0].title)
        self.assertEqual("https://www.youtube.com/watch?v=def", candidates[1].webpage_url)

    def test_download_candidate_overwrites_existing_file_when_requested(self) -> None:
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
                stdout=f"https://youtube.test/watch?v=123\n{source_path}\n",
                stderr="",
            )

            with patch("playlist_downloader.downloader.subprocess.run", return_value=completed_process):
                result = downloader.download_candidate(
                    track=track,
                    candidate=type("Candidate", (), {"webpage_url": "https://youtube.test/watch?v=123"})(),
                    output_dir=output_dir,
                    overwrite=True,
                )
                final_bytes = destination.read_bytes()

        self.assertEqual(destination, result.filepath)
        self.assertEqual(b"new", final_bytes)

    def test_download_skips_existing_file_without_overwrite(self) -> None:
        track = Track(nome="Faixa", artistas=["Artista"], album="Album", posicao=1)
        downloader = YtDlpTrackDownloader(python_executable="python-test")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            destination = output_dir / "Faixa - Artista.mp3"
            destination.write_bytes(b"existing")

            with patch("playlist_downloader.downloader.subprocess.run") as run_mock:
                result = downloader.download(track, output_dir, overwrite=False)

        self.assertEqual(destination, result.filepath)
        self.assertTrue(result.skipped)
        self.assertIsNone(result.source_url)
        run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
