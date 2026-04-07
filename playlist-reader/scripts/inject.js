// inject.js - Injetado no contexto da pagina para interceptar requisicoes do Spotify
// O Spotify usa lista virtualizada que mantem ~28 tracks no DOM.
// A abordagem principal e interceptar requisicoes de rede buscando dados da playlist.
// Fallback: auto-scroll + scraping DOM acumulando tracks em array.

(function () {
  "use strict";

  let playlistId = null;
  let playlistName = null;
  let accumulatedTracks = [];
  let totalExpected = 0;
  let isRunning = false;

  // ===================== XHR INTERCEPT =====================
  const origXHROpen = XMLHttpRequest.prototype.open;
  const origXHRSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url) {
    this._method = method;
    this._url = typeof url === "string" ? url : String(url);
    return origXHROpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function () {
    const xhr = this;
    const url = xhr._url || "";
    this.addEventListener("load", function () {
      interceptResponse(url, xhr.responseText, xhr.status);
    });
    return origXHRSend.apply(this, arguments);
  };

  // ===================== FETCH INTERCEPT =====================
  const origFetch = window.fetch;
  window.fetch = function () {
    const url = arguments[0];
    const urlStr = typeof url === "string" ? url : (url && url.url ? url.url : "");

    return origFetch.apply(this, arguments).then(function (resp) {
      const clone = resp.clone();
      clone.text().then(function (body) {
        interceptResponse(urlStr, body, resp.status);
      }).catch(function () {});
      return resp;
    });
  };

  // ===================== RESPONSE INTERCEPT HANDLER =====================
  function interceptResponse(url, body, status) {
    if (status !== 200 || !body) return;

    try {
      const data = JSON.parse(body);
      if (!data) return;
    } catch (e) {
      return; // nao e JSON
    }

    try {
      processInterceptedData(url, data);
    } catch (e) {
      // ignorar
    }
  }

  function processInterceptedData(url, data) {
    // Endpoint da Spotify API: /playlists/:id/tracks
    if (url.includes("/playlists/") && url.includes("/tracks")) {
      if (data.items && Array.isArray(data.items)) {
        if (data.total && !totalExpected) {
          totalExpected = data.total;
          sendEvent({ type: "total_tracks_found", total: totalExpected });
        }

        const tracks = parseApiTracks(data.items);
        if (tracks.length > 0) {
          accumulatedTracks = accumulatedTracks.concat(tracks);
          fixPositions();
          sendEvent({ type: "progress", count: accumulatedTracks.length, total: totalExpected });

          if (accumulatedTracks.length >= totalExpected) {
            sendEvent({ type: "done", tracks: accumulatedTracks, playlistName, playlistId });
          }
        }
      }
      return;
    }

    // Endpoints internos do web player (spclient/gue1/playlist-view)
    if (url.includes("spclient") || url.includes("wg.spotify")) {
      // Tenta encontrar playlist data no formato interno
      const tracks = findPlaylistTracks(data);
      if (tracks.length > 0 && isRunning) {
        accumulatedTracks = accumulatedTracks.concat(tracks);
        fixPositions();
        sendEvent({ type: "progress", count: accumulatedTracks.length, total: Math.max(totalExpected, accumulatedTracks.length) });
      }
      return;
    }

    // Dados da playlist (formato interno)
    if (data.type === "playlist" && data.content && data.content.items) {
      const tracks = parseInternalTracks(data.content.items);
      if (tracks.length > 0) {
        if (!totalExpected && data.content.total) {
          totalExpected = data.content.total;
        }
        accumulatedTracks = tracks;
        fixPositions();
        sendEvent({ type: "progress", count: accumulatedTracks.length, total: totalExpected });
      }
    }
  }

  /**
   * Busca recursivamente por tracks em objetos complexos do web player.
   */
  function findPlaylistTracks(obj, depth) {
    if (!obj || depth === 10) return [];

    if (Array.isArray(obj)) {
      // Se parece com array de tracks (tem uid, uri com track:, etc)
      if (obj.length > 0 && obj[0] && (obj[0].uid || obj[0].uri)) {
        const looksLikeTracks = obj.some(item =>
          item.uid && (item.uri && item.uri.includes("track:"))
        );
        if (looksLikeTracks) {
          return parseInternalTracks(obj);
        }
      }
      for (const item of obj) {
        const found = findPlaylistTracks(item, (depth || 0) + 1);
        if (found.length > 0) return found;
      }
    }

    if (typeof obj === "object") {
      for (const key of Object.keys(obj)) {
        if (key === "allTrackItems" || key === "items") {
          const found = parseInternalTracks(obj[key]);
          if (found.length > 0) return found;
        }
        const found = findPlaylistTracks(obj[key], (depth || 0) + 1);
        if (found.length > 0) return found;
      }
    }

    return [];
  }

  // ===================== PARSERS =====================

  function parseApiTracks(items) {
    const tracks = [];
    for (const item of items) {
      if (!item || !item.track || !item.track.name) continue;
      const t = item.track;

      tracks.push({
        nome: t.name,
        artistas: (t.artists || []).map(a => a.name).filter(Boolean),
        album: t.album?.name || "Desconhecido",
        duracao: msToDuration(t.duration_ms || 0),
        data_lancamento: t.album?.release_date || "Desconhecida",
        posicao: 0,
      });
    }
    return tracks;
  }

  function parseInternalTracks(items) {
    if (!Array.isArray(items)) return [];
    const tracks = [];
    for (const item of items) {
      if (!item) continue;

      // Formato: { uid, uri: "spotify:track:xxx", attributes: {...}, artists: [...], ... }
      const nome = item.name || (item.trackMetadata && item.trackMetadata.name)
        || (item.itemData && item.itemData.name) || null;
      if (!nome) continue;

      let artistas = [];
      if (item.artists && Array.isArray(item.artists)) {
        artistas = item.artists.map(a => a.name || a).filter(Boolean);
      } else if (item.artist) {
        artistas = [item.artist];
      } else {
        const meta = item.trackMetadata;
        if (meta && meta.artistName) artistas.push(meta.artistName);
      }

      let album = "Desconhecido";
      if (item.album) album = typeof item.album === "string" ? item.album : (item.album.name || "Desconhecido");
      const meta = item.trackMetadata;
      if (meta && meta.albumName) { album = meta.albumName; }

      let duracao = "0:00";
      if (meta && meta.trackDuration) duracao = msToDuration(parseInt(meta.trackDuration, 10));
      else if (item.duration) duracao = msToDuration(parseInt(item.duration, 10));
      else if (item.trackDuration) duracao = msToDuration(parseInt(item.trackDuration, 10));
      else if (item.itemData && item.itemData.duration) duracao = msToDuration(parseInt(item.itemData.duration, 10));

      let releaseDate = "Desconhecida";
      if (meta && meta.release_date) releaseDate = meta.release_date;
      else if (meta && meta.albumUri) {
        // nao temos a data aqui
      }

      tracks.push({ nome, artistas, album, duracao, data_lancamento: releaseDate, posicao: 0 });
    }
    return tracks;
  }

  function msToDuration(ms) {
    if (!ms || isNaN(ms)) return "0:00";
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${String(sec).padStart(2, "0")}`;
  }

  function fixPositions() {
    accumulatedTracks.forEach((t, i) => { t.posicao = i + 1; });
  }

  // ===================== DOM SCRAPE FALLBACK =====================

  async function scrapeDom() {
    accumulatedTracks = [];
    totalExpected = 0;
    let prevCount = 0;
    let stableWaits = 0;
    const MAX_STABLE = 8;
    const SCROLL_PX = 400;
    const WAIT_MS = 2000;

    sendEvent({ type: "progress", message: "Scraping do DOM (lista virtualizada)..." });

    // Coleta todas as tracks ja renderizadas
    const allTracks = [];
    const seenTracks = new Set();

    while (stableWaits < MAX_STABLE) {
      window.scrollBy(0, SCROLL_PX);
      await sleep(WAIT_MS);

      const rows = document.querySelectorAll('[data-testid="tracklist-row"]');
      let newCount = 0;

      for (const row of rows) {
        const link = row.querySelector('[data-testid="internal-track-link"]');
        if (!link) continue;
        const nome = link.textContent.trim();
        if (!nome || seenTracks.has(nome)) continue;
        seenTracks.add(nome);
        newCount++;

        let artistas = [];
        const artistLinks = row.querySelectorAll('a[href*="/artist/"]');
        for (const a of artistLinks) {
          const n = a.textContent.trim();
          if (n && !artistas.includes(n)) artistas.push(n);
        }
        if (!artistas.length) artistas = ["Desconhecido"];

        let album = "Desconhecido";
        const albumLink = row.querySelector('a[href*="/album/"]');
        if (albumLink) album = albumLink.textContent.trim();

        let dataLanc = "Desconhecida";
        const col4 = row.querySelector('[aria-colindex="4"]');
        if (col4) {
          const t = col4.textContent.trim();
          if (t && t.match(/\d/)) dataLanc = t;
        }

        let dur = "0:00";
        const col5 = row.querySelector('[aria-colindex="5"]');
        if (col5) {
          const m = col5.textContent.match(/(\d+:\d{2})/);
          if (m) dur = m[1];
        }

        allTracks.push({ nome, artistas, album, duracao: dur, data_lancamento: dataLanc, posicao: 0 });
      }

      fixPositions(allTracks);

      if (newCount > 0) {
        prevCount += newCount;
        stableWaits = 0;
        sendEvent({ type: "progress", message: `Coletadas ${allTracks.length} faixas via DOM...` });
      } else {
        stableWaits++;
      }
    }

    // Verifica se ha mais tracks que ainda nao foram renderizadas
    // Tenta ir ao fim da pagina e coletar novamente
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(2000);
    window.scrollTo(0, 0);
    await sleep(1000);

    // Re-coleta final
    const finalRows = document.querySelectorAll('[data-testid="tracklist-row"]');
    for (const row of finalRows) {
      const link = row.querySelector('[data-testid="internal-track-link"]');
      if (!link) continue;
      const nome = link.textContent.trim();
      if (!nome || seenTracks.has(nome)) continue;
      seenTracks.add(nome);

      let artistas = [];
      const artistLinks = row.querySelectorAll('a[href*="/artist/"]');
      for (const a of artistLinks) {
        const n = a.textContent.trim();
        if (n && !artistas.includes(n)) artistas.push(n);
      }
      if (!artistas.length) artistas = ["Desconhecido"];

      let album = "Desconhecido";
      const albumLink = row.querySelector('a[href*="/album/"]');
      if (albumLink) album = albumLink.textContent.trim();

      let dataLanc = "Desconhecida";
      const col4 = row.querySelector('[aria-colindex="4"]');
      if (col4) {
        const t = col4.textContent.trim();
        if (t && t.match(/\d/)) dataLanc = t;
      }

      let dur = "0:00";
      const col5 = row.querySelector('[aria-colindex="5"]');
      if (col5) {
        const m = col5.textContent.match(/(\d+:\d{2})/);
        if (m) dur = m[1];
      }

      allTracks.push({ nome, artistas, album, duracao: dur, data_lancamento: dataLanc, posicao: 0 });
    }

    fixPositions(allTracks);

    if (allTracks.length > 0) {
      sendEvent({ type: "done", tracks: allTracks, playlistName, playlistId });
    } else {
      sendEvent({ type: "error", message: "Nao foi possivel extrair faixas do DOM." });
    }
  }

  function fixPositions(tracks) {
    if (!tracks) return;
    tracks.forEach((t, i) => { t.posicao = i + 1; });
  }

  // ===================== SCRAPE ENTRY POINT =====================

  async function scrapePlaylist() {
    isRunning = true;
    accumulatedTracks = [];
    totalExpected = 0;

    const nameEl = document.querySelector('[data-testid="playlist-name"]');
    if (nameEl) playlistName = nameEl.textContent.trim();

    const m = window.location.pathname.match(/^\/playlist\/([a-zA-Z0-9]+)/);
    if (m) playlistId = m[1];

    sendEvent({ type: "scraping_start", playlistId, playlistName });

    // Aguarda alguns segundos para capturar requisicoes que o Spotify faz no load
    sendEvent({ type: "progress", message: "Interceptando requisoes do Spotify..." });
    await sleep(5000);

    if (accumulatedTracks.length > 0 && accumulatedTracks.length >= totalExpected) {
      sendEvent({ type: "progress", message: `Encontradas ${accumulatedTracks.length} faixas via rede.` });
      sendEvent({ type: "done", tracks: accumulatedTracks, playlistName, playlistId });
      return;
    }

    if (accumulatedTracks.length > 0) {
      // Temos algumas tracks mas nao todas via intercept
      // O Spotify talvez use um protocolo nao-JSON (protobuf). Fallback para DOM.
      sendEvent({ type: "progress", message: `${accumulatedTracks.length} faixas via rede. Completando com DOM...` });
    }

    // Fallback: scroll + DOM scrape
    await scrapeDom();
  }

  function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
  }

  // ===================== EVENTS =====================

  function sendEvent(data) {
    window.dispatchEvent(new CustomEvent("PlaylistReaderScrape", { detail: JSON.stringify(data) }));
  }

  window.addEventListener("PlaylistReaderAction", (event) => {
    try {
      const action = JSON.parse(event.detail);
      if (action.type === "SCRAPE_PLAYLIST") {
        scrapePlaylist();
      }
    } catch (e) {}
  });

  // Auto detect playlist page
  function checkPlaylistPage() {
    if (window.location.pathname.match(/^\/playlist\//i)) {
      const m = window.location.pathname.match(/^\/playlist\/([a-zA-Z0-9]+)/);
      if (m) playlistId = m[1];
      const el = document.querySelector('[data-testid="playlist-name"]');
      if (el && el.textContent.trim()) {
        playlistName = el.textContent.trim();
      } else if (document.title && !document.title.startsWith("Spotify")) {
        // Fallback: extrai nome do <title> "Nome - playlist by X | Spotify"
        playlistName = document.title.replace(/\s*[-|].*$/, "").trim();
      } else {
        playlistName = "Playlist";
      }
      sendEvent({ type: "state", isPlaylistPage: true, playlistId, playlistName });
    }
  }
  checkPlaylistPage();

  // Re-check on URL changes (SPA navigation)
  let lastPath = window.location.pathname;
  setInterval(() => {
    if (window.location.pathname !== lastPath) {
      lastPath = window.location.pathname;
      checkPlaylistPage();
    }
  }, 1000);

})();
