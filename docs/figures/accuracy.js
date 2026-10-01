/* accuracy: 27 published training runs, predicted vs reported GPU-hours (per
   trillion training tokens, so every run is on the same footing), log-log,
   with the diagonal and a +/-22% band. A toggle switches between the full
   calculator and one line of arithmetic. The dots barely move, because the
   two predictions agree. Data: data/published-runs.json, built by
   scripts/build_accuracy_figure_data.py from the cited papers. */
(function (root) {
  "use strict";
  var F = root.GPUStackFigures;
  var BAND = 0.22;

  // [name, reported, rule of thumb at 40% MFU, full calculator, run total GPU-hours]
  // Same numbers as published-runs.json, kept here so the figure also works from a file.
  var FALLBACK = [["LLaMA-7B",82432.0,89476.5,89597.6,82432],["LLaMA-13B",135168.0,173611.1,173846.1,135168],["LLaMA-33B",378880.0,434027.8,434615.2,530432],["LLaMA-65B",730258.6,870726.5,871905.0,1022362],["Llama 2 7B",92160.0,89989.6,90111.4,184320],["Llama 2 13B",184320.0,173823.0,174058.3,368640],["Llama 2 34B",519168.0,454059.8,454674.4,1038336],["Llama 2 70B",860160.0,921162.6,922409.4,1720320],["Llama 3.1 405B",1976923.1,1709864.3,1712178.6,30840000.0],["Pythia 70M",1700.6,940.5,941.8,510],["Pythia 160M",3434.6,2167.8,2170.7,1030],["Pythia 410M",8469.7,5413.1,5420.4,2540],["Pythia 1B",16105.8,13512.0,13530.3,4830],["Pythia 1.4B",23741.8,18892.2,18917.8,7120],["Pythia 2.8B",47483.6,37062.1,37112.2,14240],["Pythia 6.9B",111706.6,91563.2,91687.1,33500],["Pythia 12B",241086.2,158148.2,158362.3,72300],["BLOOM 176B",2958989.1,2353726.0,2356911.7,1082990],["PaLM 540B",10775630.8,8187121.2,8198202.5,8404992],["Gopher 280B",12561066.7,9485094.9,9497932.9,3768320],["MPT-7B",100320.0,89476.5,89597.6,100320.0],["SmolLM3 3B",19748.6,12955.4,12973.0,221184],["BloombergGPT 50B",1144576.4,675747.9,676662.5,651264],["StarCoderBase 15.5B",320256.0,206997.9,207278.0,320256],["MT-NLG 530B, 280 nodes",9510181.6,7077991.5,7087571.5,null],["MT-NLG 530B, 350 nodes",9929515.7,7077991.5,7087571.5,null],["MT-NLG 530B, 420 nodes",10538737.0,7077991.5,7087571.5,null]];

  function fromJson(j) {
    if (!j || !Array.isArray(j.rows)) return null;
    return j.rows.map(function (r) {
      return [
        r.name,
        r.reported_per_trillion_tokens,
        r.predicted_rule_40pct_mfu_per_trillion_tokens,
        r.predicted_graph_per_trillion_tokens,
        r.reported_gpu_hours,
      ];
    });
  }
  function median(a) {
    var b = a.slice().sort(function (x, y) { return x - y; });
    var m = b.length >> 1;
    return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2;
  }
  function short(n) {
    if (n >= 1e6) return n / 1e6 + "M";
    if (n >= 1e3) return n / 1e3 + "K";
    return String(n);
  }

  F.define("accuracy", {
    title: "Predicted vs reported GPU-hours",
    label: "Scatter plot: 27 published training runs, predicted against reported GPU-hours on log axes, with a band of plus or minus 22 percent",
    summary:
      "Twenty-seven published training runs, with the GPU-hours each paper reports on the horizontal axis and the prediction on the vertical axis, both on log scales. " +
      "The full calculator and the one-line rule, 6 times size times tokens divided by 40 percent of the GPU's top speed, land in almost the same place: a median error of about 22 percent for both.",
    build: function (ctx) {
      var h = ctx.h, s = ctx.s, u = ctx.util;
      var data = FALLBACK, mode = "graph";
      var svg = s("svg", { class: "ac-svg", role: "group", "aria-label": "Scatter plot of 27 runs. Each point is a button with details." });
      var tip = h("div", { class: "ac-tip", role: "tooltip" });
      var wrap = h("div", { class: "ac-wrap" }, [svg, tip]);
      var seg = h("div", { class: "gsf-seg", role: "group", "aria-label": "Prediction method" });
      var bGraph = h("button", { type: "button", "aria-pressed": "true", text: "My big graph" });
      var bRule = h("button", { type: "button", "aria-pressed": "false", text: "One line of arithmetic" });
      seg.appendChild(bGraph);
      seg.appendChild(bRule);
      var errOut = h("b");
      var readTxt = h("span", { class: "gsf-note", style: "margin:0" });
      var read = h("div", { class: "ac-read", "aria-live": "polite" }, [errOut, readTxt]);
      var legend = h("p", { class: "gsf-note" });
      var note = h("p", { class: "gsf-note" });
      ctx.el.appendChild(h("div", null, [seg, wrap, read, legend, note]));

      var pts = [], lay = null, intro = 1, pinned = -1;

      function predicted(r) { return mode === "graph" ? r[3] : r[2]; }
      function stats() {
        var errs = data.map(function (r) { return Math.abs(predicted(r) / r[1] - 1); });
        var inside = errs.filter(function (e) { return e <= BAND; }).length;
        return { med: median(errs), inside: inside };
      }
      function agree() {
        return Math.max.apply(null, data.map(function (r) { return Math.abs(r[3] / r[2] - 1); }));
      }
      function describe() {
        var st = stats();
        errOut.textContent = (st.med * 100).toFixed(1) + "%";
        readTxt.textContent =
          (mode === "graph"
            ? "median error, full calculator. "
            : "median error, 6 x size x tokens / (0.4 x GPU peak speed). ") +
          st.inside + " of " + data.length + " land inside the band.";
        note.textContent = "Both axes are GPU-hours per trillion training tokens, so a small model and a huge one share one chart. Some runs are TPU-hours. Switch methods: the dots barely move, because the two predictions agree to within " + (agree() * 100).toFixed(1) + " percent.";
        ctx.setSummary("Median error " + (st.med * 100).toFixed(1) + " percent across " + data.length + " published runs using " + (mode === "graph" ? "the full calculator" : "one line of arithmetic") + ". " + st.inside + " runs fall inside the plus or minus 22 percent band.");
      }
      function layout() {
        var W = Math.max(280, Math.min(ctx.el.clientWidth - 28, 560));
        var L = 52, R = 12, T = 10, B = 44;
        var P = Math.min(W - L - R, 440);
        return { W: W, H: P + T + B, L: L, R: R, T: T, B: B, P: P, lo: 3, hi: 7.3 };
      }
      function X(v) { return lay.L + ((Math.log10(v) - lay.lo) / (lay.hi - lay.lo)) * lay.P; }
      function Y(v) { return lay.T + lay.P - ((Math.log10(v) - lay.lo) / (lay.hi - lay.lo)) * lay.P; }
      function draw() {
        lay = layout();
        svg.setAttribute("viewBox", "0 0 " + lay.W + " " + lay.H);
        svg.setAttribute("width", lay.W);
        svg.setAttribute("height", lay.H);
        svg.style.margin = "0 auto";
        svg.style.maxWidth = lay.W + "px";
        svg.textContent = "";
        var ticks = [3, 4, 5, 6, 7];
        ticks.forEach(function (e) {
          var v = Math.pow(10, e);
          svg.appendChild(s("line", { class: "ac-grid", x1: lay.L, x2: lay.L + lay.P, y1: Y(v), y2: Y(v) }));
          svg.appendChild(s("line", { class: "ac-grid", y1: lay.T, y2: lay.T + lay.P, x1: X(v), x2: X(v) }));
          svg.appendChild(s("text", { x: lay.L - 6, y: Y(v) + 4, "text-anchor": "end", text: short(v) }));
          svg.appendChild(s("text", { x: X(v), y: lay.T + lay.P + 16, "text-anchor": "middle", text: short(v) }));
        });
        var lo = Math.pow(10, lay.lo), hi = Math.pow(10, lay.hi);
        // band between y = 0.78 x and y = 1.22 x, clipped to the plot
        var clipId = "acc" + Math.random().toString(36).slice(2, 6);
        svg.appendChild(s("clipPath", { id: clipId }, [s("rect", { x: lay.L, y: lay.T, width: lay.P, height: lay.P })]));
        var g = s("g", { "clip-path": "url(#" + clipId + ")" });
        g.appendChild(s("polygon", { class: "ac-band", points: [[lo, lo * (1 - BAND)], [hi, hi * (1 - BAND)], [hi, hi * (1 + BAND)], [lo, lo * (1 + BAND)]].map(function (p) { return X(p[0]) + "," + Y(p[1]); }).join(" ") }));
        g.appendChild(s("line", { class: "ac-diag", x1: X(lo), y1: Y(lo), x2: X(hi), y2: Y(hi) }));
        svg.appendChild(g);
        svg.appendChild(s("rect", { x: lay.L, y: lay.T, width: lay.P, height: lay.P, fill: "none", stroke: "var(--f-ink)", "stroke-width": 1.5 }));
        svg.appendChild(s("text", { class: "ac-axis-title", x: lay.W / 2, y: lay.H - 6, "text-anchor": "middle", style: "font-size:12px", text: "Reported GPU-hours / trillion tokens" }));
        svg.appendChild(s("text", { class: "ac-axis-title", transform: "translate(13 " + (lay.T + lay.P / 2) + ") rotate(-90)", "text-anchor": "middle", text: "Predicted" }));
        pts = data.map(function (r, i) {
          var c = s("circle", {
            class: "ac-pt",
            tabindex: 0,
            role: "img",
            "aria-label": r[0] + ": reported " + u.fmt(r[1]) + ", predicted " + u.fmt(predicted(r)) + " GPU-hours per trillion tokens",
            cx: X(r[1]),
            cy: Y(predicted(r)),
            r: 6,
          });
          c.addEventListener("mouseenter", function () { showTip(i); });
          c.addEventListener("focus", function () { showTip(i); });
          c.addEventListener("click", function () { showTip(i); });
          c.addEventListener("mouseleave", hideTip);
          c.addEventListener("blur", hideTip);
          svg.appendChild(c);
          return c;
        });
        mark();
        paintIntro();
      }
      function mark() {
        data.forEach(function (r, i) {
          var out = Math.abs(predicted(r) / r[1] - 1) > BAND;
          pts[i].setAttribute("class", "ac-pt" + (out ? " is-miss" : ""));
        });
        legend.innerHTML = '<span class="gsf-tag" style="border-color:var(--f-blue)">inside the band</span> <span class="gsf-tag" style="border-color:var(--f-red)">outside the band</span> <span class="gsf-tag">dashed line: prediction equals report</span> <span class="gsf-tag">shaded: plus or minus 22%</span>';
      }
      function showTip(i) {
        var r = data[i], p = predicted(r);
        var d = (p / r[1] - 1) * 100;
        tip.innerHTML = "";
        tip.appendChild(h("b", { text: r[0] }));
        tip.appendChild(h("span", { text: "reported " + u.fmt(r[1]) + "\npredicted " + u.fmt(p) + " (" + (d >= 0 ? "+" : "") + Math.round(d) + "%)" , style: "white-space:pre-line;display:block" }));
        if (r[4]) tip.appendChild(h("span", { text: "run total: " + u.fmt(r[4]) + " GPU-hours", style: "display:block;opacity:.8" }));
        var cx = X(r[1]), cy = Y(p);
        tip.classList.add("is-on");
        var tw = tip.offsetWidth, th = tip.offsetHeight;
        var left = Math.min(Math.max(4, cx - tw / 2 + (svg.getBoundingClientRect().left - wrap.getBoundingClientRect().left)), wrap.clientWidth - tw - 4);
        var top = cy - th - 12;
        if (top < 0) top = cy + 14;
        tip.style.left = left + "px";
        tip.style.top = top + "px";
      }
      function hideTip() { tip.classList.remove("is-on"); }
      function paintIntro() {
        pts.forEach(function (c, i) {
          var p = u.ease((intro * 1.5 - i / data.length * 0.5) / 1);
          c.style.opacity = String(u.clamp(p));
          c.setAttribute("r", String(6 * u.clamp(p) + (1 - u.clamp(p)) * 2));
        });
      }
      function setMode(m) {
        mode = m;
        bGraph.setAttribute("aria-pressed", m === "graph" ? "true" : "false");
        bRule.setAttribute("aria-pressed", m === "rule" ? "true" : "false");
        data.forEach(function (r, i) {
          pts[i].setAttribute("cy", Y(predicted(r)));
          pts[i].setAttribute("cx", X(r[1]));
        });
        mark();
        describe();
      }
      bGraph.addEventListener("click", function () { setMode("graph"); });
      bRule.addEventListener("click", function () { setMode("rule"); });
      ctx.fig.addEventListener("keydown", function (e) { if (e.key === "Escape") hideTip(); });

      draw();
      describe();
      ctx.onResize(function () { var c = ctx.el.clientWidth; if (lay && Math.abs(Math.min(c - 28, 560) - lay.W) > 2) { draw(); } });

      var src = ctx.root.getAttribute("data-src") || "data/published-runs.json";
      if (root.fetch) {
        root.fetch(src).then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); }).then(function (j) {
          var rows = fromJson(j);
          if (rows && rows.length === 27) {
            data = rows;
            draw();
            describe();
          }
        }).catch(function () {
          if (root.console) root.console.info("accuracy: " + src + " not available, using the built-in copy of the same 27 rows");
        });
      }

      return {
        duration: 3,
        render: function (t) {
          intro = t / 3;
          paintIntro();
        },
      };
    },
  });
})(typeof window !== "undefined" ? window : globalThis);
