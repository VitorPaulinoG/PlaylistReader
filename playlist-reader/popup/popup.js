// popup.js - Interface do usuario
// Comunica com o background para verificar se ha playlist aberta e iniciar scraping.

(function () {
  "use strict";

  const STATUS_MAP = {
    waiting: {
      cssClass: "status-waiting",
      icon: "\u23F3",
      text: "Verificando Spotify...",
    },
    scraping: {
      cssClass: "status-fetching",
      icon: "\u{1F50D}",
      text: "Iniciando coleta...",
    },
    progress: {
      cssClass: "status-progress",
      icon: "\u{1F4E5}",
      text: "Coletando faixas...",
    },
    exporting: {
      cssClass: "status-exporting",
      icon: "\u{1F4E4}",
      text: "Gerando arquivo...",
    },
    done: {
      cssClass: "status-done",
      icon: "\u2705",
      text: "Concluido!",
    },
    error: {
      cssClass: "status-error",
      icon: "\u274C",
      text: "Erro",
    },
  };

  const statusIconEl = document.getElementById("status-icon");
  const statusTextEl = document.getElementById("status-text");
  const statusEl = document.getElementById("status");
  const exportBtn = document.getElementById("export-btn");
  const playlistInfoEl = document.getElementById("playlist-info");
  const playlistNameEl = document.getElementById("playlist-name");
  const progressEl = document.getElementById("progress");
  const progressFillEl = document.getElementById("progress-fill");

  async function init() {
    setStatus("waiting");

    try {
      const response = await browser.runtime.sendMessage({ type: "REQUEST_STATUS" });

      if (response && response.isPlaylistPage && response.playlistId && !response.isScraping) {
        playlistNameEl.textContent = response.playlistName || "Playlist detectada";
        playlistInfoEl.style.display = "flex";
        exportBtn.disabled = false;
      } else if (response && response.isScraping) {
        setStatus("scraping", "Coleta em andamento...");
        exportBtn.disabled = true;
      } else {
        exportBtn.disabled = true;
        setStatus("error");
        statusTextEl.textContent = "Nenhuma playlist detectada. Abra uma playlist em open.spotify.com e aguarde.";
      }
    } catch (err) {
      exportBtn.disabled = true;
      setStatus("error");
      statusTextEl.textContent = "Erro ao comunicar com a extensao.";
    }
  }

  exportBtn.addEventListener("click", async () => {
    exportBtn.disabled = true;
    setStatus("scraping");
    progressEl.style.display = "block";
    updateProgress(0);

    await browser.runtime.sendMessage({ type: "EXPORT_PLAYLIST" });
  });

  // Escuta status updates do background
  browser.runtime.onMessage.addListener((msg) => {
    if (msg.type === "STATUS_UPDATE") {
      const config = STATUS_MAP[msg.status] || STATUS_MAP.waiting;
      statusEl.className = `status ${config.cssClass}`;
      statusIconEl.textContent = config.icon;

      if (msg.message) {
        statusTextEl.textContent = msg.message;
      }

      // Atualiza barra de progresso
      if (msg.status === "progress" && msg.message) {
        const match = msg.message.match(/(\d+)/);
        if (match) {
          const count = parseInt(match[1], 10);
          // Barra incremental (max visual = 95%, pois o fim exato nao e conhecido)
          const pct = Math.min((count / 500) * 100, 95);
          updateProgress(pct);
        }
      }

      if (msg.status === "done") {
        progressEl.style.display = "none";
        setTimeout(() => {
          exportBtn.disabled = false;
          setStatus("waiting", "Verificando Spotify...");
        }, 3000);
      }

      if (msg.status === "error") {
        progressEl.style.display = "none";
        exportBtn.disabled = false;
      }
    }
  });

  function setStatus(status, message) {
    const config = STATUS_MAP[status] || STATUS_MAP.waiting;
    statusEl.className = `status ${config.cssClass}`;
    statusIconEl.textContent = config.icon;
    statusTextEl.textContent = message || config.text;
  }

  function updateProgress(pct) {
    progressFillEl.style.width = `${Math.min(pct, 100)}%`;
  }

  init();

})();
