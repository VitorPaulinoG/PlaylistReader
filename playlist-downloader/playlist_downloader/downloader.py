from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from playlist_downloader.models import Track


class DownloadError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class DownloadArtifact:
    filepath: Path
    source_url: str | None = None


def build_search_query(track: Track) -> str:
    return "ytsearch1:" + ", ".join(track.search_terms())


def sanitize_filename(name: str) -> str:
    for char in '<>:"/\\|?*':
        name = name.replace(char, "")
    return name.strip()


@dataclass(slots=True)
class YtDlpTrackDownloader:
    python_executable: str = sys.executable

    def download(self, track: Track, output_dir: Path, overwrite: bool = False) -> DownloadArtifact:
        query = build_search_query(track)
        output_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            self._build_command(output_dir, query),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise DownloadError(f"yt-dlp failed for '{track.nome}': {stderr}")

        artifact = self._extract_download_artifact(result.stdout)
        final_path = self._move_to_track_name(artifact.filepath, output_dir, track, overwrite)
        return DownloadArtifact(filepath=final_path, source_url=artifact.source_url)

    def _build_command(self, output_dir: Path, query: str) -> list[str]:
        return [
            self.python_executable,
            "-m",
            "yt_dlp",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",
            "-o",
            str(output_dir / "%(id)s.%(ext)s"),
            "--no-playlist",
            "--print",
            "webpage_url",
            "--print",
            "after_move:filepath",
            query,
        ]

    @staticmethod
    def _extract_download_artifact(stdout: str) -> DownloadArtifact:
        source_url: str | None = None
        filepath: Path | None = None

        for line in (line.strip() for line in stdout.splitlines() if line.strip()):
            if line.startswith(("http://", "https://")):
                source_url = line
                continue

            candidate_path = Path(line)
            if candidate_path.is_file():
                filepath = candidate_path

        if filepath is None:
            raise DownloadError(f"Unexpected yt-dlp output: {stdout}")
        return DownloadArtifact(filepath=filepath, source_url=source_url)

    @staticmethod
    def _move_to_track_name(
        source_path: Path,
        output_dir: Path,
        track: Track,
        overwrite: bool,
    ) -> Path:
        desired_name = sanitize_filename(track.titulo_exibicao)
        destination = output_dir / f"{desired_name}.mp3"
        if source_path == destination:
            return source_path

        if overwrite:
            if destination.exists():
                destination.unlink()
            source_path.replace(destination)
            return destination

        counter = 2
        while destination.exists():
            destination = output_dir / f"{desired_name} ({counter}).mp3"
            counter += 1

        source_path.rename(destination)
        return destination


def download_track(track: Track, output_dir: Path) -> Path:
    return YtDlpTrackDownloader().download(track, output_dir).filepath
