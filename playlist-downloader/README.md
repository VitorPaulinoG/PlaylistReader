# playlist-downloader

CLI for downloading tracks from a YAML playlist as MP3 files with ID3 metadata, powered by `yt-dlp`.

## Requirements

- Python 3.11+
- [FFmpeg](https://ffmpeg.org/) available on `PATH`

## Installation

```bash
cd playlist-downloader
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The project installs its Python dependencies through `pip`, including `yt-dlp`, `typer`, and `rich`.

## Usage

```bash
playlist-downloader download [OPTIONS] PLAYLIST_FILE OUTPUT_DIR
```

### Playlist mode

Download tracks from a YAML file:

```bash
playlist-downloader download ../context/example.yaml /tmp/playlist-reader-smoke
```

Download a subset of the playlist:

```bash
playlist-downloader download ../context/example.yaml /tmp/playlist-reader-smoke --start-from 1 --limit 1 --show-url
```

### Search mode

Download a single track without a YAML file:

```bash
playlist-downloader download /tmp/playlist-reader-search --search "Juízo Final" "Nelson Cavaquinho" "Nelson Cavaquinho"
```

## Options

- `--overwrite`: replace an existing file with the same final name
- `--verbose`: print per-track progress while downloading
- `--limit INT`: process at most `INT` tracks
- `--start-from INT`: zero-based index into the YAML `musicas` array
- `--show-url`: show resolved source URLs in the final summary
- `--search TITLE ARTIST ALBUM`: download a single manually specified track

`--limit` and `--start-from` are only valid in playlist mode.
When a target file already exists and `--overwrite` is not set, the track is skipped.

## Playlist format

```yaml
playlist:
  nome: "Nome da Playlist"
  musicas:
    - nome: "Quando Eu Me Chamar Saudade"
      artistas:
        - "Nelson Cavaquinho"
        - "Maria Rita"
      album: "Serie Documento - Nelson Cavaquinho"
      duracao: "3:27"
      data_lancamento: "24 de set. de 2019"
      posicao: 1
```

## Behavior

- Search queries are built from `title + first artist + album`.
- Output files are named as `Title - First Artist.mp3`.
- Metadata is written with title, artists, album, and track number.
- Skipped tracks are exported to `OUTPUT_DIR/.playlist-downloader/skipped/<playlist-name>-NNN.skipped.yaml`.
- The numeric suffix is sequential, for example `Clássicos Melódicos BR-001.skipped.yaml`.
- Without `--verbose`, the CLI stays mostly quiet and always prints a final summary.
- With `--show-url`, resolved URLs are listed in the final summary.

## Tests

```bash
cd playlist-downloader
source .venv/bin/activate
PYTHONPATH=. python -m unittest discover -s tests -v
```
