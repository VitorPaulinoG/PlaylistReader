# playlist-downloader

CLI que baixa musicas de uma playlist (arquivo YAML) como MP3 via yt-dlp, preenchendo automaticamente os metadados ID3.

## Pre-requisitos

- Python 3.11+
- [FFmpeg](https://ffmpeg.org/) (necessario para `yt-dlp` extrair audio)

## Instalacao

```bash
cd playlist-downloader
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Nos proximos usos, basta ativar o ambiente virtual:

```bash
source .venv/bin/activate
```

## Uso

```bash
playlist-downloader <caminho-do-yaml> <diretorio-saida>
```

### Exemplo

```bash
playlist-downloader playlist.yaml ~/Musicas/MinhaPlaylist
```

### Formato do YAML

O arquivo deve seguir o formato abaixo:

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

## Como funciona

1. **Busca** -- Para cada musica, a busca concatena `nome da musica + primeiro artista + album` usando o prefixo `ytsearch1:` do yt-dlp, que seleciona o primeiro resultado do YouTube.
2. **Download** -- Baixa apenas o audio em MP3 (formato MP3, melhor qualidade).
3. **Metadados** -- Edita as tags ID3 do arquivo MP3:
   - **Titulo**: `Nome da Musica - Primeiro Artista`
   - **Artista**: lista de artistas do YAML
   - **Album**: nome do album
   - **Numero da faixa**: posicao na playlist

## Saida

Cada arquivo MP3 e salvo no diretorio de saida com o nome:

```
Nome da Musica - Primeiro Artista.mp3
```

O CLI mostra o progresso faixa a faixa:

```
[Playlist] Classicos Melodicos BR - 3 faixa(s)

[1/3] Baixando: Quando Eu Me Chamar Saudade - Nelson Cavaquinho
  Editando metadados...
  Salvo: Quando Eu Me Chamar Saudade - Nelson Cavaquinho.mp3

[2/3] Baixando: Juizo Final - Nelson Cavaquinho
  Editando metadados...
  Salvo: Juizo Final - Nelson Cavaquinho.mp3

Concluido.
```
