# PlaylistReader - Firefox Extension

Extensao que exporta playlists do Spotify Web Player para um arquivo YAML com informacoes de cada faixa. Nao requer conta Premium nem credenciais da API — usa scraping do DOM da pagina.

## Como Instalar

### Carregamento Temporario (para uso pessoal)

1. Abra o Firefox e navegue ate `about:debugging`
2. Clique em **"Este Firefox"** na barra lateral
3. Clique em **"Carregar Extensao Temporaria..."**
4. Selecione qualquer arquivo dentro da pasta `firefox-extension/` (ex: `manifest.json`)
5. A extensao sera carregada e ficara ativa ate o Firefox ser fechado

### Instalacao Permanente

Para uso permanente, carregue via arquivo `.xpi`:

1. Instale a ferramenta `web-ext`: `npm install -g web-ext`
2. Na pasta `firefox-extension/`, execute: `web-ext build`
3. O arquivo `.xpi` sera gerado em `web-ext-artifacts/`
4. Arraste o `.xpi` para a janela `about:addons` no Firefox

## Como Usar

1. Acesse https://open.spotify.com e faca login na sua conta
2. Navegue ate a playlist que deseja exportar (deve estar totalmente carregada)
3. Clique no icone da extensao **PlaylistReader** na barra de ferramentas
4. O popup mostrara a playlist detectada. Clique em **"Exportar Playlist"**
5. A extensao fara o auto-scroll para carregar todas as faixas via lazy-load
6. O arquivo YAML sera baixado automaticamente com todas as faixas

## O arquivo YAML contera

```yaml
playlist:
  nome: "Nome da Playlist"
  musicas:
    - nome: "Nome da Musica"
      artistas:
        - "Nome do Artista 1"
        - "Nome do Artista 2"
      album: "Nome do Album"
      duracao: "2:39"
      data_lancamento: "24 de set. de 2019"
      posicao: 1
```

## Solucao de Problemas

- **"Nenhuma playlist detectada"**: Certifique-se de que esta em `open.spotify.com/playlist/<id>`. Recarregue a pagina (F5) e reabra o popup.
- **Scroll nao funciona / parou no meio**: Verifique sua conexao. O auto-scroll aguarda o carregamento de cada bloco de faixas. Em playlists muito grandes, pode demorar.
- **Dados faltando em alguma faixa**: O scraping depende do conteudo visivel no DOM. Role manualmente a pagina e tente exportar novamente.

## Requisitos

- Firefox 109 ou superior (suporte a Manifest V3)
- Conta ativa no Spotify (Free ou Premium)
- Estar logado no Spotify Web Player
