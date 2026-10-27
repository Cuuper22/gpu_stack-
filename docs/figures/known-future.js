/* known-future: what a forecaster gains from inputs that are known ahead of
   time. One row per series, one marker per input, placed by the change in
   forecast loss against the same Timestral model with no inputs. Lower is
   better. A filled marker means the 95% intervals of the two losses do not
   overlap; a hollow one means they do. Data: data/e003-heatwave-story-v1.json,
   blocks "ablation" (measured and public series) and "ablation_sim" (simulated
   cluster) when that result is in. */
(function (root) {
  "use strict";
  var F = root.GPUStackFigures;
  var DATA = "data/e003-heatwave-story-v1.json";
  var NAME = { DA: "day-ahead price", WX: "weather forecast", DEM: "demand forecast", F: "carbon forecast", S: "job schedule", K: "checkpoint timing",
    J: "job schedule", P: "training-step phase", W: "weather forecast", C: "price and carbon forecast" };
  var KIND = { measured: "measured", public: "public", simulated: "simulated" };

  F.define("known-future", {
    title: "What known inputs add",
    label: "Chart: change in Timestral forecast loss when inputs known ahead of time are added, for each series, with one marker per input",
    summary:
      "Each row is one series. Each marker is one input known ahead of time, such as a job schedule, a weather forecast or a day-ahead price, " +
      "placed by how much it changed forecast loss against the same model with no inputs. Left of the line is better. Hollow markers have overlapping intervals.",
    build: function (ctx) {
      var h = ctx.h, s = ctx.s, u = ctx.util;
      var model = "timestral-209M", D = null, rows = [];
      var seg = h("div", { class: "gsf-seg", role: "group", "aria-label": "Model size" });
      var btns = [["timestral-209M", "Timestral 209M"], ["timestral-28M", "Timestral 28M"]].map(function (m) {
        var b = h("button", { type: "button", "aria-pressed": String(m[0] === model), text: m[1] });
        b.addEventListener("click", function () { model = m[0]; paintButtons(); build(); });
        seg.appendChild(b);
        return b;
      });
      function paintButtons() { btns.forEach(function (b, i) { b.setAttribute("aria-pressed", String(i === (model === "timestral-209M" ? 0 : 1))); }); }
      var legend = h("p", { class: "kf-legend" });
      var list = h("div", { class: "kf-list" });
      var msg = h("p", { class: "gsf-note", text: "Loading the results." });
      ctx.el.appendChild(h("div", null, [seg, list, legend, h("p", { class: "gsf-note", text: "Marker position is the change in loss against no inputs. Filled: the 95% intervals do not overlap. Hollow: they overlap. Combinations of inputs are in the Heatwave window." }), msg]));

      function shape(i, cx, cy, filled) {
        i = i % 6;
        var a = { class: "kf-m" + (filled ? " is-f" : ""), "data-k": String(i) }, r = 5;
        if (i === 0) return s("circle", Object.assign(a, { cx: cx, cy: cy, r: r }));
        if (i === 1) return s("rect", Object.assign(a, { x: cx - r, y: cy - r, width: 2 * r, height: 2 * r }));
        if (i === 2) return s("polygon", Object.assign(a, { points: [cx, cy - 6, cx + 6, cy + 5, cx - 6, cy + 5].join(" ") }));
        if (i === 3) return s("polygon", Object.assign(a, { points: [cx, cy - 6, cx + 6, cy, cx, cy + 6, cx - 6, cy].join(" ") }));
        if (i === 4) return s("polygon", Object.assign(a, { points: [cx - 6, cy - 3, cx + 6, cy - 3, cx, cy + 6].join(" ") }));
        return s("polygon", Object.assign(a, { points: [cx - 2, cy - 6, cx + 2, cy - 6, cx + 2, cy - 2, cx + 6, cy - 2, cx + 6, cy + 2, cx + 2, cy + 2, cx + 2, cy + 6, cx - 2, cy + 6, cx - 2, cy + 2, cx - 6, cy + 2, cx - 6, cy - 2, cx - 2, cy - 2].join(" ") }));
      }

      function build() {
        if (!D) return;
        var blocks = [D.ablation, D.ablation_sim].filter(function (b) { return b && b.status === "ready"; });
        var items = [], kinds = [];
        blocks.forEach(function (b) {
          Object.keys(b.datasets).forEach(function (n) {
            var d = b.datasets[n], cfgs = d.methods[model];
            if (!cfgs) return;
            var pts = Object.keys(cfgs).filter(function (c) { return cfgs[c].groups.length === 1; }).map(function (c) {
              var g = cfgs[c].groups[0], nm = NAME[g] || d.groups[g] || g;
              if (kinds.indexOf(nm) < 0) kinds.push(nm);
              return { name: nm, change: cfgs[c].change_pct, filled: cfgs[c].vs_none === "lower" || cfgs[c].vs_none === "higher" };
            });
            items.push({ what: d.what, kind: KIND[d.data_kind] || "simulated", pts: pts });
          });
        });
        var all = [];
        items.forEach(function (it) { it.pts.forEach(function (p) { all.push(p.change); }); });
        var lo = Math.min(0, Math.min.apply(null, all)), hi = Math.max(0, Math.max.apply(null, all));
        var pad = (hi - lo) * 0.06;
        lo -= pad; hi += pad;
        var W = 300;
        function X(v) { return 6 + (W - 12) * (v - lo) / (hi - lo); }
        list.replaceChildren();
        rows = [];
        items.forEach(function (it, ri) {
          var svg = s("svg", { class: "kf-svg", viewBox: "0 0 " + W + " 30", "aria-hidden": "true" }, [s("line", { x1: X(0), x2: X(0), y1: 0, y2: 30, class: "kf-zero" })]);
          it.pts.forEach(function (p) {
            var m = shape(kinds.indexOf(p.name), X(p.change), 15, p.filled);
            var t = s("title"); t.textContent = p.name + ": " + (p.change > 0 ? "+" : "") + p.change.toFixed(1) + "% loss"; m.appendChild(t);
            svg.appendChild(m);
          });
          var row = h("div", { class: "kf-row" }, [h("div", { class: "kf-what" }, [h("span", { text: it.what }), h("span", { class: "kf-kind", text: it.kind })]), svg]);
          rows.push(row);
          list.appendChild(row);
        });
        var step = [5, 10, 20, 25, 50, 100].filter(function (v) { return v >= (hi - lo) / 5; })[0] || 100;
        var ax = s("svg", { class: "kf-svg kf-ax", viewBox: "0 0 " + W + " 24", "aria-hidden": "true" }, [s("line", { x1: 6, x2: W - 6, y1: 2, y2: 2, class: "kf-axl" })]);
        for (var tv = Math.ceil(lo / step) * step; tv <= hi; tv += step) {
          var tt = s("text", { x: X(tv), y: 19, "text-anchor": "middle", class: "kf-at" });
          tt.textContent = (tv > 0 ? "+" : "") + tv + "%";
          ax.appendChild(s("line", { x1: X(tv), x2: X(tv), y1: 2, y2: 6, class: "kf-axl" }));
          ax.appendChild(tt);
        }
        list.appendChild(h("div", { class: "kf-row kf-axisrow" }, [h("div", { class: "kf-what" }, [h("span", { class: "kf-kind", text: "change in loss" })]), ax]));
        legend.replaceChildren();
        kinds.forEach(function (k, i) {
          var sv = s("svg", { viewBox: "0 0 16 16", class: "kf-key", "aria-hidden": "true" }, [shape(i, 8, 8, true)]);
          legend.appendChild(h("span", null, [sv, k]));
        });
        var parts = [];
        items.forEach(function (it) {
          parts.push(it.what + ": " + it.pts.map(function (p) { return p.name + " " + (p.change > 0 ? "+" : "") + p.change.toFixed(0) + "%"; }).join(", "));
        });
        ctx.setSummary("Change in " + model.replace("timestral-", "Timestral ") + " forecast loss against no inputs, lower is better. " + parts.join(". ") + ".");
        msg.hidden = true;
        if (ctx.reduced && ctx.root.__gsf) ctx.root.__gsf.end();
      }

      var started = false;
      function fetchData() {
        if (started) return;
        started = true;
        root.fetch(ctx.root.getAttribute("data-src") || DATA).then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
          .then(function (d) { D = d; build(); })
          .catch(function () { msg.textContent = "The results could not be fetched."; });
      }
      ctx.onVisible(function (v) { if (v) fetchData(); });
      if (ctx.reduced) fetchData();

      return {
        duration: 1.6,
        autoplay: true,
        render: function (t) {
          var n = rows.length, k = u.clamp(t / 1.2) * n;
          rows.forEach(function (r, i) { r.style.opacity = i < k ? "1" : "0.15"; });
        },
      };
    },
  });
})(typeof window !== "undefined" ? window : globalThis);
