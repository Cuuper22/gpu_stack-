/* hook-gpu-hours (also reachable as why-so-many-gpus): why a big training run
   needs many GPUs working at once. 30.84 million GPU-hours on one GPU is about
   3,500 years. Spread over 16,384 GPUs it is about 11 weeks. */
(function (root) {
  "use strict";
  var F = root.GPUStackFigures;
  var HOURS = 30.84e6; // Llama 3.1 model card, H100 GPU-hours
  var HOURS_PER_YEAR = 8766;
  var COLS = 128; // 128 x 128 = 16,384 cells
  var CELLS = COLS * COLS;
  var COUNTS = [1, 128, 2048, 16384];

  function span(n) {
    var hours = HOURS / n;
    var years = hours / HOURS_PER_YEAR;
    if (years >= 2) {
      var y = years >= 100 ? Math.round(years / 100) * 100 : Math.round(years);
      return "about " + F.util.fmt(y) + " years";
    }
    var days = hours / 24;
    if (days >= 120) return "about " + Math.round(days / 30.4) + " months";
    if (days >= 14) return "about " + Math.round(days / 7) + " weeks";
    return "about " + Math.round(days) + " days";
  }

  F.define("hook-gpu-hours", {
    title: "Why so many GPUs",
    label: "Animation: the same work takes about 3,500 years on one GPU and about 11 weeks on 16,384 GPUs",
    summary:
      "Llama 3.1 405B used 30.84 million GPU-hours. On a single GPU that is about 3,500 years. " +
      "Spread across 16,384 GPUs working together, the same work takes about 11 weeks. " +
      "Buttons let you try 1, 128, 2,048 or 16,384 GPUs.",
    build: function (ctx) {
      var h = ctx.h, s = ctx.s, u = ctx.util;
      var order = new Array(CELLS), wave = new Array(CELLS), rank = new Array(CELLS);
      var rand = u.rng(7);
      for (var i = 0; i < CELLS; i++) {
        var x = i % COLS, y = (i / COLS) | 0;
        wave[i] = (x + y) / (2 * COLS) * 0.82 + rand() * 0.18;
        order[i] = i;
      }
      var rand2 = u.rng(11);
      var perm = order.slice();
      for (i = CELLS - 1; i > 0; i--) {
        var j = Math.floor(rand2() * (i + 1));
        var tmp = perm[i];
        perm[i] = perm[j];
        perm[j] = tmp;
      }
      for (i = 0; i < CELLS; i++) rank[perm[i]] = i;

      var chip = s("svg", { class: "hk-chip", viewBox: "0 0 120 120", "aria-hidden": "true" }, [
        s("rect", { x: 26, y: 26, width: 68, height: 68, fill: "currentColor", opacity: 0.12, stroke: "currentColor", "stroke-width": 3 }),
        s("rect", { x: 40, y: 40, width: 40, height: 40, fill: "currentColor" }),
      ]);
      for (i = 0; i < 6; i++) {
        var p = 34 + i * 10.4;
        [[p, 14, p, 26], [p, 94, p, 106], [14, p, 26, p], [94, p, 106, p]].forEach(function (l) {
          chip.appendChild(s("line", { x1: l[0], y1: l[1], x2: l[2], y2: l[3], stroke: "currentColor", "stroke-width": 3 }));
        });
      }
      var canvas = h("canvas", { class: "hk-grid", role: "img", "aria-label": "A grid of 16,384 GPUs lighting up" });
      var countLabel = h("p", { class: "hk-label", text: "16,384 GPUs" });
      var hand = s("line", { x1: 11, y1: 11, x2: 11, y2: 4.5, stroke: "currentColor", "stroke-width": 2, "stroke-linecap": "round" });
      var hand2 = s("line", { x1: 11, y1: 11, x2: 11, y2: 7, stroke: "currentColor", "stroke-width": 2, "stroke-linecap": "round" });
      var clock = s("svg", { class: "hk-clock", viewBox: "0 0 22 22", "aria-hidden": "true" }, [
        s("circle", { cx: 11, cy: 11, r: 9.5, fill: "none", stroke: "currentColor", "stroke-width": 2 }),
        hand,
        hand2,
      ]);
      var fill = h("div", { class: "hk-fill" });
      var v1 = h("span", { text: "about 3,500 years" });
      var v2 = h("span", { text: span(16384) });
      var out = h("p", { class: "hk-value", "aria-live": "polite" }, [v1, v2]);
      var timeLabel = h("p", { class: "hk-time-head" }, [clock, h("span", { text: "Time to finish the same work" })]);
      var seg = h("div", { class: "gsf-seg", role: "group", "aria-label": "Number of GPUs" });
      var btns = COUNTS.map(function (n) {
        var b = h("button", { type: "button", "aria-pressed": n === 16384 ? "true" : "false", text: F.util.fmt(n) + (n === 1 ? " GPU" : " GPUs") });
        b.addEventListener("click", function () { choose(n); });
        seg.appendChild(b);
        return b;
      });
      ctx.el.appendChild(
        h("div", null, [
          h("div", { class: "hk-pair" }, [
            h("div", { class: "hk-col" }, [h("p", { class: "hk-label", text: "One GPU" }), chip]),
            h("div", { class: "hk-col" }, [countLabel, canvas]),
          ]),
          h("div", { class: "hk-time" }, [
            timeLabel,
            h("div", { class: "hk-track" }, [fill]),
            h("div", { class: "hk-axis" }, [h("span", { text: "0" }), h("span", { text: "3,500 years (linear scale)" })]),
            out,
          ]),
          seg,
          h("p", { class: "gsf-note", html: "Assumes every GPU works nonstop on one shared job. Total work: 30.84 million GPU-hours, from the Llama 3.1 model card. Up to 16,384 H100 GPUs, from the Llama 3 paper." }),
        ])
      );

      var g = canvas.getContext ? canvas.getContext("2d") : null;
      var size = 0;
      var cOff, cOn, cFront;
      function colors() {
        cOff = "#363b47";
        cOn = "#4fd0da";
        cFront = "#f3cf55";
      }
      function resize() {
        var r = canvas.getBoundingClientRect();
        var d = root.devicePixelRatio || 1;
        var w = Math.max(64, Math.round(r.width * d));
        if (w !== canvas.width) {
          canvas.width = w;
          canvas.height = w;
        }
        size = w;
        colors();
        draw();
      }
      var state = { n: 16384, waveP: 1 };
      var picked = false;
      function draw() {
        if (!g || !size) return;
        var cell = size / COLS;
        g.clearRect(0, 0, size, size);
        var n = state.n, wp = state.waveP;
        g.fillStyle = "#1b1e25";
        g.fillRect(0, 0, size, size);
        g.fillStyle = cOff;
        var pad0 = Math.max(0.2, cell * 0.08);
        for (var q = 0; q < CELLS; q++) g.fillRect((q % COLS) * cell + pad0, ((q / COLS) | 0) * cell + pad0, cell - pad0 * 2, cell - pad0 * 2);
        // gaps: draw cells on a faint background
        var pad = Math.max(0.2, cell * 0.08);
        for (var k = 0; k < CELLS; k++) {
          var on, front = false;
          if (n === 16384) {
            on = wave[k] < wp;
            front = on && wave[k] > wp - 0.06 && wp < 1;
          } else on = rank[k] < n;
          if (!on) continue;
          g.fillStyle = front ? cFront : cOn;
          var grow = n === 1 ? 7 : n <= 128 ? 3.5 : n <= 2048 ? 1.5 : 1;
          var cx = (k % COLS) * cell + cell / 2, cy = ((k / COLS) | 0) * cell + cell / 2;
          var half = (cell * grow) / 2 - pad;
          g.fillRect(cx - half, cy - half, half * 2, half * 2);
        }
      }
      function setBar(frac) {
        fill.style.transform = "scaleX(" + Math.max(frac, 0.004) + ")";
      }
      function setClock(frac) {
        var a = frac * 360 * 8;
        hand.setAttribute("transform", "rotate(" + a + " 11 11)");
        hand2.setAttribute("transform", "rotate(" + a / 12 + " 11 11)");
      }
      function showValue(which) {
        v1.className = which === 1 ? "is-on" : "";
        v2.className = which === 2 ? "is-on" : "";
      }
      function choose(n) {
        picked = true;
        state.n = n;
        state.waveP = 1;
        btns.forEach(function (b, i) { b.setAttribute("aria-pressed", COUNTS[i] === n ? "true" : "false"); });
        var frac = 1 / n;
        setBar(frac);
        setClock(frac);
        v2.textContent = span(n);
        showValue(2);
        countLabel.textContent = F.util.fmt(n) + (n === 1 ? " GPU" : " GPUs");
        chipBusy(n === 1);
        draw();
        ctx.setSummary("Llama 3.1 405B needed 30.84 million GPU-hours. With " + F.util.fmt(n) + " GPUs working together that is " + span(n) + ".");
      }
      function chipBusy(on) {
        chip.setAttribute("class", "hk-chip" + (on ? " is-busy" : ""));
      }
      ctx.onResize(resize);
      resize();

      return {
        duration: 10.5,
        onReplay: function () {
          picked = false;
          btns.forEach(function (b, i) { b.setAttribute("aria-pressed", COUNTS[i] === 16384 ? "true" : "false"); });
          countLabel.textContent = "16,384 GPUs";
          v2.textContent = span(16384);
        },
        render: function (t) {
          if (picked) return;
          var p1 = u.ease(t / 3.4);
          var p2 = u.ease((t - 4) / 2.6);
          var p3 = u.ease((t - 7) / 1.6);
          state.n = 16384;
          state.waveP = p2 * 1.1;
          var frac = p3 > 0 ? u.lerp(1, 1 / 16384, p3) : p1;
          setBar(frac);
          setClock(frac);
          showValue(p3 > 0.5 ? 2 : p1 > 0.9 ? 1 : 0);
          chipBusy(t > 0.3 && t < 4);
          countLabel.style.opacity = t > 3.9 ? 1 : 0.35;
          if (t >= 10.4) btns.forEach(function (b, i) { b.setAttribute("aria-pressed", COUNTS[i] === 16384 ? "true" : "false"); });
          draw();
        },
      };
    },
  });
})(typeof window !== "undefined" ? window : globalThis);
