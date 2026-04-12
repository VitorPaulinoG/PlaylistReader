from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from playlist_downloader.models import Track
from playlist_downloader.search_resolution import SearchCandidate


class DownloadError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class DownloadArtifact:
    filepath: Path | None
    source_url: str | None = None
    skipped: bool = False


def build_search_query(track: Track) -> str:
    search_terms: list[str] = track.search_terms()
    search_terms[0] = "\"{}\"".format(search_terms[0])
    return " - ".join(track.search_terms())


def sanitize_filename(name: str) -> str:
    for char in '<>:"/\\|?*':
        name = name.replace(char, "")
    return name.strip()


@dataclass(slots=True)
class YtDlpTrackDownloader:
    python_executable: str = sys.executable

    def download(self, track: Track, output_dir: Path, overwrite: bool = False) -> DownloadArtifact:
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / f"{sanitize_filename(track.titulo_exibicao)}.mp3"

        if target_path.exists() and not overwrite:
            return DownloadArtifact(filepath=target_path, skipped=True)

        result = subprocess.run(
            self._build_legacy_download_command(output_dir, track),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise DownloadError(f"yt-dlp failed for '{track.nome}': {stderr}")

        artifact = self._extract_download_artifact(result.stdout)
        final_path = self._move_to_track_name(artifact.filepath, output_dir, track, overwrite)
        return DownloadArtifact(filepath=final_path, source_url=artifact.source_url)

    def search_candidates(self, track: Track, candidate_count: int) -> list[SearchCandidate]:
        result = subprocess.run(
            self._build_search_command(track, candidate_count),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise DownloadError(f"yt-dlp search failed for '{track.nome}': {stderr}")
        return self._extract_search_candidates(result.stdout)

    def download_candidate(
        self,
        track: Track,
        candidate: SearchCandidate,
        output_dir: Path,
        overwrite: bool = False,
    ) -> DownloadArtifact:
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / f"{sanitize_filename(track.titulo_exibicao)}.mp3"

        if target_path.exists() and not overwrite:
            return DownloadArtifact(filepath=target_path, skipped=True)

        result = subprocess.run(
            self._build_download_url_command(output_dir, candidate.webpage_url),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise DownloadError(f"yt-dlp failed for '{track.nome}': {stderr}")

        artifact = self._extract_download_artifact(result.stdout)
        final_path = self._move_to_track_name(artifact.filepath, output_dir, track, overwrite)
        return DownloadArtifact(filepath=final_path, source_url=candidate.webpage_url)

    def _build_legacy_download_command(self, output_dir: Path, track: Track) -> list[str]:
        return self._build_download_url_command(
            output_dir=output_dir,
            url=f"ytsearch1:{build_search_query(track)}",
        )

    def _build_search_command(self, track: Track, candidate_count: int) -> list[str]:
        return [
            self.python_executable,
            "-m",
            "yt_dlp",
            "--dump-json",
            "--no-playlist",
            f"ytsearch{candidate_count}:{build_search_query(track)}",
        ]

    def _build_download_url_command(self, output_dir: Path, url: str) -> list[str]:
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
            url,
        ]

    @staticmethod
    def _extract_search_candidates(stdout: str) -> list[SearchCandidate]:
        candidates: list[SearchCandidate] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            webpage_url = data.get("webpage_url") or data.get("url")
            if not webpage_url:
                continue
            if not webpage_url.startswith(("http://", "https://")):
                webpage_url = f"https://www.youtube.com/watch?v={webpage_url}"
            candidates.append(
                SearchCandidate(
                    title=data.get("title", ""),
                    webpage_url=webpage_url,
                    channel=data.get("channel", ""),
                    uploader=data.get("uploader", ""),
                    duration=data.get("duration"),
                    album=data.get("album", ""),
                    artist=data.get("artist", ""),
                    video_id=data.get("id", ""),
                    raw_data=data,
                )
            )
        return candidates

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
