// Mounts the story's animated figures and, when present, the word explainers.
(function () {
  function start() {
    if (window.GPUStackFigures) window.GPUStackFigures.mountAll();
    if (window.GPUStackExplain) window.GPUStackExplain.init(document);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
