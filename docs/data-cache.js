/* Shared JSON fetch for the observatory scripts.
   Each data file is requested once per page and the text is shared, so
   observatory.js and webmcp-mission.js never download the same file twice.
   Data files are immutable and versioned by name, so the default HTTP cache
   applies (no cache: "no-store"). Callers get a Response-like object with
   ok, status and json(); each json() call parses its own copy. */
(() => {
  "use strict";

  const entries = new Map();

  function load(url) {
    let entry = entries.get(url);
    if (!entry) {
      entry = fetch(url, { headers: { Accept: "application/json" } }).then(async (response) => ({
        ok: response.ok,
        status: response.status,
        text: response.ok ? await response.text() : "",
      }));
      entries.set(url, entry);
      entry.then((value) => { if (!value.ok) entries.delete(url); }, () => entries.delete(url));
    }
    return entry;
  }

  window.GPUStackData = {
    async fetch(url) {
      const entry = await load(url);
      return { ok: entry.ok, status: entry.status, json: async () => JSON.parse(entry.text) };
    },
  };
})();
