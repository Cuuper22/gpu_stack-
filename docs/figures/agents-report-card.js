/* agents-report-card: an AI agent's self-graded report card. Grades get
   crossed out and re-graded, in both directions. */
(function (root) {
  "use strict";
  var F = root.GPUStackFigures;
  var ROWS = [
    { task: "A result that held on one seed", old: "BRILLIANT", now: "an accident" },
    { task: "Calculator against 27 published runs", old: "FAILED", now: "actually fine" },
    { task: "Averaging beats synchronized training", old: "NOVEL", now: "a known effect" },
  ];
  var PER = 2.8; // seconds per row

  F.define("agents-report-card", {
    title: "Report card, graded by the agent",
    label: "Report card: an AI agent's grades for its own work, each crossed out and replaced",
    summary:
      "An AI agent's self-graded report card. A result it called brilliant turned out to be an accident. " +
      "A result it called failed was actually fine, because the bar it set could not be passed. " +
      "A result it called novel was a known effect. The agent graded its own work.",
    build: function (ctx) {
      var h = ctx.h, u = ctx.util;
      var rows = ROWS.map(function (r) {
        var old = h("span", { class: "rc-old", text: r.old });
        var now = h("span", { class: "rc-new", text: r.now });
        var el = h("li", { class: "rc-row", style: "list-style:none" }, [
          h("span", { class: "rc-task", text: r.task }),
          h("span", { class: "rc-grade" }, [old, now]),
        ]);
        return { el: el, old: old, now: now, grade: el.lastChild };
      });
      var foot = h("p", { class: "rc-foot", text: "Graded by: the agent that did the work." });
      var list = h("ul", { style: "margin:0;padding:0" });
      rows.forEach(function (r) { list.appendChild(r.el); });
      ctx.el.appendChild(
        h("div", { class: "rc-sheet" }, [
          h("div", { class: "rc-head" }, [h("span", { text: "Self-assessment" }), h("span", { text: "as filed" })]),
          list,
          foot,
        ])
      );

      return {
        duration: PER * ROWS.length + 1.6,
        render: function (t) {
          rows.forEach(function (r, i) {
            var t0 = i * PER;
            r.el.classList.toggle("is-in", t >= t0);
            r.grade.style.setProperty("--strike", String(u.ease((t - t0 - 1.0) / 0.5)));
            r.now.style.setProperty("--shown", String(u.ease((t - t0 - 1.6) / 0.5)));
          });
          foot.classList.toggle("is-in", t >= PER * ROWS.length);
        },
      };
    },
  });
})(typeof window !== "undefined" ? window : globalThis);
