/* Mini-diagrams for the explainer pop-ups.
 *
 * Every visual is a 260 x 120 SVG whose loop (2 to 5 seconds) shows one
 * mechanism. The markup is plain SVG, the motion is CSS keyframes, and the
 * base style of each element is the finished frame, so removing the
 * animation (prefers-reduced-motion) leaves a readable still picture.
 *
 *   GPUStackExplainVisuals.ids            list of visual ids
 *   GPUStackExplainVisuals.has(id)        true if the id exists
 *   GPUStackExplainVisuals.svg(id, alt)   SVG markup string
 *   GPUStackExplainVisuals.mount(host, id, { alt })  put it in an element
 *   GPUStackExplainVisuals.css()          the stylesheet text
 *
 * Works in a browser (window.GPUStackExplainVisuals) and in Node (require).
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.GPUStackExplainVisuals = api;
})(this, function () {
  "use strict";

  var W = 260;
  var H = 120;
  var defs = {};
  var order = [];
  var cur = null;
  var counter = 0;

  /* ---------- small helpers ---------- */

  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function r1(n) {
    return Math.round(n * 10) / 10;
  }

  function kf(name, stops) {
    return (
      "@keyframes " +
      name +
      "{" +
      stops
        .map(function (s) {
          return r1(s[0]) + "%{" + s[1] + "}";
        })
        .join("") +
      "}"
    );
  }

  function scope(sel) {
    return sel
      .split(",")
      .map(function (s) {
        return ".v-" + cur.id + " " + s.trim();
      })
      .join(",");
  }

  /* Hold `from`, move to `to` between a% and b% of the loop, hold, reset.
     The element's own style must already equal `to`. */
  function an(sel, dur, a, b, from, to, ease) {
    var n = "xv" + ++counter;
    cur.css.push(
      kf(n, [
        [0, from],
        [a, from],
        [b, to],
        [93, to],
        [100, from],
      ]) +
        scope(sel) +
        "{animation:" +
        n +
        " " +
        dur +
        "s " +
        (ease || "ease-out") +
        " infinite}"
    );
  }

  /* Free-form keyframes. */
  function loop(sel, dur, stops, ease, extra) {
    var n = "xv" + ++counter;
    cur.css.push(
      kf(n, stops) +
        scope(sel) +
        "{animation:" +
        n +
        " " +
        dur +
        "s " +
        (ease || "linear") +
        " infinite;" +
        (extra || "") +
        "}"
    );
  }

  /* Reveal a path (pathLength 1) between a% and b%. */
  function draw(sel, dur, a, b) {
    an(sel, dur, a, b, "stroke-dashoffset:1", "stroke-dashoffset:0", "linear");
  }

  /* Move a dot along sample points between a% and b%. */
  function follow(sel, dur, pts, a, b) {
    var stops = [[0, tr(pts[0])]];
    pts.forEach(function (p, i) {
      stops.push([a + ((b - a) * i) / (pts.length - 1), tr(p)]);
    });
    stops.push([93, tr(pts[pts.length - 1])]);
    stops.push([100, tr(pts[0])]);
    loop(sel, dur, stops, "linear");
  }

  function tr(p) {
    return "transform:translate(" + r1(p[0]) + "px," + r1(p[1]) + "px)";
  }

  function T(x, y, s, cls, extra) {
    return (
      '<text x="' +
      x +
      '" y="' +
      y +
      '" class="t ' +
      (cls || "") +
      '"' +
      (extra ? " " + extra : "") +
      ">" +
      s +
      "</text>"
    );
  }

  function rect(x, y, w, h, cls, extra) {
    return (
      '<rect x="' +
      x +
      '" y="' +
      y +
      '" width="' +
      w +
      '" height="' +
      h +
      '" class="' +
      (cls || "") +
      '"' +
      (extra ? " " + extra : "") +
      "/>"
    );
  }

  function line(x1, y1, x2, y2, cls, extra) {
    return (
      '<line x1="' +
      x1 +
      '" y1="' +
      y1 +
      '" x2="' +
      x2 +
      '" y2="' +
      y2 +
      '" class="' +
      (cls || "") +
      '"' +
      (extra ? " " + extra : "") +
      "/>"
    );
  }

  function pathD(pts) {
    return pts
      .map(function (p, i) {
        return (i ? "L" : "M") + r1(p[0]) + " " + r1(p[1]);
      })
      .join("");
  }

  function poly(pts, cls, extra) {
    return (
      '<path d="' +
      pathD(pts) +
      '" pathLength="1" class="' +
      (cls || "") +
      '"' +
      (extra ? " " + extra : "") +
      "/>"
    );
  }

  function at(x, y, inner) {
    return '<g transform="translate(' + x + " " + y + ')">' + inner + "</g>";
  }

  function arc(cx, cy, r, p0, p1) {
    function pt(p) {
      var a = Math.PI * (1 - p);
      return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
    }
    var a = pt(p0);
    var b = pt(p1);
    return (
      "M" +
      r1(a[0]) +
      " " +
      r1(a[1]) +
      "A" +
      r +
      " " +
      r +
      " 0 0 1 " +
      r1(b[0]) +
      " " +
      r1(b[1])
    );
  }

  function arrowHead(x, y, dir, cls) {
    var d = dir;
    return (
      '<path d="M' +
      x +
      " " +
      (y - 5) +
      "L" +
      (x + 8 * d) +
      " " +
      y +
      "L" +
      x +
      " " +
      (y + 5) +
      'Z" class="' +
      cls +
      '"/>'
    );
  }

  function def(id, alt, build) {
    cur = { id: id, css: [] };
    var svg = build();
    defs[id] = { id: id, alt: alt, svg: svg, css: cur.css.join("") };
    order.push(id);
    cur = null;
  }

  /* ---------- shared stylesheet ---------- */

  var BASE_CSS =
    ".gsx-vis{" +
    "--k-ink:var(--pixel-ink,#14151a);" +
    "--k-cy:var(--accent-cyan,#2d8f9a);" +
    "--k-cd:var(--accent-cyan-deep,#1f6f79);" +
    "--k-go:var(--accent-gold,#f2c230);" +
    "--k-gn:var(--accent-green,#5cc14a);" +
    "--k-rd:var(--danger-red,#d0473a);" +
    "--k-bl:var(--title-bar,#2d3d9a);" +
    "--k-pa:var(--pane-bright,#fbfbf8);" +
    "--k-so:var(--chrome-well,#e4e6ea);" +
    "--k-ln:var(--chrome-border,#9a9ea6);" +
    "--k-tx:var(--text-soft,#4a4d55);" +
    "--k-wd:var(--well-dark,#272a33);" +
    "--k-t1:oklch(0.88 0.07 195);--k-t2:oklch(0.92 0.10 88);" +
    "--k-t3:oklch(0.89 0.11 140);--k-t4:oklch(0.87 0.08 28);--k-t5:oklch(0.87 0.06 260);" +
    "}" +
    ".gsx-vis svg{display:block;width:100%;height:auto;overflow:hidden}" +
    ".gsx-vis svg *{transform-box:fill-box}" +
    ".gsx-vis .t{font:500 10px var(--font-mono,ui-monospace,monospace);fill:var(--k-ink);white-space:pre}" +
    ".gsx-vis .tb{font-weight:600}.gsx-vis .tm{text-anchor:middle}.gsx-vis .te{text-anchor:end}" +
    ".gsx-vis .ts{fill:var(--k-tx)}.gsx-vis .tw{fill:var(--k-pa)}.gsx-vis .tr{fill:var(--k-rd)}" +
    ".gsx-vis .z{font-size:15px}.gsx-vis .zz{font-size:26px}" +
    ".gsx-vis .f-ink{fill:var(--k-ink)}.gsx-vis .f-cy{fill:var(--k-cy)}.gsx-vis .f-cd{fill:var(--k-cd)}" +
    ".gsx-vis .f-go{fill:var(--k-go)}.gsx-vis .f-gn{fill:var(--k-gn)}.gsx-vis .f-rd{fill:var(--k-rd)}" +
    ".gsx-vis .f-bl{fill:var(--k-bl)}.gsx-vis .f-pa{fill:var(--k-pa)}.gsx-vis .f-so{fill:var(--k-so)}" +
    ".gsx-vis .f-ln{fill:var(--k-ln)}.gsx-vis .f-wd{fill:var(--k-wd)}.gsx-vis .f-no{fill:none}" +
    ".gsx-vis .f-t1{fill:var(--k-t1)}.gsx-vis .f-t2{fill:var(--k-t2)}.gsx-vis .f-t3{fill:var(--k-t3)}" +
    ".gsx-vis .f-t4{fill:var(--k-t4)}.gsx-vis .f-t5{fill:var(--k-t5)}.gsx-vis .f-ha{fill:url(#gsx-hatch)}" +
    ".gsx-vis .s-ink{stroke:var(--k-ink)}.gsx-vis .s-cy{stroke:var(--k-cy)}.gsx-vis .s-cd{stroke:var(--k-cd)}" +
    ".gsx-vis .s-go{stroke:var(--k-go)}.gsx-vis .s-gn{stroke:var(--k-gn)}.gsx-vis .s-rd{stroke:var(--k-rd)}" +
    ".gsx-vis .s-bl{stroke:var(--k-bl)}.gsx-vis .s-ln{stroke:var(--k-ln)}.gsx-vis .s-so{stroke:var(--k-so)}" +
    ".gsx-vis .w1{stroke-width:1}.gsx-vis .w15{stroke-width:1.5}.gsx-vis .w2{stroke-width:2}.gsx-vis .w3{stroke-width:3}" +
    ".gsx-vis .ln{fill:none;stroke-linejoin:round;stroke-linecap:round}" +
    ".gsx-vis .dr{stroke-dasharray:1 1;stroke-dashoffset:0}" +
    ".gsx-vis .hv{transform-box:view-box}" +
    ".gsx-vis .o0{transform-origin:0 50%}.gsx-vis .ob{transform-origin:50% 100%}.gsx-vis .oc{transform-origin:50% 50%}" +
    ".gsx-vis.is-still *{animation:none!important;transition:none!important}" +
    "@media (prefers-reduced-motion:reduce){.gsx-vis *{animation:none!important;transition:none!important}}";

  /* =========================================================
     1. tokens
     ========================================================= */
  def(
    "tokens",
    "A sentence split into seven short colored chunks, each roughly a piece of a word.",
    function () {
      var parts = ["Train", "ing", " is", " most", "ly", " arith", "metic"];
      var tints = ["f-t1", "f-t2", "f-t3", "f-t4", "f-t5", "f-t1", "f-t2"];
      var cw = 7.6;
      var x = 12;
      var out = T(130, 22, "one sentence, cut into chunks", "tm ts");
      parts.forEach(function (p, i) {
        var w = p.length * cw;
        out +=
          '<g class="tk" style="--i:' +
          i +
          ";--c:var(--k-t" +
          ((i % 5) + 1) +
          ')">' +
          rect(x, 42, w, 28, "f-t" + ((i % 5) + 1) + " s-ink w1") +
          T(x + w / 2, 60, p, "tm") +
          "</g>";
        x += w;
      });
      out += T(130, 96, "on average, 1 token = 3/4 of a word", "tm tb");
      out += T(130, 112, "(this split is only an example)", "tm ts");
      cur.css.push(
        scope(".tk") +
          "{transform:translateX(calc(var(--i)*3px));animation:xvtk 4s ease-in-out infinite}" +
          scope(".tk rect") +
          "{animation:xvtkc 4s ease-in-out infinite}" +
          kf("xvtk", [
            [0, "transform:translateX(0)"],
            [18, "transform:translateX(0)"],
            [38, "transform:translateX(calc(var(--i)*3px))"],
            [90, "transform:translateX(calc(var(--i)*3px))"],
            [100, "transform:translateX(0)"],
          ]) +
          kf("xvtkc", [
            [0, "fill:var(--k-so)"],
            [18, "fill:var(--k-so)"],
            [38, "fill:var(--c)"],
            [90, "fill:var(--c)"],
            [100, "fill:var(--k-so)"],
          ])
      );
      return out;
    }
  );

  /* =========================================================
     2. parameters (a model as a net of learned numbers)
     ========================================================= */
  def(
    "params",
    "Layers of nodes joined by lines of different thickness. Each line is one number the model has learned.",
    function () {
      var cols = [3, 5, 5, 3];
      var xs = [34, 94, 154, 214];
      var rand = rng(7);
      var out = "";
      var nodes = cols.map(function (n, c) {
        var arr = [];
        for (var i = 0; i < n; i++) arr.push([xs[c], 50 + (i - (n - 1) / 2) * 15]);
        return arr;
      });
      for (var c = 0; c < cols.length - 1; c++) {
        nodes[c].forEach(function (a) {
          nodes[c + 1].forEach(function (b) {
            var w = 0.5 + rand() * 2.5;
            out +=
              '<line class="pl s-cd" style="stroke-width:' +
              r1(w) +
              ";animation-delay:" +
              r1(c * 0.3) +
              's" x1="' +
              a[0] +
              '" y1="' +
              r1(a[1]) +
              '" x2="' +
              b[0] +
              '" y2="' +
              r1(b[1]) +
              '"/>';
          });
        });
      }
      nodes.forEach(function (col) {
        col.forEach(function (p) {
          out += rect(p[0] - 4, r1(p[1] - 4), 8, 8, "f-go s-ink w1");
        });
      });
      out += T(130, 108, "each line is one learned number", "tm tb");
      cur.css.push(
        scope(".pl") +
          "{opacity:.6;animation:xvpl 2.4s ease-in-out infinite}" +
          kf("xvpl", [
            [0, "opacity:.18"],
            [40, "opacity:.95"],
            [100, "opacity:.18"],
          ])
      );
      return out;
    }
  );

  /* =========================================================
     3. gpu (many small cores, same step)
     ========================================================= */
  def(
    "gpu",
    "A grid of small cells that light up in a diagonal wave, all doing the same kind of math at once.",
    function () {
      var out = "";
      for (var r = 0; r < 6; r++) {
        for (var c = 0; c < 24; c++) {
          out +=
            '<rect class="gc f-cy" x="' +
            (10 + c * 10) +
            '" y="' +
            (12 + r * 10) +
            '" width="8" height="8" style="animation-delay:' +
            r1((c + r) * 0.07 - 3) +
            's"/>';
        }
      }
      out += T(130, 92, "thousands of small cores", "tm tb");
      out += T(130, 108, "same math, many numbers at once", "tm ts");
      cur.css.push(
        scope(".gc") +
          "{animation:xvgc 2.4s ease-in-out infinite}" +
          kf("xvgc", [
            [0, "fill:var(--k-so)"],
            [30, "fill:var(--k-cy)"],
            [60, "fill:var(--k-so)"],
            [100, "fill:var(--k-so)"],
          ])
      );
      return out;
    }
  );

  /* =========================================================
     4. H100 (package: die plus memory)
     ========================================================= */
  def(
    "h100",
    "A chip drawn as a large central die with memory blocks on both sides and data moving between them.",
    function () {
      var out = "";
      var ys = [12, 41, 70];
      ys.forEach(function (y, i) {
        out += rect(10, y, 42, 22, "f-t2 s-ink w15") + T(31, y + 15, "mem", "tm");
        out += rect(208, y, 42, 22, "f-t2 s-ink w15") + T(229, y + 15, "mem", "tm");
        out += line(52, y + 11, 76, y + 11, "s-ink w1");
        out += line(184, y + 11, 208, y + 11, "s-ink w1");
        out += at(52, y + 11, rect(-3, -3, 6, 6, "f-cd hl" + i)) + at(208, y + 11, rect(-3, -3, 6, 6, "f-cd hr" + i));
      });
      out += rect(76, 12, 108, 80, "f-bl s-ink w2");
      out += rect(82, 18, 96, 68, "f-no s-cy w1 hp");
      out += T(130, 60, "H100", "tm tw z tb");
      out += T(130, 108, "80 GB memory, up to 700 W", "tm tb");
      for (var i = 0; i < 3; i++) {
        var d = i * 0.35;
        cur.css.push(
          scope(".hl" + i) +
            "{animation:xvhl 1.2s linear infinite;animation-delay:" +
            d +
            "s}" +
            scope(".hr" + i) +
            "{animation:xvhr 1.2s linear infinite;animation-delay:" +
            d +
            "s}"
        );
      }
      cur.css.push(
        kf("xvhl", [
          [0, "transform:translateX(0);opacity:0"],
          [15, "opacity:1"],
          [85, "opacity:1"],
          [100, "transform:translateX(22px);opacity:0"],
        ]) +
          kf("xvhr", [
            [0, "transform:translateX(0);opacity:0"],
            [15, "opacity:1"],
            [85, "opacity:1"],
            [100, "transform:translateX(-22px);opacity:0"],
          ]) +
          scope(".hp") +
          "{animation:xvhp 1.6s ease-in-out infinite}" +
          kf("xvhp", [
            [0, "opacity:.25"],
            [50, "opacity:1"],
            [100, "opacity:.25"],
          ])
      );
      return out;
    }
  );

  /* =========================================================
     5. GPU-hour
     ========================================================= */
  def(
    "gpuhour",
    "Three GPUs times one hour on a clock makes three GPU-hours. Three squares fill as the clock hand goes around three times.",
    function () {
      var out = "";
      [14, 44, 74].forEach(function (x) {
        out += rect(x, 14, 24, 24, "f-bl s-ink w15");
        out += rect(x + 5, 19, 14, 14, "f-cy");
      });
      out += T(110, 31, "×", "tm z");
      out += '<circle cx="138" cy="26" r="16" class="f-pa s-ink w2"/>';
      out += line(138, 26, 138, 14, "s-ink w2 hand hv", 'style="transform-origin:138px 26px"');
      out += T(170, 31, "=", "tm z");
      [186, 210, 234].forEach(function (x, i) {
        out += rect(x, 14, 20, 24, "f-go s-ink w15 gh gh" + i);
      });
      out += T(130, 66, "3 GPUs × 1 hour = 3 GPU-hours", "tm tb");
      out += T(130, 84, "the same work as 1 GPU for 3 hours", "tm ts");
      out += rect(14, 96, 232, 1, "f-ln");
      out += T(130, 112, "run time is hours divided by GPUs", "tm ts");
      loop(".hand", 1, [[0, "transform:rotate(0)"], [100, "transform:rotate(360deg)"]], "linear");
      [0, 1, 2].forEach(function (i) {
        an(".gh" + i, 3, i * 33 + 2, i * 33 + 10, "fill:var(--k-so)", "fill:var(--k-go)", "ease-out");
      });
      return out;
    }
  );

  /* =========================================================
     6. FLOP
     ========================================================= */
  def(
    "flop",
    "A multiplication of two decimal numbers counts as one floating-point operation. Below it, a row of squares lights up to show many such operations per second.",
    function () {
      var out = "";
      out += rect(12, 16, 52, 26, "f-t5 s-ink w15 fa") + T(38, 34, "3.14", "tm tb");
      out += T(78, 35, "×", "tm z");
      out += rect(92, 16, 44, 26, "f-t5 s-ink w15 fb") + T(114, 34, "2.7", "tm tb");
      out += T(150, 35, "=", "tm z");
      out += rect(164, 16, 84, 26, "f-t2 s-ink w15 fc") + T(206, 34, "8.478", "tm tb");
      out += T(130, 62, "one multiply (or add) = one FLOP", "tm tb");
      for (var i = 0; i < 26; i++) {
        out +=
          '<rect class="ty f-go" x="' +
          (10 + i * 9.6) +
          '" y="74" width="7.6" height="10" style="animation-delay:' +
          r1(i * 0.07) +
          's"/>';
      }
      out += T(130, 106, "FLOP/s = how many per second", "tm ts");
      an(".fa", 3.2, 0, 8, "transform:translateX(-14px);opacity:0", "transform:none;opacity:1");
      an(".fb", 3.2, 4, 12, "transform:translateX(14px);opacity:0", "transform:none;opacity:1");
      an(".fc", 3.2, 14, 22, "transform:scale(.6);opacity:0", "transform:none;opacity:1");
      cur.css.push(
        scope(".fc") + "{transform-origin:50% 50%}" +
          scope(".ty") +
          "{animation:xvty 1.8s ease-in-out infinite}" +
          kf("xvty", [
            [0, "opacity:.2"],
            [25, "opacity:1"],
            [60, "opacity:.2"],
            [100, "opacity:.2"],
          ])
      );
      return out;
    }
  );

  /* =========================================================
     7. 6ND
     ========================================================= */
  def(
    "sixnd",
    "A forward arrow that costs two operations and a backward arrow that costs four, adding up to six.",
    function () {
      var out = "";
      out += T(8, 20, "forward", "tb");
      out += line(66, 30, 232, 30, "s-ink w2 a1 o0");
      out += arrowHead(232, 30, 1, "f-ink a1h");
      out += rect(104, 23, 14, 14, "f-go s-ink w15 oc p1") + rect(160, 23, 14, 14, "f-go s-ink w15 oc p2");
      out += T(8, 62, "backward", "tb");
      out += line(232, 70, 66, 70, "s-ink w2 a2");
      out += arrowHead(66, 70, -1, "f-ink a2h");
      [86, 122, 158, 194].forEach(function (x, i) {
        out += rect(x, 63, 14, 14, "f-cy s-ink w15 oc q" + (i + 1));
      });
      out += T(130, 102, "2 + 4 = 6 per parameter per token", "tm tb sm");
      an(".a1", 4, 0, 10, "transform:scaleX(0)", "transform:none", "linear");
      an(".a1h", 4, 8, 10, "opacity:0", "opacity:1");
      an(".p1", 4, 10, 16, "transform:scale(0)", "transform:none");
      an(".p2", 4, 18, 24, "transform:scale(0)", "transform:none");
      cur.css.push(scope(".a2") + "{transform-origin:100% 50%}");
      an(".a2", 4, 30, 40, "transform:scaleX(0)", "transform:none", "linear");
      an(".a2h", 4, 38, 41, "opacity:0", "opacity:1");
      [1, 2, 3, 4].forEach(function (n) {
        an(".q" + n, 4, 38 + n * 7, 44 + n * 7, "transform:scale(0)", "transform:none");
      });
      an(".sm", 4, 76, 84, "opacity:0", "opacity:1");
      return out;
    }
  );

  /* =========================================================
     8. peak speed (spec sheet)
     ========================================================= */
  def(
    "peak",
    "Two rows of time slots. The spec sheet row is busy in every slot. The real run row has gaps where the GPU waits for data.",
    function () {
      var real = [1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1];
      var out = T(10, 16, "spec sheet: busy every instant", "tb");
      var i;
      for (i = 0; i < 24; i++) out += rect(10 + i * 10, 22, 8, 14, "f-cd s-ink w1 pc pc" + i);
      out += T(10, 58, "real run: waits on memory and network", "tb");
      for (i = 0; i < 24; i++) {
        out += rect(10 + i * 10, 64, 8, 14, (real[i] ? "f-cd" : "f-so") + " s-ink w1 pc pc" + i);
      }
      out += rect(10, 22, 2, 56, "f-rd ph", 'style="opacity:0"');
      out += rect(10, 98, 8, 8, "f-cd s-ink w1") + T(24, 106, "computing", "");
      out += rect(98, 98, 8, 8, "f-so s-ink w1") + T(112, 106, "waiting", "");
      for (i = 0; i < 24; i++) an(".pc" + i, 4.5, i * 3.6, i * 3.6 + 1.5, "opacity:.12", "opacity:1", "linear");
      loop(".ph", 4.5, [[0, "transform:translateX(0);opacity:1"], [88, "transform:translateX(238px);opacity:1"], [94, "transform:translateX(238px);opacity:0"], [100, "transform:translateX(238px);opacity:0"]], "linear");
      return out;
    }
  );

  /* =========================================================
     9. MFU
     ========================================================= */
  def(
    "mfu",
    "A speedometer whose needle swings up, overshoots, and settles at about forty percent of the scale. The top of the scale is the spec sheet peak.",
    function () {
      var cx = 130;
      var cy = 94;
      var R = 62;
      var out = T(130, 14, "share of top speed actually used", "tm ts");
      out += '<path d="' + arc(cx, cy, R, 0, 1) + '" pathLength="1" class="ln s-so" style="stroke-width:12"/>';
      out += '<path d="' + arc(cx, cy, R, 0, 1) + '" pathLength="1" class="ln s-cy gfill" style="stroke-width:12;stroke-dasharray:.4 1"/>';
      for (var i = 0; i <= 4; i++) {
        var a = Math.PI * (1 - i / 4);
        out += line(
          r1(cx + (R + 9) * Math.cos(a)),
          r1(cy - (R + 9) * Math.sin(a)),
          r1(cx + (R + 14) * Math.cos(a)),
          r1(cy - (R + 14) * Math.sin(a)),
          "s-ink w1"
        );
      }
      out += T(cx - R, 112, "0", "tm ts");
      out += T(cx + R, 112, "peak", "tm ts");
      out += T(cx, 114, "~40%", "tm z tb");
      out += line(cx, cy, cx, cy - R + 6, "s-ink w3 ndl hv", "style=\"transform-origin:" + cx + "px " + cy + "px;transform:rotate(-18deg)\"");
      out += '<circle cx="' + cx + '" cy="' + cy + '" r="5" class="f-ink"/>';
      var ps = [0, 62, 33, 47, 38, 41, 40];
      var stops = [];
      var arcStops = [];
      var pcts = [0, 24, 40, 54, 68, 82, 100];
      ps.forEach(function (p, i) {
        stops.push([pcts[i], "transform:rotate(" + r1(-90 + 180 * (p / 100)) + "deg)"]);
        arcStops.push([pcts[i], "stroke-dasharray:" + (p / 100 || 0.001) + " 1"]);
      });
      loop(".ndl", 3.6, stops, "ease-in-out");
      loop(".gfill", 3.6, arcStops, "ease-in-out");
      return out;
    }
  );

  /* =========================================================
     10. training run (loss curve)
     ========================================================= */
  def(
    "trainrun",
    "A curve that starts high and bends down as the model reads more text, with a dot tracing it.",
    function () {
      var rand = rng(11);
      var pts = [];
      for (var i = 0; i <= 56; i++) {
        var u = i / 56;
        var y = 24 + 56 * (1 - Math.exp(-3.4 * u)) + (rand() - 0.5) * 5 * (1 - u * 0.5);
        pts.push([30 + u * 214, y]);
      }
      var out = line(28, 14, 28, 94, "s-ink w1") + line(28, 94, 248, 94, "s-ink w1");
      out += T(4, 12, "loss", "ts");
      out += T(138, 110, "text read so far", "tm ts");
      out += T(244, 38, "less wrong as it reads more", "te tb");
      out += poly(pts, "ln s-cd w2 dr tl");
      out += rect(-3, -3, 6, 6, "f-go s-ink w1 td");
      draw(".tl", 4, 4, 82);
      var sample = pts.filter(function (_, i) {
        return i % 4 === 0;
      });
      follow(".td", 4, sample, 4, 82);
      cur.css.push(scope(".td") + "{transform:translate(" + r1(pts[pts.length - 1][0]) + "px," + r1(pts[pts.length - 1][1]) + "px)}");
      return out;
    }
  );

  /* =========================================================
     11. cost per token
     ========================================================= */
  def(
    "costpertoken",
    "One token on the left, then three blocks that add up to its cost: GPU time, electricity and wear on the hardware.",
    function () {
      var out = rect(10, 38, 42, 28, "f-t5 s-ink w15") + T(31, 56, "token", "tm tb");
      out += T(61, 57, "=", "tm z");
      var boxes = [
        ["GPU time", 66, "f-t1"],
        ["power", 130, "f-t2"],
        ["wear", 194, "f-t4"],
      ];
      boxes.forEach(function (b, i) {
        out += '<g class="cb cb' + i + '">' + rect(b[1], 38, 56, 28, b[2] + " s-ink w15") + T(b[1] + 28, 56, b[0], "tm") + "</g>";
      });
      out += T(126, 57, "+", "tm z ps ps0");
      out += T(190, 57, "+", "tm z ps ps1");
      out += line(66, 78, 250, 78, "s-ink w2 br o0");
      out += T(158, 96, "cost of one token = the sum", "tm tb");
      out += T(158, 112, "hardware wear spread over its life", "tm ts");
      [0, 1, 2].forEach(function (i) {
        an(".cb" + i, 3.6, 4 + i * 14, 14 + i * 14, "transform:translateY(-16px);opacity:0", "transform:none;opacity:1");
      });
      an(".ps0", 3.6, 14, 24, "opacity:0", "opacity:1");
      an(".ps1", 3.6, 28, 38, "opacity:0", "opacity:1");
      an(".br", 3.6, 50, 66, "transform:scaleX(0)", "transform:none", "ease-out");
      return out;
    }
  );

  /* =========================================================
     12. electricity and PUE
     ========================================================= */
  def(
    "pue",
    "A datacenter building with heat rising off its roof, next to a bar showing computers at 1.0 and cooling and other overhead at 0.2.",
    function () {
      var out = "";
      out += rect(10, 44, 100, 56, "f-so s-ink w2");
      out += poly([[6, 44], [60, 28], [114, 44]], "ln s-ink w2 f-no").replace(' pathLength="1"', "");
      for (var r = 0; r < 2; r++) {
        for (var c = 0; c < 5; c++) out += rect(18 + c * 18, 54 + r * 20, 12, 14, "f-wd");
      }
      out += '<g class="fan hv" style="transform-origin:60px 36px"><line x1="52" y1="36" x2="68" y2="36" class="s-ink w2"/><line x1="60" y1="28" x2="60" y2="44" class="s-ink w2"/></g>';
      [34, 60, 86].forEach(function (x, i) {
        out += '<path d="M' + x + " 24q4 -5 0 -10t0 -10\" class=\"ln s-rd w2 ht ht" + i + '"/>';
      });
      out += rect(150, 38, 40, 60, "f-cy s-ink w15");
      out += rect(150, 26, 40, 12, "f-rd s-ink w15 cl");
      out += T(196, 72, "computers", "tb");
      out += T(196, 34, "cooling", "tr tb");
      out += T(170, 112, "PUE 1.2 = 20% extra", "tm tb");
      loop(".fan", 1.2, [[0, "transform:rotate(0)"], [100, "transform:rotate(360deg)"]], "linear");
      [0, 1, 2].forEach(function (i) {
        loop(
          ".ht" + i,
          2.4,
          [[0, "transform:translateY(8px);opacity:0"], [30, "opacity:1"], [100, "transform:translateY(-8px);opacity:0"]],
          "ease-out",
          "animation-delay:" + i * 0.5 + "s"
        );
      });
      an(".cl", 3.2, 10, 30, "transform:scaleY(0)", "transform:none");
      cur.css.push(scope(".cl") + "{transform-origin:50% 100%}");
      return out;
    }
  );

  /* =========================================================
     13. amortization
     ========================================================= */
  def(
    "amort",
    "One purchase price is cut into equal slices, one slice for each year the hardware is expected to last.",
    function () {
      var out = rect(20, 14, 220, 20, "f-go s-ink w15") + T(130, 29, "price paid once", "tm tb");
      for (var i = 0; i < 4; i++) {
        var x = 20 + i * 56;
        out += '<g class="sl sl' + i + '">' + rect(x, 52, 52, 20, "f-t2 s-ink w15") + "</g>";
        out += T(x + 26, 88, "year " + (i + 1), "tm ts");
      }
      out += T(130, 112, "price ÷ years of use = cost per year", "tm tb");
      for (var j = 0; j < 4; j++) an(".sl" + j, 4, 8 + j * 14, 20 + j * 14, "transform:translateY(-18px);opacity:0", "transform:none;opacity:1");
      return out;
    }
  );

  /* =========================================================
     14. datacenter
     ========================================================= */
  def(
    "datacenter",
    "A hall of server racks with blinking lights and network cables, with data packets moving along the cables.",
    function () {
      var rand = rng(5);
      var out = rect(6, 12, 248, 88, "f-so s-ink w2");
      for (var i = 0; i < 8; i++) {
        var x = 16 + i * 29;
        out += rect(x, 22, 22, 56, "f-wd s-ink w1");
        for (var l = 0; l < 5; l++) {
          out +=
            '<rect class="led ' +
            (rand() > 0.5 ? "f-gn" : "f-go") +
            '" x="' +
            (x + 4) +
            '" y="' +
            (27 + l * 10) +
            '" width="14" height="4" style="animation-delay:-' +
            r1(rand() * 1.6) +
            's"/>';
        }
      }
      out += line(16, 90, 244, 90, "s-ink w2");
      out += at(16, 88, rect(0, 0, 8, 4, "f-cy pk")) + at(16, 88, rect(0, 0, 8, 4, "f-cy pk pk2"));
      out += T(130, 114, "one building, one network", "tm tb");
      cur.css.push(
        scope(".led") +
          "{animation:xvled 1.6s steps(1) infinite}" +
          kf("xvled", [[0, "opacity:1"], [50, "opacity:.25"], [100, "opacity:1"]]) +
          scope(".pk2") +
          "{animation-delay:-1.4s}"
      );
      loop(".pk", 2.8, [[0, "transform:translateX(0)"], [100, "transform:translateX(212px)"]], "linear");
      return out;
    }
  );

  /* =========================================================
     15. transistor
     ========================================================= */
  def(
    "transistor",
    "A transistor as a switch. When the gate is on, electrons flow from source to drain through the channel. When it is off, nothing flows.",
    function () {
      var out = rect(14, 60, 54, 24, "f-t5 s-ink w15") + T(41, 76, "in", "tm tb");
      out += rect(192, 60, 54, 24, "f-t5 s-ink w15") + T(219, 76, "out", "tm tb");
      out += rect(68, 60, 124, 24, "f-so s-ink w15");
      out += rect(88, 30, 84, 14, "f-gn s-ink w15 gt");
      out += rect(88, 44, 84, 6, "f-ln");
      out += T(130, 24, "gate", "tm ts");
      out += T(130, 40, "ON", "tm tb gon");
      out += T(130, 40, "OFF", "tm tb tw goff", 'style="opacity:0"');
      out += '<g class="el">';
      [0, 1, 2, 3].forEach(function (i) {
        out += '<circle r="3.5" cx="80" cy="72" class="f-cd e" style="transform:translateX(' + i * 26 + "px);animation-delay:-" + r1(i * 0.2) + 's"/>';
      });
      out += "</g>";
      out += T(130, 104, "a switch with no moving parts", "tm tb");
      loop(".el", 3.6, [[0, "opacity:0"], [8, "opacity:0"], [14, "opacity:1"], [56, "opacity:1"], [62, "opacity:0"], [100, "opacity:0"]], "linear");
      loop(".gt", 3.6, [[0, "fill:var(--k-rd)"], [8, "fill:var(--k-rd)"], [14, "fill:var(--k-gn)"], [56, "fill:var(--k-gn)"], [62, "fill:var(--k-rd)"], [100, "fill:var(--k-rd)"]], "ease-in-out");
      loop(".gon", 3.6, [[0, "opacity:0"], [8, "opacity:0"], [14, "opacity:1"], [56, "opacity:1"], [62, "opacity:0"], [100, "opacity:0"]], "linear");
      loop(".goff", 3.6, [[0, "opacity:1"], [8, "opacity:1"], [14, "opacity:0"], [56, "opacity:0"], [62, "opacity:1"], [100, "opacity:1"]], "linear");
      cur.css.push(
        scope(".e") +
          "{animation:xvel .8s linear infinite}" +
          kf("xvel", [[0, "transform:translateX(0)"], [100, "transform:translateX(104px)"]])
      );
      return out;
    }
  );

  /* =========================================================
     16. lithography
     ========================================================= */
  def(
    "litho",
    "Light shines through gaps in a mask, a lens shrinks the pattern, and thin lines are printed on a wafer.",
    function () {
      var out = "";
      for (var x = 16; x <= 214; x += 12) out += line(x, 10, x, 33, "s-cy w15 lt");
      var cx = [40, 90, 140, 190];
      var blocks = [[8, 33], [47, 83], [97, 133], [147, 183], [197, 222]];
      blocks.forEach(function (b) {
        out += rect(b[0], 33, b[1] - b[0], 7, "f-ink");
      });
      out += T(228, 40, "mask", "ts");
      out += '<ellipse cx="115" cy="62" rx="100" ry="5" class="f-t1 s-ink w15"/>';
      out += T(228, 66, "lens", "ts");
      cx.forEach(function (c) {
        out += '<path d="M' + (c - 7) + " 41L" + (c + 7) + " 41L" + (c + 3) + " 84L" + (c - 3) + ' 84Z" class="f-cy bm"/>';
      });
      out += rect(8, 90, 214, 12, "f-so s-ink w15");
      cx.forEach(function (c) {
        out += rect(c - 3, 84, 6, 6, "f-go s-ink w1 ob pl");
      });
      out += T(228, 100, "wafer", "ts");
      out += T(115, 116, "light + mask + lens = lines", "tm tb");
      cur.css.push(
        scope(".lt") +
          "{stroke-dasharray:3 3;animation:xvlt .5s linear infinite}" +
          kf("xvlt", [[0, "stroke-dashoffset:0"], [100, "stroke-dashoffset:-6"]]) +
          scope(".bm") +
          "{opacity:.55}"
      );
      an(".pl", 3.6, 10, 30, "transform:scaleY(0)", "transform:none");
      return out;
    }
  );

  /* =========================================================
     17. EUV
     ========================================================= */
  def(
    "euv",
    "Two beams. In air, the extreme ultraviolet beam is absorbed after a short distance. In a vacuum, it bounces off mirrors and reaches the wafer.",
    function () {
      var out = T(10, 16, "in air: absorbed", "tb");
      out += line(14, 28, 246, 28, "s-so w1");
      out += rect(6, 24, 10, 8, "f-bl");
      out += '<path d="M16 28L78 28" pathLength="1" class="ln s-bl w3 ba"/>';
      [0, 1, 2].forEach(function (i) {
        out += '<circle r="2.5" cx="' + (90 + i * 10) + '" cy="' + (22 + (i % 2) * 12) + '" class="f-ln mo mo' + i + '"/>';
      });
      out += T(10, 56, "in a vacuum: mirrors", "tb");
      var pts = [[16, 100], [60, 100], [100, 78], [150, 100], [190, 78], [236, 78]];
      out += '<path d="' + pathD(pts) + '" class="ln s-so w1"/>';
      out += '<path d="' + pathD(pts) + '" pathLength="1" class="ln s-bl w3 dr bv"/>';
      [[60, 100], [100, 78], [150, 100], [190, 78]].forEach(function (p) {
        out += rect(p[0] - 6, p[1] - 2, 12, 4, "f-ink");
      });
      out += rect(6, 96, 10, 8, "f-bl");
      out += rect(236, 74, 14, 8, "f-go s-ink w1");
      out += T(130, 116, "13.5 nm light, no lenses", "tm tb");
      cur.css.push(
        scope(".ba") +
          "{animation:xvba 4s ease-out infinite;stroke-dasharray:.27 1}" +
          kf("xvba", [[0, "stroke-dasharray:0 1;opacity:1"], [24, "stroke-dasharray:.27 1;opacity:1"], [80, "stroke-dasharray:.27 1;opacity:1"], [92, "stroke-dasharray:.27 1;opacity:0"], [100, "stroke-dasharray:0 1;opacity:0"]]) +
          scope(".mo") +
          "{animation:xvmo 4s ease-in-out infinite}" +
          kf("xvmo", [[0, "opacity:.2"], [24, "opacity:1"], [70, "opacity:1"], [100, "opacity:.2"]])
      );
      draw(".bv", 4, 4, 70);
      return out;
    }
  );

  /* =========================================================
     18. wavelength
     ========================================================= */
  function wave(y, amp, period, cls, sel) {
    var pts = [];
    var step = Math.max(1, period / 16);
    for (var x = -period; x <= W + period; x += step) {
      pts.push([x, y - amp * Math.sin((2 * Math.PI * x) / period)]);
    }
    return '<path d="' + pathD(pts) + '" class="ln ' + cls + " " + sel + '"/>';
  }
  def(
    "wavelength",
    "Two waves scrolling past. The first has a long wavelength and the second, used for the newest chips, a much shorter one.",
    function () {
      var out = T(10, 16, "193 nm light (older machines)", "tb");
      out += wave(38, 12, 48, "s-cy w2", "wa");
      out += T(10, 64, "13.5 nm light (EUV)", "tb");
      out += wave(84, 12, 9.6, "s-bl w2", "wb");
      out += T(130, 114, "drawn 5x apart, really about 14x", "tm ts");
      loop(".wa", 2.4, [[0, "transform:translateX(0)"], [100, "transform:translateX(-48px)"]], "linear");
      loop(".wb", 2.4, [[0, "transform:translateX(0)"], [100, "transform:translateX(-9.6px)"]], "linear");
      cur.css.push(scope(".wa,.wb") + "{transform-box:view-box}");
      return out;
    }
  );

  /* =========================================================
     19. numerical aperture
     ========================================================= */
  def(
    "na",
    "A lens focusing light. A wider cone of light, which means a higher numerical aperture, focuses to a smaller spot.",
    function () {
      var out = '<ellipse cx="130" cy="30" rx="56" ry="5" class="f-t1 s-ink w15"/>';
      out += T(196, 34, "lens", "ts");
      out += '<path d="M76 32L184 32L130 88Z" class="f-cy s-cd w15 cone" style="transform-origin:130px 88px;transform-box:view-box;opacity:.45"/>';
      out += rect(30, 92, 200, 6, "f-so s-ink w1");
      out += rect(126, 90, 8, 5, "f-go s-ink w1 spot");
      out += T(14, 20, "NA 0.33", "tb n1");
      out += T(14, 20, "NA 0.55", "tb n2");
      out += T(130, 114, "wider cone, smaller spot", "tm tb");
      an(".cone", 4, 30, 48, "transform:scaleX(.6)", "transform:none", "ease-in-out");
      an(".spot", 4, 30, 48, "transform:scaleX(1.67)", "transform:none", "ease-in-out");
      an(".n1", 4, 36, 42, "opacity:1", "opacity:0", "linear");
      an(".n2", 4, 36, 42, "opacity:0", "opacity:1", "linear");
      cur.css.push(scope(".n1") + "{opacity:0}");
      return out;
    }
  );

  /* =========================================================
     20. k1
     ========================================================= */
  def(
    "k1",
    "The formula smallest feature equals k1 times wavelength divided by numerical aperture. A bar shrinks as each of the three knobs improves in turn.",
    function () {
      var out = rect(88, 10, 30, 24, "f-t2 hb hb1") + rect(146, 10, 24, 24, "f-t2 hb hb2") + rect(196, 10, 34, 24, "f-t2 hb hb3");
      out += T(22, 28, "size =", "z tb");
      out += T(92, 28, "k1", "z tb");
      out += T(124, 28, "×", "z");
      out += T(150, 28, "λ", "z tb");
      out += T(178, 28, "/", "z");
      out += T(200, 28, "NA", "z tb");
      out += rect(20, 52, 220, 12, "f-so s-ink w1");
      out += rect(20, 52, 220, 12, "f-cd bar o0", 'style="transform:scaleX(.3)"');
      out += T(130, 86, "tricks in masks and resist", "tm tb c1", 'style="opacity:0"');
      out += T(130, 86, "shorter wavelength", "tm tb c2", 'style="opacity:0"');
      out += T(130, 86, "wider lens", "tm tb c3");
      out += T(130, 108, "smaller size = finer lines", "tm ts");
      loop(".bar", 6, [[0, "transform:scaleX(1)"], [12, "transform:scaleX(1)"], [24, "transform:scaleX(.72)"], [40, "transform:scaleX(.72)"], [52, "transform:scaleX(.45)"], [66, "transform:scaleX(.45)"], [78, "transform:scaleX(.3)"], [94, "transform:scaleX(.3)"], [100, "transform:scaleX(1)"]], "ease-in-out");
      function pulse(sel, a, b) {
        loop(sel, 6, [[0, "opacity:0"], [a, "opacity:0"], [a + 4, "opacity:1"], [b, "opacity:1"], [b + 3, "opacity:0"], [100, "opacity:0"]], "linear");
      }
      pulse(".hb1,.c1", 14, 38);
      pulse(".hb2,.c2", 42, 64);
      pulse(".hb3,.c3", 68, 92);
      return out;
    }
  );

  /* =========================================================
     21. equation and units
     ========================================================= */
  def(
    "equation",
    "The equation time equals work divided by speed, written with units. The unit FLOP appears on top and bottom and cancels, leaving seconds.",
    function () {
      var x0 = 26;
      var cw = 9;
      var out = T(x0, 26, "time = work / speed", "z tb");
      out += T(x0, 56, "[s] = [FLOP] / [FLOP/s]", "z tb");
      out += line(x0 + 7 * cw, 51, x0 + 11 * cw, 51, "s-rd w2 o0 st1");
      out += line(x0 + 16 * cw, 51, x0 + 20 * cw, 51, "s-rd w2 o0 st2");
      out += T(x0, 86, "left: [s] (seconds)", "z tb lv");
      out += T(130, 108, "units that do not cancel mean a bug", "tm ts");
      an(".st1", 4.5, 18, 28, "transform:scaleX(0)", "transform:none", "ease-out");
      an(".st2", 4.5, 30, 40, "transform:scaleX(0)", "transform:none", "ease-out");
      an(".lv", 4.5, 44, 54, "opacity:0", "opacity:1");
      return out;
    }
  );

  /* =========================================================
     22. rule of thumb
     ========================================================= */
  def(
    "rule",
    "Two dots, one from the whole map and one from a one-line rule, both landing inside the same shaded band around the reported number.",
    function () {
      var out = rect(172, 10, 44, 66, "f-t2 s-go w1");
      out += line(194, 10, 194, 80, "s-go w1", 'stroke-dasharray="3 2"');
      out += T(194, 94, "reported", "tm tb");
      out += T(8, 30, "the whole map", "tb");
      out += line(104, 34, 246, 34, "s-so w2");
      out += at(188, 34, rect(-4, -4, 8, 8, "f-cd s-ink w1 d1"));
      out += T(8, 62, "one line of arithmetic", "tb ");
      out += line(158, 66, 246, 66, "s-so w2");
      out += at(201, 66, rect(-4, -4, 8, 8, "f-go s-ink w1 d2"));
      out += T(130, 112, "both land within about 22%", "tm ts");
      loop(".d1", 4, [[0, "transform:translateX(-84px)"], [38, "transform:translateX(0)"], [93, "transform:translateX(0)"], [100, "transform:translateX(-84px)"]], "ease-out");
      loop(".d2", 4, [[0, "transform:translateX(-43px)"], [46, "transform:translateX(0)"], [93, "transform:translateX(0)"], [100, "transform:translateX(-43px)"]], "ease-out");
      return out;
    }
  );

  /* =========================================================
     23. published runs (27 runs)
     ========================================================= */
  def(
    "runs27",
    "A scatter of 27 dots around a diagonal line of perfect agreement, most of them inside a shaded band of about 22 percent.",
    function () {
      var rand = rng(21);
      function gauss() {
        return (rand() + rand() + rand() + rand() - 2) * 1.73;
      }
      var X0 = 22;
      var Y0 = 96;
      var S = 70;
      var SX = 100;
      var band = [];
      var us = [0.08, 0.5, 1];
      var top = [];
      var bot = [];
      us.forEach(function (u) {
        top.push([X0 + SX * u, Y0 - S * u * 1.22]);
        bot.unshift([X0 + SX * u, Y0 - S * u * 0.78]);
      });
      band = top.concat(bot);
      var out = '<path d="' + pathD(band) + 'Z" class="f-t2"/>';
      out += line(X0, Y0, X0 + SX, Y0 - S, "s-go w1", 'stroke-dasharray="3 2"');
      out += line(X0, 12, X0, Y0, "s-ink w1") + line(X0, Y0, X0 + SX + 4, Y0, "s-ink w1");
      for (var i = 0; i < 27; i++) {
        var u = 0.1 + 0.85 * ((i * 0.618) % 1);
        var e = gauss() * 0.13;
        var yy = Math.min(Y0 - 2, Math.max(12, Y0 - S * u * (1 + e)));
        out += rect(r1(X0 + SX * u - 2.5), r1(yy - 2.5), 5, 5, "f-cd s-ink w1 oc rd rd" + i);
        an(".rd" + i, 4, 4 + i * 2, 9 + i * 2, "transform:scale(0)", "transform:none");
      }
      out += T(160, 40, "27", "zz tb");
      out += T(160, 58, "real runs,", "");
      out += T(160, 71, "one dot each", "");
      out += T(160, 87, "band: within", "ts");
      out += T(160, 99, "about 22%", "ts");
      out += T(8, 114, "dot positions are illustrative", "ts");
      return out;
    }
  );

  /* =========================================================
     24. synchronous training
     ========================================================= */
  def(
    "sync",
    "Two sites working in lockstep. The faster site finishes each step early and then sits idle until the slower site catches up.",
    function () {
      var out = T(6, 36, "site A", "tb") + T(6, 76, "site B", "tb");
      var P = 46;
      var x0 = 52;
      for (var r = 0; r < 4; r++) {
        var s = x0 + r * P;
        var a = r * 22 + 2;
        out += rect(s, 26, 14, 14, "f-cy s-ink w1 o0 ra" + r);
        out += rect(s + 14, 26, 20, 14, "f-ha s-ln w1 o0 rw" + r);
        out += rect(s, 66, 34, 14, "f-cy s-ink w1 o0 rb" + r);
        out += line(s + 37, 18, s + 37, 90, "s-rd w15 ob rs" + r, 'stroke-dasharray="3 2"');
        an(".ra" + r, 5, a, a + 4, "transform:scaleX(0)", "transform:none", "linear");
        an(".rw" + r, 5, a + 4, a + 13, "transform:scaleX(0)", "transform:none", "linear");
        an(".rb" + r, 5, a, a + 13, "transform:scaleX(0)", "transform:none", "linear");
        an(".rs" + r, 5, a + 13, a + 16, "transform:scaleY(0)", "transform:none", "linear");
      }
      out += rect(10, 100, 8, 8, "f-cy s-ink w1") + T(22, 108, "working", "");
      out += rect(84, 100, 8, 8, "f-ha s-ln w1") + T(96, 108, "waiting for the slower site", "");
      return out;
    }
  );

  /* =========================================================
     25. weight averaging
     ========================================================= */
  def(
    "wavg",
    "Two noisy lines, one per site, that are pulled back together at regular marks. Their average is a calmer line.",
    function () {
      var rand = rng(33);
      var segs = 6;
      var per = 16;
      var A = [];
      var B = [];
      var M = [];
      var c = 28;
      var x = 14;
      var dx = 232 / (segs * per);
      for (var s = 0; s < segs; s++) {
        var da = 0;
        var db = 0;
        for (var i = 0; i <= per; i++) {
          if (i > 0) {
            da += (rand() - 0.5) * 11;
            db += (rand() - 0.5) * 11;
            c += 0.3;
          }
          A.push([x, c + da]);
          B.push([x, c + db]);
          M.push([x, c + (da + db) / 2]);
          x += dx;
        }
        x -= dx;
        c += (da + db) / 2;
      }
      var out = "";
      for (var k = 0; k <= segs; k++) out += line(r1(14 + (232 / segs) * k), 22, r1(14 + (232 / segs) * k), 92, "s-so w1", 'stroke-dasharray="2 2"');
      out += poly(A, "ln s-bl w15 dr wa1") + poly(B, "ln s-go w15 dr wa2") + poly(M, "ln s-gn w3 dr wa3");
      out += rect(10, 4, 8, 8, "f-bl") + T(22, 12, "site A", "");
      out += rect(76, 4, 8, 8, "f-go") + T(88, 12, "site B", "");
      out += rect(142, 4, 8, 8, "f-gn") + T(154, 12, "average", "");
      out += T(130, 108, "pulled together at each dotted mark", "tm tb");
      draw(".wa1,.wa2,.wa3", 4.2, 4, 80);
      return out;
    }
  );

  /* =========================================================
     26. learning rate
     ========================================================= */
  def(
    "lr",
    "Two valleys. In the first, a ball takes big steps and keeps jumping from side to side. In the second, it takes tiny steps and barely moves.",
    function () {
      function yAt(u) {
        return 36 + 52 * (1 - u * u);
      }
      function bowl(x0, label) {
        var pts = [];
        for (var u = -1; u <= 1.001; u += 0.1) pts.push([x0 + 55 + u * 52, yAt(u)]);
        return poly(pts, "ln s-ink w2").replace(' pathLength="1"', "") + T(x0 + 2, 18, label, "tb");
      }
      var out = bowl(8, "big steps") + bowl(142, "small steps");
      var big = [-0.9, 0.85, -0.8, 0.76, -0.72, 0.68];
      var small = [-0.9, -0.86, -0.82, -0.78, -0.74, -0.7];
      function ball(list, x0, cls) {
        var o = "";
        var stops = [];
        var pos = list.map(function (u) {
          return [x0 + 55 + u * 52, yAt(u) - 7];
        });
        pos.forEach(function (p, i) {
          o += rect(r1(p[0] - 1.5), r1(p[1] + 5.5), 3, 3, "f-ln");
          stops.push([(i / (pos.length - 1)) * 80, tr(p)]);
        });
        stops.push([93, tr(pos[pos.length - 1])]);
        stops.push([100, tr(pos[0])]);
        o += at(0, 0, rect(-5, -5, 10, 10, "f-rd s-ink w1 " + cls, 'style="' + tr(pos[pos.length - 1]) + '"'));
        loop("." + cls, 4, stops, "ease-in-out");
        return o;
      }
      out += ball(big, 8, "bb");
      out += ball(small, 142, "bs");
      out += T(130, 112, "bottom of the valley = least wrong", "tm ts");
      return out;
    }
  );

  /* =========================================================
     27. EMA
     ========================================================= */
  def(
    "ema",
    "A jittery line of the newest values and a smooth running average that follows the trend and ignores the twitches.",
    function () {
      var rand = rng(44);
      var raw = [];
      var avg = [];
      var e = null;
      for (var i = 0; i <= 58; i++) {
        var u = i / 58;
        var base = 34 + 34 * (1 - Math.exp(-2.2 * u));
        var v = base + (rand() - 0.5) * 22;
        e = e === null ? v : e + 0.14 * (v - e);
        raw.push([16 + u * 228, v]);
        avg.push([16 + u * 228, e]);
      }
      var out = line(14, 94, 246, 94, "s-ink w1");
      out += poly(raw, "ln s-ln w1 dr er") + poly(avg, "ln s-cd w3 dr ea");
      out += rect(-3.5, -3.5, 7, 7, "f-go s-ink w1 ed");
      out += rect(10, 100, 8, 8, "f-ln") + T(22, 108, "newest value", "");
      out += rect(112, 100, 8, 8, "f-cd") + T(124, 108, "running average", "");
      draw(".er,.ea", 4, 4, 82);
      var sample = avg.filter(function (_, i) {
        return i % 3 === 0 || i === avg.length - 1;
      });
      follow(".ed", 4, sample, 4, 82);
      cur.css.push(scope(".ed") + "{transform:translate(" + r1(avg[avg.length - 1][0]) + "px," + r1(avg[avg.length - 1][1]) + "px)}");
      return out;
    }
  );

  /* =========================================================
     28. seed
     ========================================================= */
  def(
    "seed",
    "Three dice with different seeds land on different faces, and the three results below come out slightly different.",
    function () {
      var pips = {
        1: [[1, 1]],
        2: [[0, 0], [2, 2]],
        3: [[0, 0], [1, 1], [2, 2]],
        4: [[0, 0], [2, 0], [0, 2], [2, 2]],
        5: [[0, 0], [2, 0], [1, 1], [0, 2], [2, 2]],
        6: [[0, 0], [2, 0], [0, 1], [2, 1], [0, 2], [2, 2]],
      };
      var finals = [3, 5, 2];
      var seqs = [[1, 4, 6, 2, 5, 3], [6, 2, 4, 1, 3, 5], [4, 5, 1, 6, 3, 2]];
      var heights = [20, 16, 22];
      var out = "";
      var defsOut = "";
      finals.forEach(function (f, d) {
        var cx = 22 + d * 80;
        var Y = 18;
        var cid = "xvsc" + d;
        defsOut += '<clipPath id="' + cid + '"><rect x="' + cx + '" y="18" width="32" height="32"/></clipPath>';
        out += T(cx + 16, 12, "seed " + (d + 1), "tm tb");
        var sprite = "";
        for (var face = 1; face <= 6; face++) {
          var oy = 18 + (face - 1) * 32;
          sprite += rect(cx, oy, 32, 32, "f-pa s-ink w2");
          pips[face].forEach(function (p) {
            sprite += '<circle cx="' + (cx + 7 + p[0] * 9) + '" cy="' + (oy + 7 + p[1] * 9) + '" r="3" class="f-ink"/>';
          });
        }
        out += '<g clip-path="url(#' + cid + ')"><g class="sp sp' + d + '" style="transform:translateY(' + -(f - 1) * 32 + 'px)">' + sprite + "</g></g>";
        var stops = [];
        seqs[d].forEach(function (face, i) {
          stops.push([i * 9, "transform:translateY(" + -(face - 1) * 32 + "px)"]);
        });
        stops.push([60, "transform:translateY(" + -(f - 1) * 32 + "px)"]);
        stops.push([93, "transform:translateY(" + -(f - 1) * 32 + "px)"]);
        stops.push([100, "transform:translateY(" + -(seqs[d][0] - 1) * 32 + "px)"]);
        loop(".sp" + d, 3.6, stops, "steps(1)");
        out += rect(cx + 4, 98 - heights[d], 24, heights[d], "f-cy s-ink w1 ob rb" + d);
        an(".rb" + d, 3.6, 60, 72, "transform:scaleY(0)", "transform:none");
      });
      out += T(130, 64, "same code, different seed", "tm tb");
      out += line(14, 98, 246, 98, "s-ink w1");
      out += T(130, 113, "slightly different results", "tm ts");
      return "<defs>" + defsOut + "</defs>" + out;
    }
  );

  /* =========================================================
     29. checkpoint
     ========================================================= */
  def(
    "checkpoint",
    "A progress bar with save marks. A crash hits near the end, the bar rolls back to the last save, and the work since then is lost.",
    function () {
      var X0 = 14;
      var Wd = 232;
      var out = rect(X0, 44, Wd, 20, "f-so s-ink w15");
      out += rect(X0 + Wd * 0.6, 44, Wd * 0.1, 20, "f-ha lost");
      out += rect(X0, 44, Wd, 20, "f-cy s-ink w1 o0 fill", 'style="transform:scaleX(.6)"');
      [0.2, 0.4, 0.6, 0.8].forEach(function (u) {
        out += line(X0 + Wd * u, 34, X0 + Wd * u, 68, "s-ink w1");
        out += rect(X0 + Wd * u - 5, 24, 10, 10, "f-go s-ink w1");
      });
      var cx = X0 + Wd * 0.7;
      out += '<path d="M' + (cx - 6) + " 48L" + (cx + 6) + " 60M" + (cx + 6) + " 48L" + (cx - 6) + ' 60" class="ln s-rd w3 xx"/>';
      out += rect(10, 82, 8, 8, "f-go s-ink w1") + T(22, 90, "save", "");
      out += rect(70, 82, 8, 8, "f-ha s-ln w1") + T(82, 90, "work lost since last save", "");
      out += T(130, 112, "a crash rewinds to the last save", "tm tb");
      loop(".fill", 5, [[0, "transform:scaleX(0)"], [48, "transform:scaleX(.7)"], [52, "transform:scaleX(.7)"], [62, "transform:scaleX(.6)"], [66, "transform:scaleX(.6)"], [94, "transform:scaleX(1)"], [100, "transform:scaleX(1)"]], "ease-in-out");
      loop(".lost,.xx", 5, [[0, "opacity:0"], [48, "opacity:0"], [52, "opacity:1"], [70, "opacity:1"], [78, "opacity:0"], [100, "opacity:0"]], "linear");
      cur.css.push(scope(".fill") + "{}");
      return out;
    }
  );

  /* =========================================================
     30. outage and rollback
     ========================================================= */
  def(
    "outage",
    "Two progress bars. When a site goes down, the first bar rewinds to the last save and repeats work. The second keeps going with the surviving site.",
    function () {
      var X0 = 72;
      var Wd = 176;
      var out = T(6, 30, "roll back", "tb") + T(6, 76, "keep going", "tb");
      out += rect(X0, 20, Wd, 16, "f-so s-ink w15") + rect(X0, 20, Wd, 16, "f-cy s-ink w1 o0 b1", 'style="transform:scaleX(.9)"');
      out += rect(X0, 66, Wd, 16, "f-so s-ink w15") + rect(X0, 66, Wd, 16, "f-cy s-ink w1 o0 b2", 'style="transform:scaleX(.9)"');
      var cx = X0 + Wd * 0.5;
      out += '<path d="M' + (cx - 5) + " 23L" + (cx + 5) + " 33M" + (cx + 5) + " 23L" + (cx - 5) + ' 33" class="ln s-rd w3 ox ox1"/>';
      out += '<path d="M' + (cx - 5) + " 69L" + (cx + 5) + " 79M" + (cx + 5) + " 69L" + (cx - 5) + ' 79" class="ln s-rd w3 ox ox2"/>';
      out += T(cx, 52, "a site goes down", "tm tr tb ot");
      out += T(130, 108, "redo the work, or carry on without it", "tm ts");
      loop(".b1", 5, [[0, "transform:scaleX(0)"], [38, "transform:scaleX(.5)"], [46, "transform:scaleX(.5)"], [56, "transform:scaleX(.35)"], [60, "transform:scaleX(.35)"], [94, "transform:scaleX(.9)"], [100, "transform:scaleX(.9)"]], "ease-in-out");
      loop(".b2", 5, [[0, "transform:scaleX(0)"], [38, "transform:scaleX(.5)"], [60, "transform:scaleX(.6)"], [80, "transform:scaleX(.9)"], [100, "transform:scaleX(.9)"]], "ease-in-out");
      loop(".ox,.ot", 5, [[0, "opacity:0"], [38, "opacity:0"], [42, "opacity:1"], [62, "opacity:1"], [68, "opacity:0"], [100, "opacity:0"]], "linear");
      return out;
    }
  );

  /* =========================================================
     31. power reading
     ========================================================= */
  def(
    "power",
    "A fast, jumpy power curve above, and below it a slow sensor that reports only one value every half second, so it misses the quick changes.",
    function () {
      var rand = rng(9);
      var truth = [];
      var v = 28;
      var hi = true;
      var hold = 2;
      for (var x = 10; x <= 250; x += 3) {
        if (--hold <= 0) {
          hi = !hi;
          hold = 1 + Math.floor(rand() * 5);
        }
        v = hi ? 40 : 18;
        truth.push([x, v]);
      }
      var stepsD = [];
      var stair = [];
      var marks = "";
      var k = 0;
      for (var sx = 10; sx < 250; sx += 40) {
        var t = truth[Math.round((sx - 10) / 3)];
        var y = 66 + (t[1] - 18) * 0.7;
        stair.push([sx, y], [Math.min(250, sx + 40), y]);
        marks += line(sx, 40, sx, y, "s-go w1", 'stroke-dasharray="2 2"') + rect(sx - 3, y - 3, 6, 6, "f-go s-ink w1 oc sm sm" + k);
        an(".sm" + k, 4, 10 + k * 11, 16 + k * 11, "transform:scale(0)", "transform:none");
        k++;
      }
      stepsD = stair;
      var out = T(10, 12, "what the GPU draws", "tb");
      out += poly(truth.map(function (p, i) { return [p[0], p[1] + 0]; }).reduce(function (acc, p, i, arr) {
        if (i) acc.push([p[0], arr[i - 1][1]]);
        acc.push(p);
        return acc;
      }, []), "ln s-bl w15 dr tc");
      out += marks;
      out += T(10, 100, "what the sensor reports", "tb");
      out += poly(stepsD, "ln s-cd w2 dr sc");
      out += T(130, 116, "one reading per 0.5 s misses spikes", "tm ts");
      draw(".tc", 4, 4, 50);
      draw(".sc", 4, 20, 82);
      return out;
    }
  );

  /* =========================================================
     32. AI coding agents
     ========================================================= */
  def(
    "agents",
    "An editor window where lines of code are written quickly, then a report card where the same agent stamps its own work with an A plus.",
    function () {
      var out = rect(10, 10, 112, 88, "f-pa s-ink w2") + rect(10, 10, 112, 14, "f-bl");
      out += T(18, 21, "agent.py", "tw");
      var widths = [70, 48, 82, 60, 36, 74];
      widths.forEach(function (w, i) {
        out += rect(18, 32 + i * 10, w, 5, "f-cy o0 cl cl" + i);
        an(".cl" + i, 4.4, 4 + i * 6, 10 + i * 6, "transform:scaleX(0)", "transform:none", "linear");
      });
      out += rect(138, 10, 112, 88, "f-pa s-ink w2") + rect(138, 10, 112, 14, "f-bl");
      out += T(146, 21, "report", "tw");
      out += T(146, 42, "tests", "");
      out += '<path d="M200 38l5 5l10 -11" pathLength="1" class="ln s-gn w3 dr ck"/>';
      out += T(146, 62, "grade", "");
      out += T(218, 76, "A+", "tm tb z tr stamp", 'style="transform:rotate(-12deg)"');
      out += T(146, 90, "given by itself", "ts");
      out += T(130, 114, "it also grades its own work", "tm tb");
      draw(".ck", 4.4, 44, 54);
      an(".stamp", 4.4, 62, 70, "transform:rotate(-12deg) scale(2);opacity:0", "transform:rotate(-12deg);opacity:1");
      cur.css.push(scope(".stamp") + "{transform-origin:50% 50%}");
      return out;
    }
  );

  /* ---------- public API ---------- */

  var HATCH =
    '<defs><pattern id="gsx-hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
    '<rect width="4" height="4" class="f-so"/><line x1="0" y1="0" x2="0" y2="4" class="s-ln w15"/></pattern></defs>';

  function css() {
    return (
      BASE_CSS +
      order
        .map(function (id) {
          return defs[id].css;
        })
        .join("")
    );
  }

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  }

  function svg(id, alt) {
    var d = defs[id];
    if (!d) return "";
    return (
      '<svg viewBox="0 0 ' +
      W +
      " " +
      H +
      '" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="' +
      esc(alt || d.alt) +
      '" focusable="false">' +
      HATCH +
      '<g class="v-' +
      id +
      '">' +
      d.svg +
      "</g></svg>"
    );
  }

  var styleEl = null;
  function ensureStyle() {
    if (styleEl || typeof document === "undefined") return;
    styleEl = document.createElement("style");
    styleEl.setAttribute("data-gsx-visuals", "");
    styleEl.textContent = css();
    document.head.appendChild(styleEl);
  }

  function mount(host, id, opts) {
    opts = opts || {};
    ensureStyle();
    host.classList.add("gsx-vis");
    host.classList.toggle("is-still", !!opts.still);
    host.innerHTML = svg(id, opts.alt);
  }

  function unmount(host) {
    host.innerHTML = "";
  }

  return {
    ids: order.slice(),
    has: function (id) {
      return Object.prototype.hasOwnProperty.call(defs, id);
    },
    alt: function (id) {
      return defs[id] ? defs[id].alt : "";
    },
    svg: svg,
    css: css,
    mount: mount,
    unmount: unmount,
    width: W,
    height: H,
  };
});
