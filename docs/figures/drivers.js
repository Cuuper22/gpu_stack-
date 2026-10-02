/* drivers: what moves the cost of training, as horizontal bars, plus one
   slider: how much of the GPU's top speed a run actually uses. Bars come from
   data/drivers.json (label, share). If that file is missing a marked
   placeholder is shown and a console.info line says so. */
(function (root) {
  "use strict";
  var F = root.GPUStackFigures;

  // Assumptions for the slider (shown on screen).
  var PARAMS = 7e9; // a 7 billion parameter model
  var PEAK = 989.4e12; // H100 dense 16-bit operations per second
  var PRICE = 2; // dollars per GPU-hour, assumed
  var BASE_MFU = 0.4;

  // cost per token = price * 6*N*D / (peak * MFU * 3600) / D
  function costPerToken(mfu) {
    var D = 1e12;
    return (PRICE * 6 * PARAMS * D) / (PEAK * mfu * 3600) / D;
  }

  var PLACEHOLDER = [
    { label: "Share of GPU speed actually used", share: 0.3 },
    { label: "GPU price per hour", share: 0.22 },
    { label: "Model size", share: 0.18 },
    { label: "Training tokens", share: 0.15 },
    { label: "Electricity price", share: 0.06 },
    { label: "Everything else together", share: 0.09 },
  ];

  function normalise(raw) {
    var rows = Array.isArray(raw) ? raw : raw && (raw.top || raw.drivers || raw.rows || raw.items);
    if (!Array.isArray(rows)) return null;
    rows = rows
      .filter(function (r) { return r && typeof r.label === "string" && isFinite(r.share); })
      .map(function (r) { return { label: r.label, share: Number(r.share) }; });
    if (!rows.length) return null;
    var sum = rows.reduce(function (a, r) { return a + r.share; }, 0);
    if (sum > 1.5) rows.forEach(function (r) { r.share /= 100; });
    return rows;
  }

  F.define("drivers", {
    title: "What moves the cost",
    label: "Chart and slider: what moves the cost of training, and how cost per token changes with the share of GPU speed you use",
    summary:
      "Horizontal bars show how much each input moves the cost of training. Below, a slider sets the share of the GPU's top speed " +
      "that a run actually uses, from 20 to 60 percent. Cost per token is shown relative to 40 percent: half the speed used means twice the cost.",
    build: function (ctx) {
      var h = ctx.h, u = ctx.util;
      var list = h("ul", { class: "dr-bars", "aria-label": "Share of cost movement by input" });
      var bannerSlot = h("div");
      var rowsData = [], fills = [];
      var base = ctx.root.getAttribute("data-src") || "data/drivers.json";

      function paintRows(rows, placeholder) {
        rowsData = rows.slice().sort(function (a, b) { return b.share - a.share; });
        var max = Math.max.apply(null, rowsData.map(function (r) { return r.share; })) || 1;
        list.textContent = "";
        list.className = "dr-bars" + (placeholder ? " dr-placeholder" : "");
        fills = rowsData.map(function (r, i) {
          var f = h("div", { class: "dr-fill" });
          f.dataset.w = (r.share / max).toFixed(4);
          list.appendChild(
            h("li", { class: "dr-row" + (i === 0 ? " is-top" : "") }, [
              h("span", { class: "dr-label", text: r.label }),
              h("div", { class: "dr-track" }, [f]),
              h("span", { class: "dr-val", text: Math.round(r.share * 100) + "%" }),
            ])
          );
          return f;
        });
        bannerSlot.textContent = "";
        if (placeholder) {
          bannerSlot.appendChild(h("p", { class: "dr-banner", text: "Placeholder values, not data. The real shares arrive with data/drivers.json." }));
        }
        grow(lastT);
      }
      var lastT = 0;
      paintRows(PLACEHOLDER, true);
      if (root.fetch) {
        root
          .fetch(base)
          .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
          .then(function (j) {
            var rows = normalise(j);
            if (!rows) throw new Error("no rows");
            paintRows(rows, false);
          })
          .catch(function () {
            if (root.console) root.console.info("drivers: " + base + " not available, showing a marked placeholder");
          });
      }

      // slider
      var touched = false;
      var slider = h("input", { type: "range", min: 20, max: 60, step: 1, value: 40, id: "dr-mfu-" + Math.random().toString(36).slice(2, 7), "aria-label": "Share of the GPU's top speed actually used, percent" });
      var useOut = h("b", { text: "40%" });
      var big = h("div", { class: "dr-big" });
      var bigNum = h("span", { text: "1.0x" });
      var bigSub = h("small", { text: "cost per token, compared with using 40%" });
      big.appendChild(bigNum);
      big.appendChild(bigSub);
      var fillM = h("div", { class: "dr-meter-fill" });
      var meterNote = h("p");
      var scale = h("div", { class: "dr-scale", "aria-hidden": "true" });
      function pos(v) { return ((v - 20) / 40) * 100; }
      scale.appendChild(h("i", { style: "left:" + pos(38) + "%;width:" + (pos(43) - pos(38)) + "%" }));
      scale.appendChild(h("span", { style: "left:" + pos(38) + "%", text: "Llama 3: 38 to 43%" }));

      function setMfu(pct, fromUser) {
        var mfu = pct / 100;
        var rel = costPerToken(mfu) / costPerToken(BASE_MFU);
        useOut.textContent = Math.round(pct) + "%";
        bigNum.textContent = rel.toFixed(1) + "x";
        fillM.style.width = Math.min(100, (rel / 2.2) * 100) + "%";
        meterNote.innerHTML = "At 40% it costs about <b class=\"gsf-num\">$" + u.fmt(costPerToken(BASE_MFU) * 1e6, 2) + "</b> per million tokens in GPU rental alone.";
        slider.setAttribute("aria-valuetext", Math.round(pct) + " percent, cost " + rel.toFixed(1) + " times");
        if (fromUser) ctx.setSummary("At " + Math.round(pct) + " percent of the GPU's top speed, cost per token is " + rel.toFixed(1) + " times the cost at 40 percent.");
      }
      slider.addEventListener("input", function () {
        touched = true;
        big.setAttribute("aria-live", "polite");
        setMfu(Number(slider.value), true);
      });
      var refMark = h("div", { class: "dr-meter-ref", style: "left:" + (1 / 2.2) * 100 + "%" });

      var play = h("div", { class: "dr-play" }, [
        h("p", { class: "dr-q", text: "How much of the GPU's speed do you actually use?" }),
        h("p", { class: "dr-use" }, [h("span", { text: "Share of top speed used" }), useOut]),
        slider,
        scale,
        h("div", { class: "dr-out" }, [
          big,
          h("div", { class: "dr-meter" }, [
            h("div", { class: "dr-meter-track" }, [fillM, refMark]),
            meterNote,
          ]),
        ]),
        h("p", { class: "gsf-note", text: "Assumed: a 7 billion parameter model, an H100 at 989.4 trillion operations per second, $2 per GPU-hour. The ratio does not depend on the price. Halve the speed you use and each token costs twice as much." }),
      ]);
      ctx.el.appendChild(bannerSlot);
      ctx.el.appendChild(list);
      ctx.el.appendChild(play);
      setMfu(40, false);

      function grow(t) {
        lastT = t;
        fills.forEach(function (f, i) {
          var p = u.ease((t - i * 0.12) / 0.8);
          f.style.transform = "scaleX(" + (Number(f.dataset.w) * p).toFixed(4) + ")";
        });
      }

      return {
        duration: 4.4,
        autoplay: true,
        render: function (t) {
          grow(t);
          if (touched) return;
          // one gentle sweep to show the slider moves the number
          var s = u.clamp((t - 1.8) / 2.4, 0, 1);
          var v = 40 - 20 * Math.sin(Math.PI * s) * (s > 0 && s < 1 ? 1 : 0);
          if (s > 0 && s < 1) {
            slider.value = String(Math.round(v));
            setMfu(v, false);
          } else if (t >= 4.4 || s === 0) {
            slider.value = "40";
            setMfu(40, false);
          }
        },
        onReplay: function () {
          touched = false;
        },
      };
    },
  });
})(typeof window !== "undefined" ? window : globalThis);
