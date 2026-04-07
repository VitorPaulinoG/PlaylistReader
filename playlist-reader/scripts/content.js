// content.js - Ponte entre inject.js (contexto da pagina) e background.js
// Injeta o script de scraping e encaminha eventos via CustomEvent -> runtime.sendMessage

(function () {
  "use strict";

  // Injeta inject.js no contexto da pagina
  function injectScript() {
    const script = document.createElement("script");
    script.src = browser.runtime.getURL("scripts/inject.js");
    (document.head || document.documentElement).appendChild(script);
    console.log("[Content] inject.js injected");
  }

  injectScript();

  // Escuta eventos do inject.js e envia ao background
  window.addEventListener("PlaylistReaderScrape", (event) => {
    let data;
    try {
      data = JSON.parse(event.detail);
    } catch (e) {
      return;
    }
    console.log("[Content] Received from inject.js:", data.type, data);

    // Encaminha ao background
    browser.runtime.sendMessage({
      type: "SCRAPE_EVENT",
      data: data,
    }).then(() => {
      console.log("[Content] Sent to background:", data.type);
    }).catch((err) => {
      console.error("[Content] Failed to send to background:", err);
    });
  });

  // Escuta requisicoes do popup
  browser.runtime.onMessage.addListener((msg) => {
    console.log("[Content] Received from background:", msg);
    if (msg.type === "SCRAPE_PLAYLIST") {
      window.dispatchEvent(new CustomEvent("PlaylistReaderAction", {
        detail: JSON.stringify({ type: "SCRAPE_PLAYLIST" }),
      }));
    }
  });

})();
