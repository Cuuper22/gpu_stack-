import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const docs = path.join(here, "..", "docs");
const require = createRequire(import.meta.url);
const visuals = require(path.join(docs, "explain-visuals.js"));
const data = JSON.parse(readFileSync(path.join(docs, "data", "explainers.json"), "utf8"));
const entries = data.entries;

const BANNED_PHRASES = [
  "fun fact",
  "buckle up",
  "spoiler",
  "let's dive in",
  "game-changer",
  "game changer",
  "passionate",
  "here's the thing",
  "let that sink in",
  "the result?",
  "turns out",
  "most people don't know",
  "this changes everything",
  "read that again",
  "mind-blowing",
  "insane",
  "massive",
  "the secret",
];

function words(s) {
  return s.trim().split(/\s+/).filter(Boolean).length;
}

function visibleText(e) {
  const parts = [e.term, e.title, e.body, ...(e.aliases || [])];
  if (e.link) parts.push(e.link.label);
  if (e.alt) parts.push(e.alt);
  return parts;
}

test("explainers.json has about thirty entries with unique ids", () => {
  assert.ok(entries.length >= 30, "expected at least 30 entries, got " + entries.length);
  const ids = new Set();
  for (const e of entries) {
    assert.ok(!ids.has(e.id), "duplicate id " + e.id);
    ids.add(e.id);
  }
});

test("the required concepts are all covered", () => {
  const need = [
    "token", "parameters", "gpu", "h100", "gpu-hour", "flop", "6nd", "peak-speed", "mfu",
    "training-run", "cost-per-token", "electricity", "pue", "amortization", "datacenter",
    "transistor", "lithography", "euv", "wavelength", "numerical-aperture", "k1",
    "equation-units", "rule-of-thumb", "published-runs", "sync-training", "weight-averaging",
    "learning-rate", "ema", "seed", "checkpoint", "outage-rollback", "power-reading",
    "coding-agents",
  ];
  const have = new Set(entries.map((e) => e.id));
  for (const id of need) assert.ok(have.has(id), "missing entry " + id);
});

test("every entry has the required fields and an existing visual", () => {
  for (const e of entries) {
    for (const key of ["id", "term", "title", "body", "visual", "review"]) {
      assert.equal(typeof e[key], "string", e.id + ": missing " + key);
      assert.ok(e[key].length > 0, e.id + ": empty " + key);
    }
    assert.match(e.id, /^[a-z0-9][a-z0-9-]*$/, e.id + ": id must be kebab case");
    assert.equal(e.review, "draft", e.id + ": review must be draft");
    assert.ok(visuals.has(e.visual), e.id + ": unknown visual " + e.visual);
    if (e.link) {
      assert.match(e.link.href, /^(https:\/\/|#|\.{0,2}\/)/, e.id + ": bad link");
      assert.ok(e.link.label && e.link.label.length > 0, e.id + ": link needs a label");
    }
    if (e.aliases) assert.ok(Array.isArray(e.aliases), e.id + ": aliases must be a list");
  }
});

test("aliases and ids never collide across entries", () => {
  const seen = new Map();
  for (const e of entries) {
    for (const key of [e.id, ...(e.aliases || [])]) {
      const k = key.toLowerCase();
      assert.ok(!seen.has(k) || seen.get(k) === e.id, "term key '" + key + "' used by " + seen.get(k) + " and " + e.id);
      seen.set(k, e.id);
    }
  }
});

test("bodies are short", () => {
  for (const e of entries) {
    const n = words(e.body);
    assert.ok(n < 60, e.id + ": body has " + n + " words, limit is 59");
    assert.ok(n >= 12, e.id + ": body is too thin (" + n + " words)");
  }
});

test("house style: no em dashes, exclamation points, emoji or banned phrases", () => {
  const emoji = /\p{Extended_Pictographic}/u;
  for (const e of entries) {
    for (const text of visibleText(e)) {
      assert.ok(!/[—–]/.test(text), e.id + ": dash character in '" + text + "'");
      assert.ok(!text.includes("!"), e.id + ": exclamation point in '" + text + "'");
      assert.ok(!emoji.test(text), e.id + ": emoji in '" + text + "'");
      const low = text.toLowerCase();
      for (const p of BANNED_PHRASES) assert.ok(!low.includes(p), e.id + ": banned phrase '" + p + "'");
    }
  }
});

test("visual source has no em dashes or exclamation marks in visible text", () => {
  const src = readFileSync(path.join(docs, "explain-visuals.js"), "utf8");
  assert.ok(!/[—–]/.test(src), "dash character in explain-visuals.js");
  for (const id of visuals.ids) {
    const svg = visuals.svg(id);
    const texts = [...svg.matchAll(/>([^<]+)</g)].map((m) => m[1]);
    for (const t of texts) {
      assert.ok(!t.includes("!"), id + ": exclamation in label '" + t + "'");
      assert.ok(!/\p{Extended_Pictographic}/u.test(t), id + ": emoji in label '" + t + "'");
    }
  }
});

test("each visual renders balanced SVG and has an alt text", () => {
  assert.ok(visuals.ids.length >= 30);
  for (const id of visuals.ids) {
    const svg = visuals.svg(id);
    assert.ok(svg.startsWith("<svg") && svg.endsWith("</svg>"), id + ": not an svg");
    assert.ok(visuals.alt(id).length > 20, id + ": alt text too short");
    const stack = [];
    for (const m of svg.matchAll(/<(\/?)([a-zA-Z][\w:-]*)([^>]*?)(\/?)>/g)) {
      const [, close, name, , self] = m;
      if (self) continue;
      if (close) assert.equal(stack.pop(), name, id + ": mismatched </" + name + ">");
      else stack.push(name);
    }
    assert.equal(stack.length, 0, id + ": unclosed tags " + stack.join(","));
    assert.ok(!/NaN|undefined/.test(svg), id + ": NaN or undefined in markup");
    const attrs = [...svg.matchAll(/<(\w+)((?:\s+[\w:-]+="[^"]*")+)\s*\/?>/g)];
    for (const a of attrs) {
      const names = [...a[2].matchAll(/\s([\w:-]+)=/g)].map((n) => n[1]);
      assert.equal(new Set(names).size, names.length, id + ": duplicate attribute on <" + a[1] + "> " + names.join(","));
    }
  }
  const css = visuals.css();
  assert.ok(!/NaN|undefined/.test(css), "NaN or undefined in generated CSS");
  assert.ok(css.includes("prefers-reduced-motion"), "stylesheet must honor reduced motion");
});

test("every data-term in the demo page is known", () => {
  const html = readFileSync(path.join(docs, "explain-demo.html"), "utf8");
  const keys = new Set();
  for (const e of entries) for (const k of [e.id, ...(e.aliases || [])]) keys.add(k.toLowerCase());
  const used = [...html.matchAll(/data-term="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(used.length >= 6, "demo should use several terms");
  for (const t of used) assert.ok(keys.has(t.toLowerCase()), "demo uses unknown term " + t);
});
