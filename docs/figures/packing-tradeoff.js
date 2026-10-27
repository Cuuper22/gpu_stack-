/* packing-tradeoff: plan a simulated GPU cluster around a higher or lower
   percentile of the power forecast and see what you get. Each dot is one of
   the 21 percentiles: GPU-hours delivered against energy drawn over the power
   cap, averaged over the held-out test episodes. Every number is read from
   data/e003-heatwave-story-v1.json, built from experiments/e003-heatwave/
   results/packing-v1.json. Simulated, not measured. */
(function (root) {
  "use strict";
  var F = root.GPUStackFigures;
  var DATA = "data/e003-heatwave-story-v1.json";

  function ord(q) {
    var p = Math.round(q * 100);
    var s = p % 100 >= 11 && p % 100 <= 13 ? "th" : p % 10 === 1 ? "st" : p % 10 === 2 ? "nd" : p % 10 === 3 ? "rd" : "th";
    return p + s;
  }

  F.define("packing-tradeoff", {
    title: "Planning low or high on the forecast",
    label: "Chart: GPU-hours delivered against energy over the power cap for 21 forecast percentiles in a simulated two-site cluster, with a slider to pick the percentile",
    summary:
      "Simulated, not measured. Each of 21 forecast percentiles, from the 1st to the 99th, is a way to decide how many jobs a two-site cluster admits. " +
      "Planning on a low percentile admits more jobs and draws more energy over the power cap. Planning on a high percentile admits fewer jobs and stays under the cap more often.",
    build: function (ctx) {
      var h = ctx.h, s = ctx.s, u = ctx.util;
      var P = null, idx = 18, manual = null;
      var W = 380, H = 250, L = 52, R = 14, T = 14, B = 40;
      var X0 = 0, X1 = 1, Y0 = 0, Y1 = 1;
      function X(v) { return L + (W - L - R) * (v - X0) / (X1 - X0); }
      function Y(v) { return T + (H - T - B) * (1 - (v - Y0) / (Y1 - Y0)); }

      var svg = s("svg", { class: "pt-svg", viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "Scatter of GPU-hours delivered against energy over the cap, one dot per forecast percentile. The text below the figure gives the numbers." });
      function text(x, y, str, anchor, cls) {
        var t = s("text", { x: x, y: y, "text-anchor": anchor || "start", class: cls || "pt-t" });
        t.textContent = str;
        svg.appendChild(t);
        return t;
      }
      var axes = s("g");
      svg.appendChild(axes);
      function ticks(lo, hi, n) {
        var raw = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), step = mag, out = [];
        [1, 2, 2.5, 5, 10].some(function (m) { step = m * mag; return step >= raw; });
        for (var v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(v);
        return { list: out, step: step };
      }
      function drawAxes(es, gs) {
        var tx = ticks(0, Math.max.apply(null, es) * 1.06, 4), ty = ticks(Math.min.apply(null, gs) * 0.97, Math.max.apply(null, gs) * 1.03, 3);
        X1 = tx.list[tx.list.length - 1] + tx.step / 2;
        Y0 = Math.floor(Math.min.apply(null, gs) * 0.97 / ty.step) * ty.step;
        Y1 = ty.list[ty.list.length - 1] + ty.step / 2;
        tx.list.forEach(function (v) {
          axes.appendChild(s("line", { x1: X(v), x2: X(v), y1: T, y2: H - B, class: "pt-grid" }));
          var t = s("text", { x: X(v), y: H - B + 16, "text-anchor": "middle", class: "pt-t" }); t.textContent = String(v); axes.appendChild(t);
        });
        ty.list.forEach(function (v) {
          axes.appendChild(s("line", { x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: "pt-grid" }));
          var t = s("text", { x: L - 6, y: Y(v) + 4, "text-anchor": "end", class: "pt-t" }); t.textContent = v.toLocaleString("en-US"); axes.appendChild(t);
        });
        var cap = s("text", { x: 4, y: 11, class: "pt-t" }); cap.textContent = "GPU-hours delivered (axis starts at " + Y0.toLocaleString("en-US") + ")"; axes.appendChild(cap);
      }
      text(W - R, H - 6, "energy over the cap (kWh per episode)", "end");
      var line = s("polyline", { class: "pt-line", fill: "none" });
      var dots = s("g");
      var whisk = s("g", { class: "pt-whisk" });
      var react = s("rect", { width: 9, height: 9, class: "pt-react" });
      var reactT = s("text", { class: "pt-t", "text-anchor": "end" });
      reactT.textContent = "react to the meter";
      var mark = s("circle", { r: 6, class: "pt-mark" });
      [line, dots, whisk, react, reactT, mark].forEach(function (n) { svg.appendChild(n); });

      var q = h("input", { type: "range", min: "0", max: "20", step: "1", value: "18", id: "pt-q", "aria-describedby": "pt-read" });
      var qLabel = h("label", { for: "pt-q", class: "pt-label", text: "Forecast percentile to plan around" });
      var read = h("p", { class: "pt-read", id: "pt-read", "aria-live": "polite" });
      var note = h("p", { class: "gsf-note", text: "Simulated two-site cluster. Dots are means over the held-out test episodes; the cross on the gold dot is the 95% interval." });
      var msg = h("p", { class: "gsf-note", text: "Loading the packing results." });
      ctx.el.appendChild(h("div", null, [svg, qLabel, q, read, note, msg]));

      function ready(d) {
        P = d.packing;
        var lv = P.quantile_levels;
        var pts = lv.map(function (v) { return P.policies["timestral-5M/q" + v]; });
        var rr = P.policies.reactive;
        drawAxes(pts.map(function (p) { return p.energy_above_cap_kwh.mean; }).concat([rr.energy_above_cap_kwh.mean]),
          pts.map(function (p) { return p.gpu_hours.mean; }).concat([rr.gpu_hours.mean]));
        line.setAttribute("points", pts.map(function (p) { return X(p.energy_above_cap_kwh.mean).toFixed(1) + "," + Y(p.gpu_hours.mean).toFixed(1); }).join(" "));
        pts.forEach(function (p, i) {
          dots.appendChild(s("circle", { r: 3, cx: X(p.energy_above_cap_kwh.mean).toFixed(1), cy: Y(p.gpu_hours.mean).toFixed(1), class: "pt-dot" }));
        });
        var r = P.policies.reactive;
        react.setAttribute("x", X(r.energy_above_cap_kwh.mean) - 4.5);
        react.setAttribute("y", Y(r.gpu_hours.mean) - 4.5);
        reactT.setAttribute("x", X(r.energy_above_cap_kwh.mean) - 10);
        reactT.setAttribute("y", Y(r.gpu_hours.mean) + 4);
        msg.hidden = true;
        var first = pts[0], last = pts[pts.length - 1];
        ctx.setSummary("Simulated, not measured, " + P.test_seeds.length + " held-out test episodes of " + P.window_hours + " hours. Reacting to measured power delivers " +
          Math.round(r.gpu_hours.mean).toLocaleString("en-US") + " GPU-hours with " + r.energy_above_cap_kwh.mean.toFixed(1) + " kWh over the cap. Planning on the " + ord(lv[0]) +
          " percentile delivers " + Math.round(first.gpu_hours.mean).toLocaleString("en-US") + " GPU-hours with " + first.energy_above_cap_kwh.mean.toFixed(1) + " kWh over the cap. Planning on the " +
          ord(lv[lv.length - 1]) + " percentile delivers " + Math.round(last.gpu_hours.mean).toLocaleString("en-US") + " GPU-hours with " + last.energy_above_cap_kwh.mean.toFixed(1) + " kWh over the cap.");
        paint(idx);
        if (ctx.reduced && ctx.root.__gsf) ctx.root.__gsf.end();
      }
      function paint(i) {
        if (!P) return;
        var lv = P.quantile_levels, p = P.policies["timestral-5M/q" + lv[i]];
        var ex = p.energy_above_cap_kwh, gy = p.gpu_hours;
        mark.setAttribute("cx", X(ex.mean)); mark.setAttribute("cy", Y(gy.mean));
        whisk.replaceChildren(
          s("line", { x1: X(ex.lo), x2: X(ex.hi), y1: Y(gy.mean), y2: Y(gy.mean) }),
          s("line", { x1: X(ex.mean), x2: X(ex.mean), y1: Y(gy.lo), y2: Y(gy.hi) }));
        q.value = String(i);
        q.setAttribute("aria-valuetext", ord(lv[i]) + " percentile");
        read.textContent = "Plan on the " + ord(lv[i]) + " percentile: " + Math.round(gy.mean).toLocaleString("en-US") + " GPU-hours, " + ex.mean.toFixed(1) +
          " kWh over the cap, over the cap in " + Math.round(100 * p.violation_rate.mean) + "% of intervals.";
      }
      q.addEventListener("input", function () {
        manual = Number(q.value);
        if (ctx.root.__gsf) ctx.root.__gsf.timeline.pause();
        paint(manual);
      });
      var started = false;
      function fetchData() {
        if (started) return;
        started = true;
        var src = ctx.root.getAttribute("data-src") || DATA;
        root.fetch(src).then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); }).then(ready)
          .catch(function () { msg.textContent = "The packing results could not be fetched."; });
      }
      ctx.onVisible(function (v) { if (v) fetchData(); });
      if (ctx.reduced) fetchData();

      var D = 8;
      return {
        duration: D,
        still: D,
        onReplay: function () { manual = null; },
        render: function (t) {
          if (manual !== null) return;
          var a = t <= 6 ? 20 - 20 * u.ease(t / 6) : 0 + 18 * u.ease((t - 6) / 2);
          idx = Math.round(u.clamp(a, 0, 20));
          paint(idx);
        },
      };
    },
  });
})(typeof window !== "undefined" ? window : globalThis);
