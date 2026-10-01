/* cost-ladder: one number, followed down. Cost per token is made of GPU time,
   electricity and hardware wear. GPU time is math needed divided by GPU speed.
   Speed comes from the chip, the chip from its transistors, the transistors
   from the light that prints them. Rungs appear as you scroll through the
   figure. Click a rung to light the link that says what it is made of. */
(function (root) {
  "use strict";
  var F = root.GPUStackFigures;

  var RUNGS = [
    { cards: [{ name: "Cost of one token", sub: "The one number. A token is about three quarters of a word." }] },
    {
      cards: [
        { name: "GPU time", sub: "Rented or owned." },
        { name: "Electricity", sub: "GPUs and cooling." },
        { name: "Hardware wear", sub: "Chips age out." },
      ],
    },
    {
      cards: [
        { name: "Math needed", sub: "<b>6 x size x tokens</b>" },
        { name: "GPU speed", sub: "Math done per second." },
      ],
    },
    { cards: [{ name: "The chip", sub: "Speed comes from how many switches it has and how fast they flip." }] },
    { cards: [{ name: "Transistors", sub: "Tiny switches. Smaller ones mean more per chip." }] },
    { cards: [{ name: "The light that prints them", sub: "The shorter the wavelength, the finer the lines it can draw." }] },
  ];
  var LINKS = [
    "Add up what the run uses, then divide by its tokens.",
    "GPU time is the math to do, divided by the math per second.",
    "Speed is set by the chip. Math needed is set by the model.",
    "A chip is billions of transistors.",
    "How small a transistor can be depends on the finest line the light can print.",
  ];

  F.define("cost-ladder", {
    title: "Following one number down",
    label: "Diagram: cost per token, then GPU time and electricity, then math and GPU speed, then the chip, transistors and the light that prints them",
    summary:
      "A ladder from one number down to physics. Cost per token is made of GPU time, electricity and hardware wear. " +
      "GPU time is the math needed, about 6 times model size times tokens, divided by GPU speed. " +
      "GPU speed comes from the chip, the chip from its transistors, and the transistors from the light that prints them.",
    build: function (ctx) {
      var h = ctx.h, u = ctx.util;
      var wrap = h("ol", { class: "cl", style: "list-style:none;margin:0 auto;padding:0" });
      var rungEls = [], linkEls = [], buttons = [];
      var hot = -1;

      RUNGS.forEach(function (r, i) {
        var row = h("li", { style: "margin:0" });
        var inner = h("div", { class: "cl-row " + (r.cards.length === 3 ? "three" : r.cards.length === 2 ? "two" : "one") });
        var group = [];
        r.cards.forEach(function (c) {
          var b = h("button", { type: "button", class: "cl-rung", "aria-pressed": "false" }, [
            h("span", { class: "cl-name", text: c.name }),
            h("span", { class: "cl-sub", html: c.sub }),
          ]);
          b.addEventListener("click", function () { reveal(i + 1); pick(i); });
          b.addEventListener("focus", function () { reveal(i + 1); });
          inner.appendChild(b);
          group.push(b);
          buttons.push(b);
        });
        rungEls.push(group);
        row.appendChild(inner);
        if (i < LINKS.length) {
          var l = h("div", { class: "cl-link", text: LINKS[i] });
          linkEls.push(l);
          row.appendChild(l);
        }
        wrap.appendChild(row);
      });
      ctx.el.appendChild(wrap);
      ctx.el.appendChild(h("p", { class: "gsf-note", text: "Click a step to see what it is made of." }));

      function pick(i) {
        hot = hot === i ? -1 : i;
        mark();
      }
      function mark() {
        rungEls.forEach(function (g, k) {
          g.forEach(function (b) { b.setAttribute("aria-pressed", k === hot ? "true" : "false"); });
        });
        linkEls.forEach(function (l, k) { l.className = "cl-link" + (k === hot ? " is-hot" : "") + (l.classList.contains("is-in") ? " is-in" : ""); });
      }

      var shown = 0; // how many rungs are revealed (fractional)
      function reveal(n) {
        if (n <= shown) return;
        shown = n;
        paint();
      }
      function paint() {
        rungEls.forEach(function (g, k) {
          g.forEach(function (b) { b.classList.toggle("is-in", shown > k); });
        });
        linkEls.forEach(function (l, k) { l.classList.toggle("is-in", shown > k + 0.5); });
      }

      var timed = false;
      function fromScroll() {
        if (timed || ctx.reduced) return;
        var r = ctx.fig.getBoundingClientRect();
        var vh = root.innerHeight || 800;
        var travel = r.height + 0.4 * vh;
        var p = u.clamp((0.95 * vh - r.top) / travel);
        reveal(p * RUNGS.length * 1.02);
      }
      var on = false;
      function listen(v) {
        if (v === on) return;
        on = v;
        var fn = v ? "addEventListener" : "removeEventListener";
        root[fn]("scroll", fromScroll, { passive: true });
        root[fn]("resize", fromScroll);
        if (v) fromScroll();
      }
      ctx.onVisible(listen);

      return {
        duration: 6,
        autoplay: false,
        onReplay: function () {
          shown = 0;
          timed = true;
          hot = -1;
          mark();
          paint();
        },
        render: function (t) {
          if (t === 0) {
            if (timed) {
              shown = 0;
              paint();
            }
            return;
          }
          timed = t < 6;
          shown = Math.max(shown, (t / 5.2) * RUNGS.length);
          if (t >= 6) shown = RUNGS.length;
          paint();
        },
        still: 6,
      };
    },
  });
})(typeof window !== "undefined" ? window : globalThis);
