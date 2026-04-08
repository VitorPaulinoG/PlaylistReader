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

    from playlist_downloader.downloader import YtDlpTrackDownloader
    from playlist_downloader.metadata import Id3MetadataWriter
    from playlist_downloader.services import PlaylistDownloadService
    from playlist_downloader.yaml_parser import YamlPlaylistParser

    service = PlaylistDownloadService(
        parser=YamlPlaylistParser(),
        downloader=YtDlpTrackDownloader(),
        metadata_writer=Id3MetadataWriter(),
        output=sys.stdout,
    )
    service.run(yaml_path, output_dir)


if __name__ == "__main__":
    main()
