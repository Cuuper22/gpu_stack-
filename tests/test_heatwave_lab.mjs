import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DOCS = path.join(ROOT, "docs");

async function readJson(name) {
  return JSON.parse(await fs.readFile(path.join(DOCS, "data", name), "utf8"));
}
function plain(html) {
  return html
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
async function chapter() {
  const html = await fs.readFile(path.join(DOCS, "index.html"), "utf8");
  const m = html.match(/<section class="story-section" id="story-heatwave">([\s\S]*?)<\/section>/);
  assert.ok(m, "chapter exists");
  return { html, body: m[1] };
}

test("the Heatwave window module registers a mount function and keeps the house style", async () => {
  const src = await fs.readFile(path.join(DOCS, "heatwave-lab.js"), "utf8");
  assert.ok(!/[—–]/.test(src), "no em or en dash");
  assert.ok(src.length < 40 * 1024, "module stays small: " + src.length);
  globalThis.window = globalThis;
  await import(path.join(DOCS, "heatwave-lab.js"));
  assert.equal(typeof globalThis.GPUStackHeatwave.mount, "function");
});

test("the Heatwave data file has every quantile state and labels its data", async () => {
  const d = await readJson("e003-heatwave-lab-v1.json");
  assert.equal(d.schema, "gpu-stack.e003-heatwave-lab.v1");
  for (const key of ["packing", "outage", "cost", "audit", "forecast", "thermal", "ablation", "ablation_sim", "finetune"]) {
    assert.ok(d[key] && d[key].status, key + " block");
  }
  assert.equal(d.packing.status, "ready");
  assert.equal(d.packing.data_kind, "simulated");
  assert.equal(d.packing.quantile_levels.length, 21);
  for (const q of d.packing.quantile_levels) {
    const run = d.packing.trace.runs["timestral-5M/q" + String(q)];
    assert.ok(run, "trace for level " + q);
    assert.equal(run.site_power_kw.length, d.packing.trace.runs.reactive.site_power_kw.length);
    assert.ok(run.matches_committed_part, "replay matches the committed eval part for " + q);
    assert.ok(d.packing.policies["timestral-5M/q" + String(q)], "summary for level " + q);
  }
  assert.ok(d.packing.policies.reactive);
  assert.equal(d.outage.data_kind, "simulated");
  assert.equal(d.outage.versions.v2.status, "ready", "outage v2 is in");
  const raw = await fs.readFile(path.join(DOCS, "data", "e003-heatwave-lab-v1.json"), "utf8");
  assert.ok(raw.length < 1.5 * 1024 * 1024, "data file under 1.5 MB");
});

test("the story data file is the lab file without the replay traces", async () => {
  const lab = await readJson("e003-heatwave-lab-v1.json");
  const story = await readJson("e003-heatwave-story-v1.json");
  assert.equal(story.schema, "gpu-stack.e003-heatwave-story.v1");
  for (const key of Object.keys(lab)) {
    if (key === "schema" || key === "packing") continue;
    assert.deepEqual(story[key], lab[key], key + " matches");
  }
  assert.equal(story.packing.trace.runs, undefined);
  assert.deepEqual(story.packing.policies, lab.packing.policies);
  const raw = await fs.readFile(path.join(DOCS, "data", "e003-heatwave-story-v1.json"), "utf8");
  assert.ok(raw.length < 150 * 1024, "story data stays small: " + raw.length);
});

test("pending blocks say so and ready blocks carry a source and a data label", async () => {
  const d = await readJson("e003-heatwave-lab-v1.json");
  for (const key of ["forecast", "thermal", "ablation", "ablation_sim", "finetune"]) {
    assert.ok(["ready", "pending"].includes(d[key].status), key);
  }
  assert.equal(d.ablation.status, "ready");
  for (const [name, ds] of Object.entries(d.ablation.datasets)) {
    assert.ok(["public", "measured", "simulated"].includes(ds.data_kind) || /simulated/.test(ds.data_kind), name + " data kind");
    assert.ok(ds.methods["timestral-209M"].none.wql > 0, name);
    for (const cfg of Object.values(ds.methods["timestral-209M"])) assert.ok(!cfg.groups.includes("L"), "no config that reads realised values");
  }
  assert.ok(d.ablation.source.sha256 && d.ablation.source.file.endsWith("ablation_real.json"));
});

test("the Story chapter cites its numbers and every number matches the data file", async () => {
  const { body } = await chapter();
  const story = await readJson("e003-heatwave-story-v1.json");
  const byId = new Map(story.story_numbers.map((n) => [n.id, n]));
  assert.ok(byId.size === story.story_numbers.length, "unique ids");
  assert.ok(!/[—–]/.test(plain(body)), "no em dash in copy");
  assert.ok(!plain(body).includes("!"), "no exclamation point");
  const ALLOW = new Set(["1", "5", "10", "21", "99", "90", "2026"]);
  const paragraphs = body.match(/<p>[^]*?<\/p>/g) || [];
  let cited = 0;
  for (const p of paragraphs) {
    const text = plain(p);
    const ids = [...p.matchAll(/<!-- hw: ([^>]*?) -->/g)].flatMap((m) => m[1].trim().split(/\s+/));
    const covered = ids.map((id) => {
      assert.ok(byId.has(id), "unknown number id " + id);
      const n = byId.get(id);
      assert.ok(text.includes(n.text), `paragraph must contain "${n.text}" (${id}): ${text.slice(0, 70)}`);
      cited += 1;
      return n.text;
    }).join(" | ");
    for (const tok of text.replace(/\b[HB]\d{3}\b/g, "").match(/\d[\d,]*(?:\.\d+)?/g) || []) {
      const t = tok.replace(/,$/, "");
      assert.ok(ALLOW.has(t) || covered.includes(t), `number ${t} has no source id in: ${text.slice(0, 70)}`);
    }
  }
  assert.ok(cited >= 40, "the chapter cites its numbers: " + cited);
});

test("claims the prose makes about intervals and counts hold in the data", async () => {
  const d = await readJson("e003-heatwave-story-v1.json");
  assert.equal(d.forecast.n_series_both_sizes_lower, d.forecast.n_series, "Timestral lower than every textbook method on every series");
  const u = d.outage.versions.v2.policies.ts28m.useful_gpu_h_vs_reactive;
  assert.ok(u.lo < 0 && u.hi > 0, "useful GPU-hours difference is inside its interval");
  const u3 = d.outage.versions.v3.policies.ts28m.useful_gpu_h_vs_reactive;
  assert.ok(u3.lo < 0 && u3.hi > 0, "v3 useful GPU-hours difference is inside its interval");
  const l3 = d.outage.versions.v3.policies.ts28m.lost_gpu_h_vs_reactive;
  assert.ok(l3.hi < 0, "v3 lost GPU-hours are lower than reacting");
  const lv = d.packing.learned_vs_reactive;
  assert.ok(lv["10"].vs_reactive.lo < 0 && lv["10"].vs_reactive.hi > 0, "the $10 difference spans zero");
  assert.ok(lv["40"].vs_reactive.lo > 0 && lv["160"].vs_reactive.lo > 0 && lv["2.5"].vs_reactive.hi < 0);
  const cfg = (ds, c) => d.ablation.datasets[ds].methods["timestral-209M"][c].vs_none;
  assert.equal(cfg("caiso_rt_lmp_5min", "DA"), "lower");
  assert.equal(cfg("caiso_rt_lmp_5min", "WX"), "overlap");
  assert.equal(cfg("laptop_power_1s_run2", "S"), "lower");
  assert.equal(cfg("laptop_power_10hz_run2", "S"), "higher");
  assert.equal(cfg("gb_carbon_30min", "F"), "lower");
  assert.ok(d.outage.versions.v2.policies.ts28m.recall_in_time > d.outage.versions.v1.policies.ts28m.recall_in_time);
});

test("a pending marker in the chapter exists only while its result is pending", async () => {
  const { body } = await chapter();
  const d = await readJson("e003-heatwave-story-v1.json");
  for (const key of ["ablation_sim", "finetune"]) {
    const marker = new RegExp("HEATWAVE PENDING: [a-z_ ]*\\b" + key + "\\b").test(body);
    const ready = d[key].status === "ready";
    assert.ok(!(marker && ready), key + " landed: replace its pending paragraph with its numbers from data");
    if (!marker) assert.ok(ready, key + ": pending paragraph removed too early");
  }
});

test("the chapter has its figures and the window exists", async () => {
  const { html, body } = await chapter();
  assert.ok(body.includes('data-figure="packing-tradeoff"') && body.includes('data-figure="known-future"'));
  assert.ok(html.includes('src="figures/packing-tradeoff.js"') && html.includes('src="figures/known-future.js"'));
  assert.ok(html.includes('data-window="heatwave"'), "window exists");
});

test("glossary entries for Heatwave are edited and their numbers are sourced", async () => {
  const ex = await readJson("explainers.json");
  const story = await readJson("e003-heatwave-story-v1.json");
  const all = story.story_numbers.map((n) => n.text).join(" | ");
  for (const id of ["quantile-forecast", "timestral", "thermal-throttling", "power-cap", "carbon-intensity"]) {
    const e = ex.entries.find((x) => x.id === id);
    assert.ok(e, id);
    assert.equal(e.review, "edited", id);
    for (const tok of e.body.match(/\d[\d,]*(?:\.\d+)?/g) || []) {
      assert.ok(["1", "5", "10", "21", "99", "2026"].includes(tok) || all.includes(tok), id + ": unsourced number " + tok);
    }
  }
  const visuals = new Set(ex.entries.filter((e) => ["quantile-forecast", "timestral", "thermal-throttling", "power-cap", "carbon-intensity"].includes(e.id)).map((e) => e.visual));
  assert.equal(visuals.size, 5, "each Heatwave term has its own visual");
});

test("the Heatwave icon is its own and is used on the desktop, the title bar and the taskbar", async () => {
  const css = await fs.readFile(path.join(DOCS, "styles", "70-pixel-icons.css"), "utf8");
  const grab = (cls) => (css.match(new RegExp("\\." + cls + " \\{\\s*background-image: url\\(([^)]*)\\)")) || [])[1];
  assert.ok(grab("px-heat") && grab("px-graph"));
  assert.notEqual(grab("px-heat"), grab("px-graph"));
  const html = await fs.readFile(path.join(DOCS, "index.html"), "utf8");
  assert.equal((html.match(/px-heat/g) || []).length, 3);
  assert.ok(!/px-graph"><\/span>\s*<span class="icon-label">Heatwave/.test(html));
});
