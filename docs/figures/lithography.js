/* lithography: light shines through a mask and prints lines on a wafer.
   The smallest printable line is CD = k1 x wavelength / NA, with k1 = 0.3
   (a typical value). Pick the light (193 nm immersion or 13.5 nm EUV) and the
   numerical aperture (NA) and watch the line width change. */
(function (root) {
  "use strict";
  var F = root.GPUStackFigures;
  var K1 = 0.3;
  var TOOLS = {
    duv: {
      name: "193 nm immersion",
      nm: 193,
      na: [0.85, 1.35, 1.35],
    },
    euv: {
      name: "13.5 nm EUV",
      nm: 13.5,
      na: [0.33, 0.55, 0.33],
    },
  };
  var PX_PER_NM = 1.4; // close-up scale, same for every setting

  F.define("lithography", {
    title: "Printing a line with light",
    label: "Diagram: light shines through a mask and a lens and prints lines on a wafer. Choose the light and lens width to see the smallest printable line.",
    summary:
      "Light passes through a mask with slits, then a lens, and prints lines on a wafer. The smallest line is about 0.3 times the wavelength divided by the lens's numerical aperture. " +
      "193 nanometer immersion light with a numerical aperture of 1.35 prints lines near 43 nanometers. 13.5 nanometer EUV light at 0.33 prints about 12 nanometers, and at 0.55 about 7 nanometers.",
    build: function (ctx) {
      var h = ctx.h, s = ctx.s, u = ctx.util;
      var uid = Math.random().toString(36).slice(2, 7);
      var tool = "euv", na = TOOLS.euv.na[2];
      var slits = [150, 180, 210];

      var wavePat = s("pattern", { id: "wv" + uid, patternUnits: "userSpaceOnUse", width: 8, height: 14 }, [
        s("rect", { x: 0, y: 0, width: 8, height: 3, fill: "#7fd0dc" }),
      ]);
      var linePat = s("pattern", { id: "ln" + uid, patternUnits: "userSpaceOnUse", width: 40, height: 60 }, [
        s("rect", { x: 0, y: 0, width: 20, height: 60, fill: "#e9c34a" }),
      ]);
      var clip = s("clipPath", { id: "cp" + uid }, [s("rect", { x: 0, y: 0, width: 0, height: 60 })]);
      var beam = function (pts) {
        return s("polygon", { points: pts, fill: "url(#wv" + uid + ")" });
      };
      var beams = [
        s("rect", { x: 100, y: 24, width: 160, height: 46, fill: "url(#wv" + uid + ")" }),
      ];
      slits.forEach(function (c) {
        beams.push(s("rect", { x: c - 7, y: 78, width: 14, height: 44, fill: "url(#wv" + uid + ")" }));
        var t = 180 + (c - 180) * 0.35;
        beams.push(beam([c - 7 + "," + 139, c + 7 + "," + 139, t + 2.5 + "," + 190, t - 2.5 + "," + 190].join(" ")));
      });
      var wavesG = s("g", null, beams);
      var maskPieces = [[60, 143], [157, 173], [187, 203], [217, 300]].map(function (p) {
        return s("rect", { x: p[0], y: 70, width: p[1] - p[0], height: 8, fill: "#9aa0ad" });
      });
      var scene = s("svg", { class: "li-scene", viewBox: "0 0 360 224", role: "img", "aria-label": "Light passing through a mask and a lens onto a wafer" }, [
        s("defs", null, [wavePat]),
        s("rect", { x: 0, y: 0, width: 360, height: 224, fill: "var(--well-dark, #1d2027)" }),
        wavesG,
        s("rect", { x: 100, y: 10, width: 160, height: 14, fill: "#e9c34a" }),
        s("text", { x: 268, y: 21, text: "light" }),
        ].concat(maskPieces).concat([
        s("text", { x: 304, y: 78, text: "mask" }),
        s("ellipse", { cx: 180, cy: 130, rx: 66, ry: 9, fill: "#5d86c8", opacity: 0.85 }),
        s("text", { x: 252, y: 134, text: "lens" }),
        s("rect", { x: 90, y: 190, width: 180, height: 12, fill: "#9aa0ad" }),
        s("text", { x: 278, y: 200, text: "wafer" }),
      ]));

      var close = s("svg", { class: "li-scene", viewBox: "0 0 360 76", role: "img", "aria-label": "Close-up of the printed lines", style: "margin-top:6px" }, [
        s("defs", null, [linePat, clip]),
        s("rect", { x: 0, y: 0, width: 360, height: 60, fill: "#2b2e36" }),
        s("g", { "clip-path": "url(#cp" + uid + ")" }, [s("rect", { x: 0, y: 0, width: 360, height: 60, fill: "url(#ln" + uid + ")" })]),
      ]);
      var scaleLine = s("rect", { x: 4, y: 66, width: 50 * PX_PER_NM, height: 3, fill: "var(--f-ink, #1c1d21)" });
      var scaleTxt = s("text", { x: 4 + 50 * PX_PER_NM + 8, y: 71, text: "50 nm", style: "fill:var(--f-soft,#4a4c54)" });
      close.appendChild(scaleLine);
      close.appendChild(scaleTxt);
      close.insertBefore(s("rect", { x: 0, y: 62, width: 360, height: 14, fill: "var(--f-body,#f7f6f2)" }), scaleLine);

      var toolSeg = h("div", { class: "gsf-seg", role: "group", "aria-label": "Type of light" });
      var toolBtns = {};
      Object.keys(TOOLS).forEach(function (k) {
        var b = h("button", { type: "button", "aria-pressed": k === tool ? "true" : "false", text: TOOLS[k].name });
        b.addEventListener("click", function () { setTool(k); });
        toolBtns[k] = b;
        toolSeg.appendChild(b);
      });
      var slider = h("input", { type: "range", step: 0.01, "aria-label": "Numerical aperture, how wide a cone of light the lens gathers" });
      var naOut = h("b", { class: "gsf-num" });
      var cdOut = h("p", { class: "li-cd", "aria-live": "polite" });
      var eq = h("p", { class: "li-eq" });
      var cap = h("p", { class: "li-caption", "data-slot": "caption" });
      var custom = ctx.root.getAttribute("data-caption");

      ctx.el.appendChild(h("div", null, [
        scene,
        close,
        h("div", { class: "li-controls" }, [
          h("div", null, [h("span", { class: "li-lab", text: "Light" }), toolSeg]),
          h("div", null, [h("label", { class: "li-lab" }, ["Lens opening, NA ", naOut]), slider]),
        ]),
        h("div", { class: "li-read" }, [cdOut, eq]),
        h("p", { class: "gsf-note", text: "k1 = 0.3 is a typical value for a good single exposure. Schematic, not to scale. The close-up uses the same scale for every setting." }),
        cap,
      ]));

      function cd() { return (K1 * TOOLS[tool].nm) / na; }
      function update() {
        var T = TOOLS[tool], v = cd();
        naOut.textContent = na.toFixed(2);
        slider.value = String(na);
        var txt = v >= 10 ? Math.round(v) : v.toFixed(1);
        cdOut.innerHTML = "";
        cdOut.appendChild(document.createTextNode(txt + " nm"));
        cdOut.appendChild(h("small", { text: "smallest line you can print" }));
        eq.textContent = "CD = k1 x wavelength / NA = " + K1 + " x " + T.nm + " / " + na.toFixed(2);
        cap.textContent = custom || "Finest line: about " + txt + " nm";
        var px = Math.max(1.5, v * PX_PER_NM);
        linePat.setAttribute("width", String(px * 2));
        linePat.firstChild.setAttribute("width", String(px));
        var vis = 6 + T.nm * 0.14; // schematic wavelength, not to scale
        wavePat.setAttribute("height", String(vis));
        wavePat.firstChild.setAttribute("height", String(Math.max(1.4, vis * 0.2)));
        ctx.setSummary("Using " + T.name + " light at a numerical aperture of " + na.toFixed(2) + ", the smallest printable line is about " + txt + " nanometers.");
      }
      function setTool(k) {
        tool = k;
        Object.keys(toolBtns).forEach(function (n) { toolBtns[n].setAttribute("aria-pressed", n === k ? "true" : "false"); });
        var r = TOOLS[k].na;
        slider.min = String(r[0]);
        slider.max = String(r[1]);
        na = r[2];
        update();
      }
      slider.addEventListener("input", function () {
        na = Number(slider.value);
        update();
      });
      setTool("euv");

      var clipRect = clip.firstChild;
      return {
        duration: 4.8,
        loop: true,
        still: 3.6,
        render: function (t) {
          var vis = Number(wavePat.getAttribute("height"));
          var off = ((t / 1.2) % 1) * vis;
          wavePat.setAttribute("patternTransform", "translate(0 " + off.toFixed(2) + ")");
          clipRect.setAttribute("width", String((u.ease(t / 2.6) * 360).toFixed(1)));
        },
      };
    },
  });
})(typeof window !== "undefined" ? window : globalThis);
