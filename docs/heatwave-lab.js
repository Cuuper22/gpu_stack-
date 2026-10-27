/* heatwave.exe: the Heatwave window. Reads data/e003-heatwave-lab-v1.json (made by
   scripts/build_heatwave_lab_data.py from committed result files). Nothing here
   computes a result; every number shown is read from the data file, and a result
   that is not in yet says so. Four tabs: pack jobs under a cap (replay of one
   simulated episode), outages, cheaper and cleaner hours, known inputs. */
(function (root) {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var DATA_URL = "data/e003-heatwave-lab-v1.json";
  var uid = 0;

  function h(tag, attrs, kids) {
    var n = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") n.textContent = attrs[k];
      else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c) n.append(c); });
    return n;
  }
  function s(tag, attrs, kids) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs || {}) if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]);
    (kids || []).forEach(function (c) { if (c) n.append(c); });
    return n;
  }
  function on(n, type, fn) { n.addEventListener(type, fn); return n; }
  function txt(parent, x, y, cls, str, anchor) {
    var t = s("text", { x: x, y: y, class: cls || "hwl-axis", "text-anchor": anchor || "start" });
    t.textContent = str;
    parent.append(t);
    return t;
  }
  function fmt(x, d) {
    if (x === null || x === undefined || isNaN(x)) return "n/a";
    return Number(x).toLocaleString("en-US", { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 });
  }
  function pct(x, d) { return x === null || x === undefined ? "n/a" : fmt(100 * x, d || 0) + "%"; }
  function ci(m, d) { return m ? fmt(m.mean, d) + " [" + fmt(m.lo, d) + ", " + fmt(m.hi, d) + "]" : "n/a"; }
  function pending(text) { return h("p", { class: "hwl-pending", text: text || "Result pending." }); }
  function scrollBox(child, label) { return h("div", { class: "hwl-scroll", tabindex: "0", role: "region", "aria-label": label }, [child]); }
  function table(head, rows, caption) {
    var t = h("table", { class: "hwl-table" }, [caption ? h("caption", { class: "hwl-sr", text: caption }) : null,
      h("thead", {}, [h("tr", {}, head.map(function (x) { return h("th", { scope: "col", text: x }); }))])]);
    var tb = h("tbody");
    rows.forEach(function (r) { tb.append(h("tr", {}, r.map(function (c) { return h("td", { text: c }); }))); });
    t.append(tb);
    return scrollBox(t, (caption || "Table") + ", scrolls sideways on narrow screens");
  }
  function levelLabel(q) {
    var p = Math.round(q * 100);
    var suf = p % 100 >= 11 && p % 100 <= 13 ? "th" : p % 10 === 1 ? "st" : p % 10 === 2 ? "nd" : p % 10 === 3 ? "rd" : "th";
    return p + suf;
  }
  function niceTicks(max, n) {
    var raw = max / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), step = mag;
    [1, 2, 2.5, 5, 10].some(function (m) { step = m * mag; return step >= raw; });
    var out = [];
    for (var v = 0; ; v += step) {
      out.push(v);
      if (v >= max - 1e-9) break;
    }
    return out;
  }
  function group(options, current, onPick, label) {
    var box = h("div", { class: "hwl-tabs", role: "group", "aria-label": label });
    function paint(cur) { Array.prototype.forEach.call(box.children, function (b) { b.setAttribute("aria-pressed", String(b.dataset.k === cur)); }); }
    options.forEach(function (o) {
      box.append(on(h("button", { type: "button", class: "hwl-btn", "data-k": o[0], text: o[1] }), "click", function () { paint(o[0]); onPick(o[0]); }));
    });
    paint(current);
    return box;
  }
  function field(label, control, help) {
    var id = "hwl-" + (++uid);
    control.setAttribute("id", id);
    return h("div", { class: "hwl-field" }, [h("label", { class: "hwl-label", for: id, text: label }), control, help ? h("span", { class: "hwl-help", text: help }) : null]);
  }
  var KIND = { public: "public data", measured: "measured on my laptop", simulated: "simulated" };
  function kindLabel(k) { return /simulated/.test(k) ? "simulated plant, public weather and prices" : KIND[k] || k; }

  /* ---------------- pack jobs under a cap ---------------- */
  function packingPane(P, reduced) {
    if (!P || P.status !== "ready") return { el: pending("The packing result is not in yet."), stop: function () {} };
    var levels = P.quantile_levels, penalties = P.penalties_usd_per_kwh, tr = P.trace;
    var nT = tr.runs.reactive.site_power_kw.length;
    var perHour = Math.round(3600 / tr.bin_s);
    var hours = nT * tr.bin_s / 3600;
    var state = { i: levels.indexOf(0.9) >= 0 ? levels.indexOf(0.9) : levels.length - 3, pen: penalties.indexOf(40) >= 0 ? 40 : penalties[0], t: 0, timer: null };
    function key(q) { return "timestral-5M/q" + String(q); }

    var tMin = Infinity, tMax = -Infinity, pMax = Math.max.apply(null, tr.site_caps_kw);
    Object.keys(tr.runs).forEach(function (k) {
      tr.runs[k].rack_max_gpu_c.forEach(function (row) { row.forEach(function (v) { if (v !== null) { tMin = Math.min(tMin, v); tMax = Math.max(tMax, v); } }); });
      tr.runs[k].site_power_kw.forEach(function (row) { row.forEach(function (v) { pMax = Math.max(pMax, v); }); });
    });
    var ticks = niceTicks(pMax * 1.04, 4);
    var yTop = ticks[ticks.length - 1];

    var label = h("label", { class: "hwl-label" });
    var slider = h("input", { type: "range", min: "0", max: String(levels.length - 1), step: "1", value: String(state.i), class: "hwl-range" });
    var penSel = h("select", {}, penalties.map(function (p) { return h("option", { value: String(p), text: "$" + p + " per kWh" }); }));
    penSel.value = String(state.pen);
    var scrub = h("input", { type: "range", min: "0", max: String(nT - 1), step: "1", value: "0", class: "hwl-range" });
    var play = h("button", { type: "button", class: "hwl-btn", text: reduced ? "Next hour" : "Play" });

    var W = 640, H = 240, L = 50, R = 10, T = 12, B = 44;
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, class: "hwl-chart", role: "img",
      "aria-label": "Simulated site power over the scored window against each site's power cap. Planning lower in the forecast keeps more jobs in and crosses the cap more often." });
    function x(i) { return L + (W - L - R) * i / (nT - 1); }
    function y(v) { return T + (H - T - B) * (1 - v / yTop); }
    ticks.forEach(function (v) {
      svg.append(s("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "hwl-grid" }));
      txt(svg, L - 6, y(v) + 4, "hwl-axis", fmt(v), "end");
    });
    txt(svg, 4, 11, "hwl-axis", "kW");
    for (var hr = 0; hr <= hours; hr += 4) txt(svg, x(Math.min(nT - 1, hr * perHour)), H - B + 16, "hwl-axis", String(hr), "middle");
    txt(svg, W - R, H - 4, "hwl-axis", "hours into the scored window", "end");
    var over = s("g", { class: "hwl-over" });
    svg.append(over);
    tr.site_caps_kw.forEach(function (c, k) {
      svg.append(s("line", { x1: L, x2: W - R, y1: y(c), y2: y(c), class: "hwl-cap hwl-s" + k }));
      txt(svg, L + 4, y(c) - 4, "hwl-axis hwl-cap-t", tr.site_ids[k] + " cap");
    });
    var lines = tr.site_ids.map(function (sid, k) { var p = s("polyline", { class: "hwl-line hwl-s" + k, fill: "none" }); svg.append(p); return p; });
    var cursor = s("line", { y1: T, y2: H - B, class: "hwl-cursor" });
    svg.append(cursor);

    var legend = h("p", { class: "hwl-legend" }, tr.site_ids.map(function (sid, k) {
      return h("span", {}, [h("i", { class: "hwl-key hwl-s" + k }), sid + ", cap " + fmt(tr.site_caps_kw[k], 1) + " kW"]);
    }).concat([h("span", {}, [h("i", { class: "hwl-key hwl-key-over" }), "power above the cap"])]));

    var cells = tr.rack_ids.map(function (rid) {
      var tmp = h("span", { class: "hwl-rack-temp" });
      var cell = h("div", { class: "hwl-rack" }, [h("span", { class: "hwl-rack-id", text: rid }), tmp]);
      return { cell: cell, tmp: tmp };
    });
    var racks = h("div", { class: "hwl-racks", role: "group", "aria-label": "Racks at the moment shown by the time slider, colored by their hottest GPU" }, cells.map(function (c) { return c.cell; }));
    var scale = h("p", { class: "hwl-scale" }, [h("span", { text: fmt(tMin, 0) + " °C" }), h("i", { class: "hwl-ramp", "aria-hidden": "true" }), h("span", { text: fmt(tMax, 0) + " °C" }),
      h("span", { class: "hwl-help", text: "Each box is a rack, colored by its hottest GPU, from pale and cool to red and hot." })]);
    var counters = h("div");
    var best = h("p", { class: "hwl-note" });
    var clock = h("span", { class: "hwl-help" });

    function heat(v) {
      if (v === null || v === undefined) return "var(--chrome-well)";
      var f = Math.max(0, Math.min(1, (v - tMin) / Math.max(1e-6, tMax - tMin)));
      return "oklch(" + (0.86 - 0.28 * f).toFixed(3) + " " + (0.04 + 0.16 * f).toFixed(3) + " " + (95 - 70 * f).toFixed(1) + ")";
    }
    function bestName(k) {
      var m = /^timestral-(\w+)\/q(.+)$/.exec(k || "");
      return m ? "Timestral " + m[1] + " planning at the " + levelLabel(Number(m[2])) + " percentile" : "n/a";
    }
    function draw() {
      var q = levels[state.i];
      label.textContent = "Plan around the " + levelLabel(q) + " percentile of the power forecast";
      slider.setAttribute("aria-valuetext", levelLabel(q) + " percentile");
      var run = tr.runs[key(q)];
      over.replaceChildren();
      lines.forEach(function (ln, k) {
        ln.setAttribute("points", run.site_power_kw.map(function (row, i) { return x(i).toFixed(1) + "," + y(row[k]).toFixed(1); }).join(" "));
        var cap = tr.site_caps_kw[k], bw = (W - L - R) / (nT - 1);
        run.site_power_kw.forEach(function (row, i) {
          if (row[k] > cap) over.append(s("rect", { x: (x(i) - bw / 2).toFixed(1), width: bw.toFixed(1), y: y(row[k]).toFixed(1), height: (y(cap) - y(row[k])).toFixed(1), class: "hwl-over-bar" }));
        });
      });
      cursor.setAttribute("x1", x(state.t)); cursor.setAttribute("x2", x(state.t));
      scrub.value = String(state.t);
      var hh = state.t * tr.bin_s / 3600;
      clock.textContent = "hour " + fmt(hh, 1) + " of " + fmt(hours);
      scrub.setAttribute("aria-valuetext", "hour " + fmt(hh, 1) + " of " + fmt(hours));
      cells.forEach(function (rc, k) {
        var v = run.rack_max_gpu_c[state.t][k];
        rc.cell.style.background = heat(v);
        rc.tmp.textContent = v === null || v === undefined ? "idle" : fmt(v, 1) + " °C";
      });
      var pen = String(state.pen);
      var rows = [["Plan at the " + levelLabel(q) + " percentile", P.policies[key(q)]], ["React to measured power", P.policies.reactive],
        ["Learned quantile choice", P.policies["timestral-5M/learned@" + pen]]];
      counters.replaceChildren(table(["policy", "GPU-hours delivered", "energy over the cap (kWh)", "intervals over the cap", "net value at $" + pen + " per kWh ($)"],
        rows.map(function (r) {
          var m = r[1];
          return [r[0], m ? ci(m.gpu_hours, 0) : "n/a", m ? ci(m.energy_above_cap_kwh, 1) : "n/a", m ? pct(m.violation_rate.mean) : "n/a",
            m && m.net_value_usd && m.net_value_usd[pen] ? ci(m.net_value_usd[pen], 0) : "n/a"];
        }), "Counters for the chosen plan, reacting, and the learned choice: mean and 95% interval over " + P.test_seeds.length + " test episodes"));
      best.textContent = "At $" + pen + " per kWh over the cap, the fixed choice with the most net value on the test episodes was " + bestName(P.best_fixed_by_penalty[pen]) + ".";
    }
    function stop() {
      if (state.timer) root.clearInterval(state.timer);
      state.timer = null;
      if (!reduced) play.textContent = "Play";
    }
    on(play, "click", function () {
      if (reduced) { state.t = Math.min(nT - 1, state.t + perHour); if (state.t >= nT - 1) state.t = 0; draw(); return; }
      if (state.timer) { stop(); return; }
      play.textContent = "Pause";
      state.timer = root.setInterval(function () { state.t = (state.t + 1) % nT; draw(); }, 100);
    });
    on(slider, "input", function () { state.i = Number(slider.value); draw(); });
    on(scrub, "input", function () { state.t = Number(scrub.value); draw(); });
    on(penSel, "change", function () { state.pen = Number(penSel.value); draw(); });
    draw();
    var sid = "hwl-" + (++uid);
    slider.setAttribute("id", sid);
    label.setAttribute("for", sid);
    var el = h("div", { class: "hwl-pane" }, [
      h("p", { class: "hwl-caption", text: "Simulated, not measured. Two sites in a test episode (seed " + tr.seed + ") replayed below. The table gives means and 95% intervals over " +
        P.test_seeds.length + " test episodes. Plan lower in the forecast and more jobs get in, and the sites cross the cap more often." }),
      h("div", { class: "hwl-controls" }, [h("div", { class: "hwl-field hwl-wide" }, [label, slider]), h("span", { class: "hwl-help hwl-wide", text: "1st to 99th percentile in 21 steps. Low plans for a quiet moment, high plans for the worst one." }),
        field("Price of each kWh over the cap", penSel), field("Time in the episode", scrub), h("div", { class: "hwl-field" }, [play, clock])]),
      scrollBox(svg, "Power chart, scrolls sideways on narrow screens"), legend, racks, scale, counters, best]);
    return { el: el, stop: stop };
  }

  /* ---------------- outages ---------------- */
  function outagePane(O) {
    if (!O || O.status !== "ready") return { el: pending(), stop: function () {} };
    var v2 = O.versions.v2, v1 = O.versions.v1;
    function policyTable(V, withPaired, cap) {
      return table(["policy", "useful GPU-hours", "GPU-hours lost to faults"].concat(withPaired ? ["lost, minus reactive"] : []).concat(["events warned in time", "false alarms per day"]),
        Object.keys(V.policies).map(function (k) {
          var p = V.policies[k];
          return [p.label, fmt(p.useful_gpu_h, 0), fmt(p.lost_gpu_h, 1)].concat(withPaired ? [p.lost_gpu_h_vs_reactive ? ci(p.lost_gpu_h_vs_reactive, 1) : "n/a"] : [])
            .concat([p.recall_in_time === null ? "n/a" : pct(p.recall_in_time), p.false_alarms_per_day === null ? "n/a" : fmt(p.false_alarms_per_day, 1)]);
        }), cap);
    }
    var box = h("div", { class: "hwl-pane" });
    if (!v2 || v2.status !== "ready") {
      box.append(h("p", { class: "hwl-caption", text: "Simulated. Warn before trouble, checkpoint early, then move or pause the work." }), h("h3", { class: "hwl-h", text: "With each GPU's own temperature as a warning sign" }), pending());
    } else {
      var ev = v2.events;
      box.append(h("p", { class: "hwl-caption", text: "Simulated, not measured. " + v2.n_test_seeds + " held-out episodes of " + fmt(v2.episode_hours) + " hours, " + v2.events_total + " events in them: " +
        Object.keys(ev).map(function (k) { return ev[k].n + " " + k + "s"; }).join(", ") + ". Of the " + v2.events_scheduled + " scheduled ones, " + v2.events_with_precursor +
        " showed a warning sign in the data first and " + (v2.events_scheduled - v2.events_with_precursor) + " showed nothing. A warning means: save a checkpoint early, then move the work to the other site or pause it. Means over the episodes; the paired column gives a 95% interval." }));
      box.append(h("h3", { class: "hwl-h", text: "With each GPU's own temperature as a warning sign" }), policyTable(v2, true, "Outage response, second version: means over held-out episodes"));
      var bt = v2.by_event_type;
      if (bt && bt.ts28m) {
        box.append(h("h3", { class: "hwl-h", text: "What the Timestral 28M warnings caught, by kind of event" }),
          table(["event", "count", "with a warning sign", "warned in time", "median warning (min)", "GPU-hours lost, reactive", "GPU-hours lost, Timestral 28M"],
            Object.keys(bt.ts28m).map(function (k) {
              var a = bt.ts28m[k], b = bt.reactive ? bt.reactive[k] : null;
              return [k, a.n_events, a.n_with_precursor, a.warned_in_time === null ? "n/a" : pct(a.warned_in_time), a.median_lead_min === null ? "n/a" : fmt(a.median_lead_min, 0),
                b ? fmt(b.lost_gpu_h, 1) : "n/a", fmt(a.lost_gpu_h, 1)];
            }), "Events by kind: how many, how many warned in time, and GPU-hours lost"));
      }
    }
    if (v1 && v1.status === "ready") {
      box.append(h("details", { class: "hwl-details" }, [h("summary", { text: "First version: rack-level warning signs only" }), policyTable(v1, true, "Outage response, first version")]));
    }
    return { el: box, stop: function () {} };
  }

  /* ---------------- cheaper, cleaner hours ---------------- */
  var PC = { reactive: 0, seasonal_naive_24: 1, ets_24: 2, arima_seasonal: 3, timestral_28M: 5, perfect: 6, offline_optimum: 7 };
  var NAMES = { no_shift: "no shifting", reactive: "react to today's price", seasonal_naive_24: "yesterday's prices", ets_24: "ETS", arima_seasonal: "ARIMA",
    timestral_28M: "Timestral 28M", perfect: "perfect foresight", offline_optimum: "best possible schedule" };
  function timingPane(C) {
    if (!C || C.status !== "ready") return { el: pending(), stop: function () {} };
    var st = { pair: "caiso", lam: 5 };
    var holder = h("div");
    var lamOut = h("span", { class: "hwl-help" });
    var lam = h("input", { type: "range", min: "0", max: "10", step: "1", value: String(st.lam), class: "hwl-range" });
    function render() {
      var P = C.pairs[st.pair], pols = Object.keys(P.curves).filter(function (k) { return k !== "no_shift"; });
      var xs = [], ys = [];
      pols.forEach(function (k) { xs = xs.concat(P.curves[k].saving_pct_electricity); ys = ys.concat(P.curves[k].saving_pct_co2); });
      var xt = niceTicks(Math.max.apply(null, xs) * 1.05, 4), yt = niceTicks(Math.max.apply(null, ys) * 1.05, 4);
      var x1 = xt[xt.length - 1], y1 = yt[yt.length - 1];
      var W = 640, H = 300, L = 54, R = 14, T = 14, B = 44;
      function X(v) { return L + (W - L - R) * v / x1; }
      function Y(v) { return T + (H - T - B) * (1 - v / y1); }
      var svg = s("svg", { viewBox: "0 0 " + W + " " + H, class: "hwl-chart", role: "img",
        "aria-label": "Saving in electricity cost against saving in carbon for each scheduling policy; higher and further right is better. The table below gives the numbers." });
      xt.forEach(function (v) { svg.append(s("line", { x1: X(v), x2: X(v), y1: T, y2: H - B, class: "hwl-grid" })); txt(svg, X(v), H - B + 16, "hwl-axis", fmt(v), "middle"); });
      yt.forEach(function (v) { svg.append(s("line", { x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: "hwl-grid" })); txt(svg, L - 6, Y(v) + 4, "hwl-axis", fmt(v), "end"); });
      txt(svg, W - R, H - 4, "hwl-axis", "saving in electricity cost of the flexible work (%)", "end");
      txt(svg, 4, 11, "hwl-axis", "saving in carbon (%)");
      pols.forEach(function (k) {
        var c = P.curves[k];
        svg.append(s("polyline", { class: "hwl-pareto hwl-p" + PC[k], fill: "none",
          points: c.saving_pct_electricity.map(function (v, i) { return X(v).toFixed(1) + "," + Y(c.saving_pct_co2[i]).toFixed(1); }).join(" ") }));
        svg.append(s("circle", { class: "hwl-dot hwl-p" + PC[k] + "-f", r: 5, cx: X(c.saving_pct_electricity[st.lam]).toFixed(1), cy: Y(c.saving_pct_co2[st.lam]).toFixed(1) }));
      });
      var swing = P.curves.timestral_28M.lambda[st.lam];
      lamOut.textContent = "Weight on carbon: " + fmt(swing, 1) + " (0 chases price only, 1 chases carbon only)";
      lam.setAttribute("aria-valuetext", "weight on carbon " + fmt(swing, 1));
      var key = h("p", { class: "hwl-legend" }, pols.map(function (k) { return h("span", {}, [h("i", { class: "hwl-key hwl-k" + PC[k] }), NAMES[k] || k]); }));
      var tb = table(["policy", "electricity saved (%)", "carbon saved (%)", "whole cost per token saved (%)"],
        pols.map(function (k) { var c = P.curves[k]; return [NAMES[k] || k, fmt(c.saving_pct_electricity[st.lam], 1), fmt(c.saving_pct_co2[st.lam], 1), fmt(c.saving_pct_total[st.lam], 2)]; }),
        "Savings against no shifting, at the chosen weight on carbon");
      var note = st.pair === "de" ? "Germany's carbon figure is a lifecycle estimate built from published medians, not an official number. " : "California's carbon figure is the in-state intensity, with imports left out. ";
      holder.replaceChildren(scrollBox(svg, "Savings chart, scrolls sideways on narrow screens"), key, tb, h("p", { class: "hwl-note", text: note + "The whole cost per token moves little because hardware is most of it." }));
    }
    var region = group([["caiso", "California (CAISO)"], ["de", "Germany (DE-LU)"]], st.pair, function (k) { st.pair = k; render(); }, "Grid region");
    on(lam, "input", function () { st.lam = Number(lam.value); render(); });
    render();
    return { stop: function () {}, el: h("div", { class: "hwl-pane" }, [
      h("p", { class: "hwl-caption", text: "Real day-ahead prices and carbon from the last " + C.test_weeks + " weeks, held out; the workload is modeled, not measured. " + pct(C.setting.flexible_fraction) + " of the work may wait up to " + C.setting.window_hours + " hours. Each line sweeps the weight on carbon from 0 to 1; the dots show the weight you pick." }),
      region, h("div", { class: "hwl-controls" }, [field("Weight on carbon", lam), lamOut]), holder]) };
  }

  /* ---------------- known inputs ---------------- */
  function inputsPane(A, S, F) {
    var st = { size: "timestral-209M" };
    var holder = h("div");
    function oneTable(name, D, size) {
      var cfgs = D.methods[size];
      if (!cfgs) return null;
      var rows = Object.keys(cfgs).map(function (c) {
        var x = cfgs[c];
        var lab = x.groups.length ? x.groups.map(function (g) { return D.groups[g] || g; }).join(" + ") : "no inputs";
        var read = x.vs_none === "baseline" ? "baseline" : x.vs_none === "lower" ? "lower" : x.vs_none === "higher" ? "higher" : "no clear change";
        return [lab, fmt(x.wql, 4), "[" + fmt(x.lo, 4) + ", " + fmt(x.hi, 4) + "]", x.change_pct === null ? "" : (x.change_pct > 0 ? "+" : "") + fmt(x.change_pct, 1) + "%" + (x.d_lo === undefined ? "" : " [" + fmt(x.d_lo, 4) + ", " + fmt(x.d_hi, 4) + "]"), read];
      });
      Object.keys(D.methods).filter(function (m) { return m.indexOf("timestral") !== 0; }).forEach(function (m) {
        var x = D.methods[m].none;
        rows.push([m.replace(/-\d+$/, "").replace("-", " ") + " (no inputs)", fmt(x.wql, 4), "[" + fmt(x.lo, 4) + ", " + fmt(x.hi, 4) + "]", "", "reference"]);
      });
      return h("div", {}, [h("h3", { class: "hwl-h", text: D.what }),
        h("p", { class: "hwl-help", text: kindLabel(D.data_kind) + ". " + fmt(D.n_origins) + " forecast windows, " + D.horizon_steps + " steps of " + D.step + " ahead." }),
        table(["inputs known ahead", "loss", "95% interval", "change [paired difference interval]", "reading"], rows, D.what + ": loss with and without known-ahead inputs")]);
    }
    function render() {
      holder.replaceChildren();
      Object.keys(A.datasets).forEach(function (n) { var t = oneTable(n, A.datasets[n], st.size); if (t) holder.append(t); });
      holder.append(h("h3", { class: "hwl-h hwl-h-big", text: "Simulated cluster: job schedule, training-step phase, weather forecast, price and carbon forecast" }));
      if (!S || S.status !== "ready") holder.append(pending("Result pending: the simulated version of this test is still running."));
      else Object.keys(S.datasets).forEach(function (n) { var t = oneTable(n, S.datasets[n], st.size); if (t) holder.append(t); });
      var runs = F && F.status === "ready" ? F.runs : null;
      holder.append(h("h3", { class: "hwl-h hwl-h-big", text: "Fine-tuned against zero-shot" }));
      if (!runs) holder.append(pending("Result pending: the fine-tuning runs are not in yet."));
      else {
        holder.append(h("p", { class: "hwl-help", text: "Loss on held-out windows. For each side I take its better setting, with or without the known-ahead inputs, and divide: below 1 means fine-tuning lowered the loss. The differences are paired over the same windows, with 95% intervals." }));
        var d = function (x) { return x ? (x.mean > 0 ? "+" : "") + fmt(x.mean, 4) + " [" + fmt(x.lo, 4) + ", " + fmt(x.hi, 4) + "]" : ""; };
        runs.forEach(function (r) {
          var rows = [];
          r.series.forEach(function (sr) {
            r.models.forEach(function (m) {
              var z = sr.best.zero_shot, f = sr.best[m], pv = sr.paired_vs_zero_shot[m] || {};
              if (!z || !f) return;
              rows.push([sr.what + (r.models.length > 1 ? " (" + m.replace(/^finetuned-/, "") + ")" : ""), kindLabel(sr.data_kind), fmt(z.wql, 4), fmt(f.wql, 4), fmt(f.wql / z.wql, 3), d(pv.none), d(pv.cov_all)]);
            });
          });
          var cap = "Timestral " + r.size + (r.run_label === "colab-cpu" ? ", CPU pilot (" + r.models.map(function (m) { return m.replace(/^finetuned-/, ""); }).join(", ") + ")" : ", all weights trained on one GPU");
          holder.append(h("h3", { class: "hwl-h", text: cap }), table(["series", "data", "zero-shot", "fine-tuned", "ratio", "difference, no inputs", "difference, with inputs"], rows, cap + ": fine-tuned against zero-shot"));
        });
      }
    }
    var el = h("div", { class: "hwl-pane" }, []);
    if (!A || A.status !== "ready") { el.append(pending("The known-inputs result is not in yet.")); return { el: el, stop: function () {} }; }
    el.append(h("p", { class: "hwl-caption", text: "What does a forecaster gain from things that are known ahead of time, like a job schedule, a weather forecast or a day-ahead price? Loss is the weighted quantile loss over all horizons, lower is better. Series are measured (my laptop) or public (grid). Intervals are 95% block-bootstrap intervals. The reading comes from the paired difference over the same windows: I call a change real only when its interval is clear of zero. GB carbon uses an archived forecast whose issue time is undocumented." }),
      group([["timestral-209M", "Timestral 209M"], ["timestral-28M", "Timestral 28M"]], st.size, function (k) { st.size = k; render(); }, "Model size"), holder);
    render();
    return { el: el, stop: function () {} };
  }

  function mount(el) {
    el.replaceChildren(h("p", { class: "hwl-pending", text: "Loading the Heatwave results." }));
    var reduced = !!(root.matchMedia && root.matchMedia("(prefers-reduced-motion: reduce)").matches);
    root.fetch(DATA_URL).then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); }).then(function (D) {
      var panes = { packing: packingPane(D.packing, reduced), outage: outagePane(D.outage), timing: timingPane(D.cost), inputs: inputsPane(D.ablation, D.ablation_sim, D.finetune) };
      var names = { packing: "Pack jobs under a cap", outage: "Outages", timing: "Cheaper, cleaner hours", inputs: "Known inputs" };
      var order = Object.keys(panes), btns = {};
      var tabs = h("div", { class: "hwl-tabs", role: "tablist", "aria-label": "Heatwave experiments" });
      var panel = h("div", { class: "hwl-body", role: "tabpanel", tabindex: "0" });
      function show(k, focus) {
        order.forEach(function (o) { panes[o].stop(); var on_ = o === k; btns[o].setAttribute("aria-selected", String(on_)); btns[o].setAttribute("tabindex", on_ ? "0" : "-1"); });
        panel.replaceChildren(panes[k].el);
        panel.setAttribute("aria-labelledby", btns[k].id);
        if (focus) btns[k].focus();
      }
      order.forEach(function (k, i) {
        var b = h("button", { type: "button", role: "tab", class: "hwl-btn", id: "hwl-tab-" + k, text: names[k], "aria-controls": "hwl-panel" });
        on(b, "click", function () { show(k, false); });
        on(b, "keydown", function (e) {
          var j = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? order.length - 1 : null;
          if (j === null) return;
          e.preventDefault();
          show(order[(j + order.length) % order.length], true);
        });
        btns[k] = b;
        tabs.append(b);
      });
      panel.setAttribute("id", "hwl-panel");
      el.replaceChildren(h("div", { class: "hwl" }, [tabs, panel]));
      show("packing", false);
    }).catch(function () {
      el.replaceChildren(h("p", { class: "hwl-pending", text: "The Heatwave data file could not be fetched." }));
    });
  }

  root.GPUStackHeatwave = { mount: mount };
})(typeof window !== "undefined" ? window : globalThis);
