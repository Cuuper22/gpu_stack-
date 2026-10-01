/* flaky-sites: two datacenters train the same tiny model while outages hit.
   Three ways to cope, switched by tabs. A second panel shows why a running
   average of a noisy curve looks like an improvement. Everything here is a
   schematic with made-up numbers, and says so. */
(function (root) {
  "use strict";
  var F = root.GPUStackFigures;
  var N = 40; // steps in the schematic run
  var TICKS_PER_S = 3;
  var OUT = { A: [30, 34], B: [12, 22] };

  var MODES = [
    { id: "lock", tab: "Stay in lockstep", desc: "Both sites wait for each other, so an outage stalls everyone." },
    { id: "avg", tab: "Each trains alone, average every 8 steps", desc: "Each site trains by itself. Every 8 steps the two models are averaged." },
    { id: "alive", tab: "Keep the survivor going", desc: "The site that is still up keeps training. The other one copies it when it returns." },
  ];

  function isDown(site, k) {
    return k >= OUT[site][0] && k < OUT[site][1];
  }

  function simulate(mode, u) {
    var rand = u.rng(mode === "lock" ? 3 : mode === "avg" ? 4 : 5);
    var sa = 0, sb = 0, g = 0, da = 0, db = 0, solo = 0;
    var rows = [{ sa: 0, sb: 0, da: 0, db: 0, stA: "run", stB: "run", link: "", loss: 2 }];
    for (var k = 0; k < N; k++) {
      var dA = isDown("A", k), dB = isDown("B", k);
      var stA = dA ? "down" : "run", stB = dB ? "down" : "run", link = "";
      if (mode === "lock") {
        if (!dA && !dB) {
          g++;
          sa = sb = g;
          link = "sync";
        } else {
          if (!dA) stA = "wait";
          if (!dB) stB = "wait";
        }
      } else if (mode === "avg") {
        if (!dA) { sa++; da += 0.15; }
        if (!dB) { sb++; db += 0.15; }
        if (k % 8 === 7 && !dA && !dB) {
          var m = (sa + sb) / 2;
          sa = sb = m;
          da = db = 0;
          link = "average";
        }
      } else {
        if (k === OUT.B[1]) { sb = sa; db = 0; link = "copy"; }
        if (k === OUT.A[1]) { sa = sb; da = 0; link = "copy"; }
        if (!dA) sa++;
        if (!dB) sb++;
        if (dA || dB) solo++;
        if (dB) db += 0.12;
        if (dA) da += 0.12;
      }
      var p = mode === "lock" ? g : mode === "avg" ? (sa + sb) / 2 : Math.max(sa, sb);
      var wobble = mode === "lock" ? 0.012 : mode === "avg" ? 0.03 : 0.035;
      var loss = 0.25 + 1.75 * Math.exp(-p / 14) + (rand() - 0.5) * 2 * wobble + (mode === "alive" ? 0.022 * (solo / N) * 10 : 0);
      rows.push({ sa: sa, sb: sb, da: Math.min(1, da), db: Math.min(1, db), stA: stA, stB: stB, link: link, loss: loss });
    }
    return rows;
  }

  F.define("flaky-sites", {
    title: "Flaky datacenters, three ways to cope",
    label: "Animation: two datacenters train the same model while outages hit, under three strategies, plus a noisy curve with a running average",
    summary:
      "A schematic, not data. Two sites train the same small model and each goes down for a while. " +
      "Staying in lockstep stalls both sites during an outage. Training alone and averaging every 8 steps keeps both moving. " +
      "Keeping the survivor going lets the working site continue and the other copies it on return. " +
      "A second panel shows a noisy loss curve with a running average that is smoother and so looks better.",
    build: function (ctx) {
      var h = ctx.h, s = ctx.s, u = ctx.util;
      var sims = {};
      MODES.forEach(function (m) { sims[m.id] = simulate(m.id, u); });
      var mode = "lock";

      var tabs = h("div", { class: "gsf-seg fk-tabs fk-seg-col", role: "tablist", "aria-label": "How the sites cope with outages" });
      var tabBtns = MODES.map(function (m, i) {
        var b = h("button", { type: "button", role: "tab", id: "fk-t-" + m.id, "aria-selected": i === 0 ? "true" : "false", tabindex: i === 0 ? "0" : "-1", text: m.tab });
        b.addEventListener("click", function () { setMode(m.id, true); });
        b.addEventListener("keydown", function (e) {
          var d = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
          if (!d) return;
          e.preventDefault();
          var n = (i + d + MODES.length) % MODES.length;
          tabBtns[n].focus();
          setMode(MODES[n].id, true);
        });
        tabs.appendChild(b);
        return b;
      });
      var desc = h("p", { class: "fk-desc", role: "tabpanel", "aria-live": "polite" });

      function site(name) {
        var lamp = h("i", { class: "fk-lamp" });
        var state = h("span", { class: "fk-state" });
        var bar = h("i", { style: "width:0" });
        var num = h("p", { class: "fk-num" });
        var wv = [];
        var w = h("div", { class: "fk-w", "aria-hidden": "true" });
        for (var i = 0; i < 6; i++) { var c = h("i"); wv.push(c); w.appendChild(c); }
        var box = h("div", { class: "fk-site" }, [
          h("p", { class: "fk-site-head" }, [lamp, h("span", { text: name }), state]),
          h("div", { class: "fk-steps" }, [bar]),
          num,
          h("p", { class: "fk-num", style: "margin:0 0 3px", text: "weights" }),
          w,
        ]);
        return { box: box, lamp: lamp, state: state, bar: bar, num: num, wv: wv };
      }
      var A = site("Site A"), B = site("Site B");
      var linkLabel = h("span", { text: "" });
      var link = h("div", { class: "fk-link", "aria-hidden": "true" }, [linkLabel]);
      var sites = h("div", { class: "fk-sites" }, [A.box, link, B.box]);

      var lossPath = s("path", { stroke: "var(--f-blue)", "stroke-width": 2.2 });
      var idealPath = s("path", { stroke: "var(--f-soft)", "stroke-width": 1.4, "stroke-dasharray": "4 3" });
      var bandA = s("rect", { y: 0, height: 60, fill: "var(--f-red)", opacity: 0.16 });
      var bandB = s("rect", { y: 0, height: 60, fill: "var(--f-red)", opacity: 0.16 });
      function X(k) { return (k / N) * 200; }
      bandA.setAttribute("x", X(OUT.A[0])); bandA.setAttribute("width", X(OUT.A[1]) - X(OUT.A[0]));
      bandB.setAttribute("x", X(OUT.B[0])); bandB.setAttribute("width", X(OUT.B[1]) - X(OUT.B[0]));
      function LY(v) { return 56 - ((v - 0.2) / 2) * 50; }
      var ideal = "";
      for (var k = 0; k <= N; k++) ideal += (k ? "L" : "M") + X(k).toFixed(1) + " " + LY(0.25 + 1.75 * Math.exp(-k / 14)).toFixed(1);
      idealPath.setAttribute("d", ideal);
      var lossSvg = s("svg", { class: "fk-svg", viewBox: "0 0 200 60", preserveAspectRatio: "none", role: "img", "aria-label": "Loss over training steps, schematic" }, [bandA, bandB, idealPath, lossPath]);
      var loss = h("div", { class: "fk-loss" }, [
        h("div", { class: "fk-loss-head" }, [h("span", { text: "Model error over time (lower is better)" }), h("span", { text: "schematic, not data" })]),
        lossSvg,
        h("p", { class: "fk-legend" }, [
          h("span", null, [h("i", { style: "border-color:var(--f-blue)" }), "this strategy"]),
          h("span", null, [h("i", { style: "border-color:var(--f-soft);border-top-style:dashed" }), "no outages"]),
          h("span", null, [h("i", { style: "border-color:var(--f-red);opacity:.4" }), "an outage"]),
        ]),
      ]);

      // second panel
      var n2 = 60, W2 = 8;
      var r2 = u.rng(21), noisy = [], smooth = [], nz = 0;
      for (var i = 0; i < n2; i++) {
        nz = nz * 0.35 + (r2() - 0.5) * 0.7;
        noisy.push(0.3 + 1.7 * Math.exp(-i / 16) + nz * (0.35 + 0.65 * Math.exp(-i / 30)));
      }
      for (i = 0; i < n2; i++) {
        var a = Math.max(0, i - W2 + 1), sum = 0;
        for (var j = a; j <= i; j++) sum += noisy[j];
        smooth.push(sum / (i - a + 1));
      }
      function px(i) { return (i / (n2 - 1)) * 200; }
      function py(v) { return 64 - ((v - 0.1) / 2.3) * 58; }
      var noisyD = noisy.map(function (v, i) { return (i ? "L" : "M") + px(i).toFixed(1) + " " + py(v).toFixed(1); }).join("");
      var noisyPath = s("path", { d: noisyD, stroke: "var(--f-soft)", "stroke-width": 1.4, opacity: 0.8 });
      var smoothPath = s("path", { stroke: "var(--f-green)", "stroke-width": 3 });
      var win = s("rect", { y: 0, height: 70, fill: "var(--f-gold)", opacity: 0.3 });
      var svg2 = s("svg", { class: "fk-svg", style: "height:110px", viewBox: "0 0 200 70", preserveAspectRatio: "none", role: "img", "aria-label": "A noisy loss curve and its running average" }, [win, smoothPath, noisyPath]);
      var panel2 = h("div", { class: "fk-panel2" }, [
        h("p", { class: "dr-q", style: "margin:0 0 6px;font:700 16px/1.35 var(--f-sans)", text: "Why averaging looked like a discovery" }),
        svg2,
        h("p", { class: "fk-legend" }, [
          h("span", null, [h("i", { style: "border-color:var(--f-soft)" }), "noisy training curve"]),
          h("span", null, [h("i", { style: "border-color:var(--f-green)" }), "running average of the last 8 points"]),
        ]),
        h("p", { class: "gsf-note", text: "Judged by the average, the same run looks steadier and a little better, even though training itself did not change. Schematic, not data." }),
      ]);

      ctx.el.appendChild(h("div", null, [tabs, desc, sites, loss, panel2]));

      var cur = null;
      function setMode(id, user) {
        mode = id;
        MODES.forEach(function (m, i) {
          tabBtns[i].setAttribute("aria-selected", m.id === id ? "true" : "false");
          tabBtns[i].setAttribute("tabindex", m.id === id ? "0" : "-1");
          if (m.id === id) {
            desc.textContent = m.desc;
            desc.setAttribute("aria-labelledby", "fk-t-" + m.id);
          }
        });
        if (user && ctx.root.__gsf) {
          var tl = ctx.root.__gsf.timeline;
          tl.seek(0);
          if (!ctx.reduced) tl.play();
          else tl.end();
        }
      }
      setMode("lock", false);

      var swWeights = [0.3, 0.9, 0.5, 0.15, 0.75, 0.6];
      function paintSite(S, steps, d, st, name) {
        S.bar.style.width = (steps / N) * 100 + "%";
        S.num.textContent = "step " + Math.floor(steps);
        S.lamp.className = "fk-lamp" + (st === "down" ? " is-down" : st === "wait" ? " is-wait" : "");
        S.box.className = "fk-site" + (st === "down" ? " is-down" : "");
        S.state.textContent = st === "down" ? "down" : st === "wait" ? "waiting" : "training";
        S.wv.forEach(function (c, i) {
          c.style.background = "color-mix(in oklab, var(--f-cyan) " + Math.round((1 - Math.min(1, d * swWeights[i] * 1.6)) * 100) + "%, var(--f-gold))";
        });
      }
      function paintLoss(rows, kk) {
        var d = "";
        for (var i = 1; i <= kk; i++) d += (i === 1 ? "M" : "L") + X(i).toFixed(1) + " " + LY(rows[i].loss).toFixed(1);
        lossPath.setAttribute("d", d);
      }

      return {
        duration: 15,
        loop: true,
        still: 14,
        onReplay: function () { cur = null; },
        render: function (t) {
          var rows = sims[mode];
          var pos = Math.min(N, t * TICKS_PER_S);
          var kk = Math.min(N, Math.floor(pos));
          var fr = pos - kk;
          var a = rows[kk], b = rows[Math.min(N, kk + 1)];
          var stepsA = u.lerp(a.sa, b.sa, kk >= N ? 0 : fr * (b.sa - a.sa > 0 && b.sa - a.sa < 2 ? 1 : 0));
          var stepsB = u.lerp(a.sb, b.sb, kk >= N ? 0 : fr * (b.sb - a.sb > 0 && b.sb - a.sb < 2 ? 1 : 0));
          var info = rows[Math.min(N, kk + 1)];
          paintSite(A, kk >= N ? a.sa : stepsA, info.da, kk >= N ? a.stA : info.stA);
          paintSite(B, kk >= N ? a.sb : stepsB, info.db, kk >= N ? a.stB : info.stB);
          var lk = kk >= N ? "" : info.link;
          link.className = "fk-link" + (lk ? " is-on" : "");
          linkLabel.textContent = lk;
          paintLoss(rows, Math.min(N, kk + (kk >= N ? 0 : 1)));
          // panel 2
          var c = ((t % 7) / 7) * (n2 - 1);
          var ci = Math.floor(c);
          var d2 = "";
          for (var i = 0; i <= ci; i++) d2 += (i ? "L" : "M") + px(i).toFixed(1) + " " + py(smooth[i]).toFixed(1);
          smoothPath.setAttribute("d", d2);
          win.setAttribute("x", px(Math.max(0, c - W2 + 1)));
          win.setAttribute("width", Math.max(2, px(Math.min(c, W2 - 1) + 0)) || 2);
        },
      };
    },
  });
})(typeof window !== "undefined" ? window : globalThis);
