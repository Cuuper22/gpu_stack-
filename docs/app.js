// CuperOS desktop: two windows (Story, Calculator) and a link to the Lab.
// On phones the windows become plain full-width pages with a tab bar on top.
(() => {
  "use strict";

  const phone = window.matchMedia("(max-width: 760px)");
  const windows = {};
  document.querySelectorAll("[data-window]").forEach((node) => { windows[node.dataset.window] = node; });
  const tasks = [...document.querySelectorAll("[data-task]")];
  const tabs = [...document.querySelectorAll(".phone-tabs [data-open]")];
  let front = "story";
  let zCounter = 5;

  function isOpen(name) {
    return Boolean(windows[name]) && !windows[name].hidden;
  }

  function mountCalculator() {
    const root = document.getElementById("calculator-root");
    if (!root || root.dataset.mounted) return;
    const api = window.GPUStackCalculator;
    if (api && typeof api.mount === "function") {
      root.dataset.mounted = "1";
      api.mount(root);
    } else {
      root.replaceChildren();
      const note = document.createElement("p");
      note.className = "coming-soon";
      note.textContent = "Calculator coming soon";
      root.append(note);
    }
  }

  function refresh() {
    tasks.forEach((button) => {
      const name = button.dataset.task;
      button.classList.toggle("is-active", isOpen(name) && front === name);
      button.setAttribute("aria-pressed", String(isOpen(name)));
    });
    tabs.forEach((tab) => {
      if (tab.dataset.open === front) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    });
    Object.entries(windows).forEach(([name, node]) => node.classList.toggle("is-front", isOpen(name) && front === name));
  }

  function open(name, options = {}) {
    const node = windows[name];
    if (!node) return;
    if (phone.matches) {
      Object.entries(windows).forEach(([other, el]) => { el.hidden = other !== name; });
    } else {
      node.hidden = false;
    }
    node.classList.remove("is-max");
    front = name;
    zCounter += 1;
    node.style.zIndex = String(zCounter);
    if (name === "calculator") mountCalculator();
    refresh();
    if (options.updateHash !== false && window.history && window.history.replaceState) {
      const hash = name === "story" && !window.location.hash ? "" : `#${name}`;
      if (window.location.hash !== hash && hash) window.history.replaceState(null, "", hash);
    }
  }

  function close(name) {
    const node = windows[name];
    if (!node || phone.matches) return;
    node.hidden = true;
    if (front === name) {
      front = Object.keys(windows).find(isOpen) || "";
    }
    refresh();
  }

  document.addEventListener("click", (event) => {
    const opener = event.target.closest("[data-open]");
    if (opener) {
      event.preventDefault();
      open(opener.dataset.open);
      return;
    }
    const task = event.target.closest("[data-task]");
    if (task) {
      const name = task.dataset.task;
      if (isOpen(name) && front === name && !phone.matches) close(name);
      else open(name);
      return;
    }
    const action = event.target.closest("[data-window-action]");
    if (action) {
      const node = action.closest("[data-window]");
      if (!node) return;
      const name = node.dataset.window;
      if (action.dataset.windowAction === "max") node.classList.toggle("is-max");
      else close(name);
      return;
    }
    const win = event.target.closest("[data-window]");
    if (win && !phone.matches && win.dataset.window !== front) open(win.dataset.window, { updateHash: false });
  });

  phone.addEventListener("change", () => {
    if (phone.matches) {
      const name = isOpen(front) ? front : "story";
      open(name, { updateHash: false });
    } else {
      windows.story.hidden = false;
      refresh();
    }
  });

  function start() {
    const wanted = window.location.hash.slice(1);
    if (phone.matches) {
      open(windows[wanted] ? wanted : "story", { updateHash: false });
    } else {
      windows.story.hidden = false;
      open("story", { updateHash: false });
      if (wanted === "calculator") open("calculator", { updateHash: false });
    }
    refresh();
  }

  window.addEventListener("hashchange", () => {
    const wanted = window.location.hash.slice(1);
    if (windows[wanted]) open(wanted, { updateHash: false });
  });

  const clock = document.getElementById("clock");
  function tick() {
    if (!clock) return;
    const now = new Date();
    const hours = now.getHours() % 12 || 12;
    const minutes = String(now.getMinutes()).padStart(2, "0");
    clock.textContent = `${hours}:${minutes} ${now.getHours() >= 12 ? "PM" : "AM"}`;
  }
  tick();
  window.setInterval(tick, 30000);

  start();
})();
