import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Baixa músicas de uma playlist (YAML) como MP3 via yt-dlp."
    )
    parser.add_argument("yaml_path", type=str, help="Caminho do arquivo YAML da playlist")
    parser.add_argument("output_dir", type=str, help="Diretório onde os arquivos MP3 serão salvos")
    args = parser.parse_args()

    yaml_path = Path(args.yaml_path)
    if not yaml_path.is_file():
        print(f"Erro: arquivo '{yaml_path}' não encontrado.")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Deferred imports (heavier dependencies)
    from music_downloader.downloader import DownloadError, download_track
    from music_downloader.metadata import set_metadata
    from music_downloader.yaml_parser import parse_playlist

    playlist = parse_playlist(str(yaml_path))
    print(f"[Playlist] {playlist.nome} - {len(playlist.musicas)} faixa(s)")
    print()

    for track in playlist.musicas:
        n = f"[{track.posicao}/{len(playlist.musicas)}]"
        print(f"{n} Baixando: {track.nome} - {track.primeiro_artista}")

        try:
            out_path = download_track(track, output_dir)
        except DownloadError as e:
            print(f"  Erro ao baixar: {e}")
            continue

        print(f"  Editando metadados...")
        try:
            set_metadata(out_path, track)
        except Exception as e:
            print(f"  Erro ao editar metadados: {e}")
        else:
            print(f"  Salvo: {out_path.name}")

        print()

    print("Concluído.")
