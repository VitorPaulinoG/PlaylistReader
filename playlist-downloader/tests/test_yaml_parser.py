from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from playlist_downloader.yaml_parser import YamlPlaylistParser


class YamlPlaylistParserTest(unittest.TestCase):
    def test_parse_uses_defaults_for_missing_fields(self) -> None:
        yaml_content = textwrap.dedent(
            """
            playlist:
              nome: "Teste"
              musicas:
                - nome: "Faixa 1"
            """
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            yaml_path = Path(temp_dir) / "playlist.yaml"
            yaml_path.write_text(yaml_content, encoding="utf-8")

            playlist = YamlPlaylistParser().parse(yaml_path)

        self.assertEqual("Teste", playlist.nome)
        self.assertEqual(1, len(playlist.musicas))
        track = playlist.musicas[0]
        self.assertEqual("Faixa 1", track.nome)
        self.assertEqual([], track.artistas)
        self.assertEqual("Desconhecido", track.album)
        self.assertEqual("0:00", track.duracao)
        self.assertEqual("Desconhecida", track.data_lancamento)
        self.assertEqual(0, track.posicao)
        self.assertEqual("Desconhecido", track.primeiro_artista)


if __name__ == "__main__":
    unittest.main()
