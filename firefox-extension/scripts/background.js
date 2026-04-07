// background.js - Background service worker (Manifest V3)
// Gerencia o fluxo de scraping: recebe eventos do inject.js via content script,
// gera YAML a partir dos dados coletados do DOM e dispara o download.

(function () {
  "use strict";

  // Estado atual do scraping
  let scrapState = {
    isPlaylistPage: false,
    playlistId: null,
    playlistName: null,
    isScraping: false,
  };

  /**
   * Escuta mensagens do content script e do popup.
   */
  browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    console.log("[Background] Received message:", msg.type, msg.data || msg);

    // SCRAPE_EVENT: vem do inject.js (reencaminhado pelo content script)
    if (msg.type === "SCRAPE_EVENT" && msg.data) {
      handleScrapeEvent(msg.data);
      return;
    }

    // REQUEST_STATUS: popup pedindo estado atual
    if (msg.type === "REQUEST_STATUS") {
      console.log("[Background] State:", scrapState);
      sendResponse({
        isPlaylistPage: scrapState.isPlaylistPage,
        playlistId: scrapState.playlistId,
        playlistName: scrapState.playlistName,
        isScraping: scrapState.isScraping,
      });
      return true;
    }

    // EXPORT_PLAYLIST: popup pedindo para iniciar o scraping
    if (msg.type === "EXPORT_PLAYLIST") {
      startScrape();
      return true;
    }
  });

  console.log("[Background] Script loaded!");

  /**
   * Inicia o scraping pedindo ao injet-script para comecar.
   */
  function startScrape() {
    if (scrapState.isScraping) return;
    scrapState.isScraping = true;

    broadcastTabs({ type: "SCRAPE_PLAYLIST" });
    updateStatus("scraping", "Iniciando coleta da playlist...");
  }

  /**
   * Envia uma mensagem para todas as abas do Spotify.
   */
  function broadcastTabs(msg) {
    browser.tabs.query({ url: "https://open.spotify.com/*" }).then((tabs) => {
      for (const tab of tabs) {
        browser.tabs.sendMessage(tab.id, msg).catch(() => {});
      }
    }).catch(() => {});
  }

  /**
   * Processa eventos recebidos do inject.js.
   */
  function handleScrapeEvent(data) {
    switch (data.type) {
      case "state":
        scrapState.isPlaylistPage = data.isPlaylistPage || false;
        scrapState.playlistId = data.playlistId || null;
        scrapState.playlistName = data.playlistName || null;
        break;

      case "scraping_start":
        scrapState.playlistName = data.playlistName || "Playlist";
        scrapState.isScraping = true;
        updateStatus("scraping", "Coletando faixas da playlist...");
        break;

      case "progress":
        if (data.count > 0) {
          updateStatus("progress", `Coletadas ${data.count} faixas ate agora...`);
        }
        break;

      case "done":
        scrapState.isScraping = false;
        const tracks = data.tracks || [];
        const name = data.playlistName || scrapState.playlistName || "Playlist";

        updateStatus("exporting", `Gerando YAML com ${tracks.length} faixas...`);

        const yamlContent = generateYaml(name, tracks);
        const filename = sanitizeFilename(`${name}.yaml`);
        downloadYaml(yamlContent, filename);
        updateStatus("done", `Exportado com sucesso! ${tracks.length} faixas.`);
        break;

      case "error":
        scrapState.isScraping = false;
        updateStatus("error", data.message || "Erro desconhecido.");
        break;
    }
  }

  /**
   * Gera YAML no formato especificado em app-idea.md.
   */
  function generateYaml(playlistName, tracks) {
    if (typeof jsyaml !== "undefined" && jsyaml.dump) {
      const data = {
        playlist: {
          nome: playlistName,
          musicas: tracks.map(track => ({
            nome: track.nome,
            artistas: track.artistas,
            album: track.album,
            duracao: track.duracao,
            data_lancamento: track.data_lancamento,
            posicao: track.posicao,
          })),
        },
      };

      return jsyaml.dump(data, {
        indent: 2,
        lineWidth: -1,
        noRefs: true,
      });
    }

    // Fallback manual YAML
    let yaml = `playlist:\n`;
    yaml += `  nome: "${escapeYaml(playlistName)}"\n`;
    yaml += `  musicas:\n`;

    for (const t of tracks) {
      yaml += `    - nome: "${escapeYaml(t.nome)}"\n`;
      yaml += `      artistas:\n`;
      for (const a of t.artistas) {
        yaml += `        - "${escapeYaml(a)}"\n`;
      }
      yaml += `      album: "${escapeYaml(t.album)}"\n`;
      yaml += `      duracao: "${t.duracao}"\n`;
      yaml += `      data_lancamento: "${t.data_lancamento}"\n`;
      yaml += `      posicao: ${t.posicao}\n`;
    }

    return yaml;
  }

  function escapeYaml(str) {
    if (!str) return "";
    return String(str).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }

  /**
   * Dispara download do YAML.
   */
  function downloadYaml(content, filename) {
    const blob = new Blob([content], { type: "text/yaml;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    browser.downloads.download({
      url: url,
      filename: `playlist-reader-${filename}`,
      saveAs: true,
    }).then(() => {
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    }).catch((err) => {
      updateStatus("error", `Falha ao baixar: ${err.message}`);
    });
  }

  /**
   * Envia status ao popup.
   */
  function updateStatus(status, message) {
    browser.runtime.sendMessage({
      type: "STATUS_UPDATE",
      status: status,
      message: message,
    }).catch(() => {});
  }

  /**
   * Sanitiza nome de arquivo.
   */
  function sanitizeFilename(name) {
    return name
      .replace(/[<>:"/\\|?*\x00-\x1F]/g, "")
      .replace(/\s+/g, "_")
      .substring(0, 100) + ".yaml";
  }

})();
