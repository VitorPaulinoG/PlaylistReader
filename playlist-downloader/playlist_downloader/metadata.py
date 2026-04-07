from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TRCK


def set_metadata(filepath: Path, track) -> None:
    """Set ID3 tags on the MP3 file: title, artist, album, track number."""
    display_title = f"{track.nome} - {track.primeiro_artista}"

    try:
        tags = ID3(str(filepath))
    except ID3NoHeaderError:
        tags = ID3()
        tags.save(str(filepath))
        tags = ID3(str(filepath))

    tags["TIT2"] = TIT2(encoding=3, text=display_title)
    tags["TPE1"] = TPE1(encoding=3, text=track.artistas)
    tags["TALB"] = TALB(encoding=3, text=track.album)
    tags["TRCK"] = TRCK(encoding=3, text=str(track.posicao))
    tags.save(str(filepath))
