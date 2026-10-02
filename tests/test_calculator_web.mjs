// The web calculator evaluates the same expressions the Python equation graph resolved.
// docs/data/calculator-model.json holds expected values that Python computed; this test
// evaluates the exported expression trees in JavaScript and compares.
import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const calc = require(path.join(here, "..", "docs", "calculator.js"));
const model = JSON.parse(readFileSync(path.join(here, "..", "docs", "data", "calculator-model.json"), "utf8"));

test("model has the expected shape", () => {
  assert.equal(model.tests.length, 3);
  assert.deepEqual(model.output_order, Object.keys(model.outputs));
  assert.match(model.accuracy.text, /Checked against 27 published training runs/);
  for (const oid of model.output_order) {
    assert.ok(model.outputs[oid].chain.length > 0, `${oid} has a chain`);
  }
});

for (const [i, t] of model.tests.entries()) {
  test(`case ${i + 1}: ${t.name} matches Python`, () => {
    const { outputs } = calc.evaluate(model, t.inputs);
    for (const [k, expected] of Object.entries(t.expected)) {
      const got = outputs[k];
      const rel = Math.abs(got - expected) / Math.max(Math.abs(expected), 1e-300);
      assert.ok(rel < 1e-9, `${k}: js ${got} vs python ${expected} (rel ${rel})`);
    }
  });
}

test("the last step of each chain equals the output", () => {
  const { outputs, steps } = calc.evaluate(model, model.tests[0].inputs);
  for (const oid of model.output_order) {
    const last = steps[oid][steps[oid].length - 1];
    const rel = Math.abs(last.value - outputs[oid]) / Math.abs(outputs[oid]);
    // electricity and hardware chains end on the cost step itself; the others on a unit conversion
    assert.ok(rel < 1e-9, `${oid}: last step ${last.variable} ${last.value} vs ${outputs[oid]}`);
  }
});

test("more GPUs changes time but not cost per token", () => {
  const base = { ...model.tests[0].inputs };
  const more = { ...base, n_gpus: base.n_gpus * 2 };
  const a = calc.evaluate(model, base).outputs;
  const b = calc.evaluate(model, more).outputs;
  assert.ok(Math.abs(a.training_days / b.training_days - 2) < 1e-9);
  assert.ok(Math.abs(a.cost_per_million_tokens / b.cost_per_million_tokens - 1) < 1e-9);
});
