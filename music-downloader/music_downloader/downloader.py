import re
import subprocess
import sys
from pathlib import Path


class DownloadError(Exception):
    pass


def build_search_query(track) -> str:
    parts = [track.nome]
    if track.primeiro_artista:
        parts.append(track.primeiro_artista)
    if track.album:
        parts.append(track.album)
    return "ytsearch1:" + ", ".join(parts)


def sanitize_filename(name: str) -> str:
    for char in '<>:"/\\|?*':
        name = name.replace(char, '')
    return name.strip()


def download_track(track, output_dir: Path) -> Path:
    query = build_search_query(track)
    output_dir.mkdir(parents=True, exist_ok=True)

    outtmpl = str(output_dir / "%(id)s.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", outtmpl,
        "--no-playlist",
        "--print", "after_move:filepath",
        query,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise DownloadError(f"yt-dlp failed for '{track.nome}': {result.stderr}")

    lines = result.stdout.strip().split("\n")
    downloaded = lines[-1].strip()
    if not downloaded or not Path(downloaded).is_file():
        raise DownloadError(f"Unexpected yt-dlp output: {result.stdout}")

    # Renomear com o nome do YAML
    desired_name = sanitize_filename(f"{track.nome} - {track.primeiro_artista}")
    dest = output_dir / f"{desired_name}.mp3"
    src = Path(downloaded)
    if src != dest:
        # Evita sobrescrever se ja existir
        counter = 2
        while dest.exists():
            dest = output_dir / f"{desired_name} ({counter}).mp3"
            counter += 1
        src.rename(dest)

    return dest
