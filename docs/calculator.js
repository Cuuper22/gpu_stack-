/*
 * GPU Stack calculator widget.
 *
 *   GPUStackCalculator.mount(element, { modelUrl, model })
 *
 * Every number comes from docs/data/calculator-model.json, which is generated from the
 * Python equation graph (scripts/build_site_data.py). The browser only evaluates the
 * exported expression trees, so the web page and `gpu-stack estimate` agree.
 *
 * Also exports (for tests): evaluate(model, inputs), evalTree(node, env).
 */
(function (root) {
  "use strict";

  var SCRIPT_SRC = (function () {
    try {
      return document.currentScript && document.currentScript.src ? document.currentScript.src : "";
    } catch (e) {
      return "";
    }
  })();

  // ---------------------------------------------------------------- math

  function evalTree(node, env) {
    if (typeof node === "number") return node;
    if (typeof node === "string") {
      if (!(node in env)) throw new Error("missing input " + node);
      return env[node];
    }
    var op = node[0];
    var i;
    var acc;
    if (op === "add") {
      acc = 0;
      for (i = 1; i < node.length; i++) acc += evalTree(node[i], env);
      return acc;
    }
    if (op === "mul") {
      acc = 1;
      for (i = 1; i < node.length; i++) acc *= evalTree(node[i], env);
      return acc;
    }
    if (op === "pow") return Math.pow(evalTree(node[1], env), evalTree(node[2], env));
    throw new Error("unknown operation " + op);
  }

  // inputs: {id: number}. Returns {outputs: {id: value}, steps: {outputId: [{...step, value}]}}.
  function evaluate(model, inputs) {
    var outputs = {};
    var steps = {};
    model.output_order.forEach(function (oid) {
      var spec = model.outputs[oid];
      outputs[oid] = evalTree(spec.expr, inputs);
      steps[oid] = spec.chain.map(function (s) {
        return {
          variable: s.variable, label: s.label, formula: s.formula, unit: s.unit, kind: s.kind,
          equation: s.equation, value: evalTree(s.expr, inputs)
        };
      });
    });
    return { outputs: outputs, steps: steps };
  }

  // ---------------------------------------------------------------- formatting

  function group(n) {
    return Math.round(n).toLocaleString("en-US");
  }

  function sig(v, digits) {
    if (!isFinite(v)) return "n/a";
    if (v === 0) return "0";
    var a = Math.abs(v);
    if (a >= 1e6 || a < 1e-3) return v.toExponential(digits - 1).replace("e+", " x 10^").replace("e-", " x 10^-");
    var d = Math.max(0, digits - 1 - Math.floor(Math.log10(a)));
    return Number(v.toFixed(Math.min(d, 8))).toLocaleString("en-US", { maximumFractionDigits: 8 });
  }

  function si(v, unit) {
    var prefixes = [[1e18, "E"], [1e15, "P"], [1e12, "T"], [1e9, "G"], [1e6, "M"], [1e3, "k"]];
    var a = Math.abs(v);
    for (var i = 0; i < prefixes.length; i++) {
      if (a >= prefixes[i][0]) return sig(v / prefixes[i][0], 4) + " " + prefixes[i][1] + unit;
    }
    return sig(v, 4) + " " + unit;
  }

  function count(v) {
    var a = Math.abs(v);
    if (a >= 1e12) return sig(v / 1e12, 3) + " trillion";
    if (a >= 1e9) return sig(v / 1e9, 3) + " billion";
    if (a >= 1e6) return sig(v / 1e6, 3) + " million";
    return group(v);
  }

  function money(v) {
    if (!isFinite(v)) return "n/a";
    if (Math.abs(v) >= 1000) return "$" + group(v);
    if (Math.abs(v) >= 1) return "$" + v.toFixed(2);
    if (Math.abs(v) >= 0.01) return "$" + v.toFixed(4);
    return "$" + sig(v, 3);
  }

  function formatValue(v, unit) {
    switch (unit) {
      case "USD": return money(v);
      case "USD/s": return money(v) + " per second";
      case "USD/token": return "$" + sig(v, 3) + " per token";
      case "USD/kWh": return "$" + sig(v, 3) + " per kWh";
      case "USD/(W*s)": return "$" + sig(v, 3) + " per watt-second";
      case "FLOP/s": return si(v, "FLOP/s");
      case "FLOP": return si(v, "FLOP");
      case "W": return si(v, "W");
      case "s": return sig(v, 4) + " s";
      case "days": return sig(v, 3) + " days";
      case "MWh": return sig(v, 3) + " MWh";
      case "GPU-hours": return group(v) + " GPU-hours";
      case "parameters": return count(v) + " parameters";
      case "tokens": return count(v) + " tokens";
      case "GPUs": return group(v) + " GPUs";
      case "steps": return group(v) + " steps";
      case "x": return sig(v, 3) + "x";
      case "years": return sig(v, 3) + " years";
      default:
        if (unit && unit.indexOf("fraction") === 0) return sig(v * 100, 3) + "%";
        return sig(v, 4) + (unit ? " " + unit : "");
    }
  }

  function headline(oid, v) {
    if (oid === "training_days") {
      if (v < 1) return { big: sig(v * 24, 3), small: "hours" };
      return { big: sig(v, 3), small: "days" };
    }
    if (oid === "gpu_hours") return { big: group(v), small: "GPU-hours" };
    if (oid === "energy_mwh") {
      if (v < 1) return { big: sig(v * 1000, 3), small: "kWh" };
      return { big: sig(v, 3), small: "MWh" };
    }
    if (oid === "cost_per_million_tokens") return { big: money(v), small: "per million tokens" };
    return { big: money(v), small: "" };
  }

  // ---------------------------------------------------------------- DOM helpers

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "class") n.className = attrs[k];
        else if (k === "text") n.textContent = attrs[k];
        else if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]);
      });
    }
    (children || []).forEach(function (c) {
      if (c) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return n;
  }

  var uid = 0;

  // Steps that only restate the line above them; hidden until the viewer asks for every step.
  var MINOR_STEPS = [
    "training.flops_per_step", "training.flops_executed_per_step", "training.t_step_nominal",
    "training.t_bubbles", "training.t_step", "training.wallclock_nominal",
    "econ.power.price_kwh", "econ.power.price_ws"
  ];

  function tip(text) {
    var id = "gsc-tip-" + ++uid;
    var t = el("span", { class: "gsc-tip", tabindex: "0", role: "button", "aria-label": "What is this? " + text, "aria-describedby": id }, ["?"]);
    t.appendChild(el("span", { class: "gsc-tip-text", id: id, role: "tooltip", text: text }));
    return t;
  }

  function tagClass(model, tag) {
    if (tag === model.tags.user) return "gsc-tag-user";
    if (tag === model.tags.spec) return "gsc-tag-spec";
    return "gsc-tag-assume";
  }

  function tagChip(model, tag) {
    return el("span", { class: "gsc-tag " + tagClass(model, tag), text: tag });
  }

  // ---------------------------------------------------------------- widget

  var PRESETS = [
    { label: "Small: 1B on 0.3T tokens, 64 GPUs", params: 1, tokens: 0.3, gpus: 64 },
    { label: "Medium: 7B on 2T tokens, 1,024 GPUs", params: 7, tokens: 2, gpus: 1024 },
    { label: "Large: 70B on 2T tokens, 4,096 GPUs", params: 70, tokens: 2, gpus: 4096 }
  ];

  function build(root_el, model) {
    var state = {
      paramsB: 7, tokensT: 2, gpus: 1024, gpu: "H100-SXM",
      adv: {}, // id -> number the viewer typed (display units)
      open: null
    };
    var advInputs = model.inputs.filter(function (i) { return i.advanced && i.id !== "peak_flops" && i.id !== "tdp_w"; });
    var scale = { mfu: 100, residual_fraction: 100, other_hardware_fraction: 100, gpu_power_fraction: 100, server_power_fraction: 100 };
    var advUnit = {
      mfu: "%", pue: "x", electricity_price: "$ per kWh", gpu_price: "$ per GPU", useful_life_years: "years",
      residual_fraction: "% of price", other_hardware_fraction: "% of GPU price", gpu_power_fraction: "% of rating",
      server_power_fraction: "% of GPU power"
    };
    var advStep = {
      mfu: "1", pue: "0.05", electricity_price: "0.005", gpu_price: "500", useful_life_years: "0.5",
      residual_fraction: "1", other_hardware_fraction: "5", gpu_power_fraction: "5", server_power_fraction: "5"
    };

    root_el.textContent = "";
    root_el.classList.add("gsc");

    var form = el("form", { class: "gsc-inputs", novalidate: "novalidate" });
    form.addEventListener("submit", function (e) { e.preventDefault(); });

    // Presets
    var presetRow = el("div", { class: "gsc-presets", role: "group", "aria-label": "Example runs" });
    PRESETS.forEach(function (p) {
      var b = el("button", { type: "button", class: "gsc-chip", text: p.label });
      b.addEventListener("click", function () {
        state.paramsB = p.params; state.tokensT = p.tokens; state.gpus = p.gpus;
        syncBasics(); update();
      });
      presetRow.appendChild(b);
    });
    form.appendChild(presetRow);

    function field(id, label, tooltip, input, unitText) {
      var lab = el("label", { class: "gsc-label", for: id }, [label]);
      var row = el("div", { class: "gsc-field" }, [
        el("div", { class: "gsc-field-head" }, [lab, tooltip ? tip(tooltip) : null]),
        el("div", { class: "gsc-input-row" }, [input, unitText ? el("span", { class: "gsc-unit", text: unitText }) : null])
      ]);
      return row;
    }

    var uidBase = "gsc" + (++uid) + "-";
    var inParams = el("input", { id: uidBase + "params", type: "number", inputmode: "decimal", min: "0.001", step: "any" });
    var inTokens = el("input", { id: uidBase + "tokens", type: "number", inputmode: "decimal", min: "0.001", step: "any" });
    var inGpus = el("input", { id: uidBase + "gpus", type: "number", inputmode: "numeric", min: "1", step: "1" });
    var selGpu = el("select", { id: uidBase + "gpu" });
    Object.keys(model.gpus).forEach(function (k) {
      selGpu.appendChild(el("option", { value: k, text: model.gpus[k].label }));
    });

    var byId = {};
    model.inputs.forEach(function (i) { byId[i.id] = i; });

    var basics = el("div", { class: "gsc-basics" }, [
      field(uidBase + "params", "Model size", byId.params.tooltip, inParams, "billion parameters"),
      field(uidBase + "tokens", "Training data", byId.tokens.tooltip, inTokens, "trillion tokens"),
      field(uidBase + "gpu", "GPU type", "The chip that does the arithmetic. Its speed and power come from the maker's datasheet.", selGpu, ""),
      field(uidBase + "gpus", "Number of GPUs", byId.n_gpus.tooltip, inGpus, "GPUs")
    ]);
    form.appendChild(basics);

    // Advanced
    var details = el("details", { class: "gsc-advanced" });
    details.appendChild(el("summary", { text: "Advanced: change the assumptions" }));
    var advBox = el("div", { class: "gsc-adv-grid" });
    var advEls = {};
    advInputs.forEach(function (spec) {
      var inp = el("input", { id: uidBase + spec.id, type: "number", inputmode: "decimal", step: advStep[spec.id] || "any" });
      var chipHolder = el("span", { class: "gsc-chip-holder" });
      var f = field(uidBase + spec.id, spec.label, spec.tooltip, inp, advUnit[spec.id] || "");
      f.querySelector(".gsc-field-head").appendChild(chipHolder);
      advBox.appendChild(f);
      advEls[spec.id] = { input: inp, chip: chipHolder };
      inp.addEventListener("input", function () {
        var raw = inp.value.trim();
        if (raw === "" || isNaN(Number(raw))) { delete state.adv[spec.id]; } else { state.adv[spec.id] = Number(raw); }
        update();
      });
    });
    details.appendChild(advBox);
    var specNote = el("p", { class: "gsc-spec-note" });
    details.appendChild(specNote);
    var reset = el("button", { type: "button", class: "gsc-reset", text: "Reset assumptions to defaults" });
    reset.addEventListener("click", function () { state.adv = {}; update(); });
    details.appendChild(reset);
    form.appendChild(details);

    // Results
    var results = el("div", { class: "gsc-results", "aria-live": "polite" });
    var grid = el("div", { class: "gsc-cards" });
    var panel = el("div", { class: "gsc-panel", hidden: "hidden" });
    var errBox = el("p", { class: "gsc-error", role: "alert", hidden: "hidden" });
    var accuracy = el("p", { class: "gsc-accuracy", text: model.accuracy.text });
    var notIncluded = el("p", { class: "gsc-note" }, [el("strong", { text: "Not included: " }), model.not_included]);
    results.appendChild(errBox);
    results.appendChild(grid);
    results.appendChild(panel);
    results.appendChild(accuracy);
    results.appendChild(notIncluded);

    var layout = el("div", { class: "gsc-layout" }, [form, results]);
    root_el.appendChild(layout);

    var cards = {};
    model.output_order.forEach(function (oid) {
      var spec = model.outputs[oid];
      var big = el("span", { class: "gsc-card-big" });
      var small = el("span", { class: "gsc-card-small" });
      var btn = el("button", {
        type: "button", class: "gsc-card gsc-card-" + oid, "aria-expanded": "false",
        "data-output": oid
      }, [
        el("span", { class: "gsc-card-label", text: spec.label }),
        big, small,
        el("span", { class: "gsc-card-more", text: "What is this made of?" })
      ]);
      btn.addEventListener("click", function () {
        state.open = state.open === oid ? null : oid;
        render(lastResult);
      });
      var wrap = el("div", { class: "gsc-card-wrap" }, [btn, tip(spec.tooltip)]);
      grid.appendChild(wrap);
      cards[oid] = { btn: btn, big: big, small: small };
    });

    function syncBasics() {
      inParams.value = String(state.paramsB);
      inTokens.value = String(state.tokensT);
      inGpus.value = String(state.gpus);
      selGpu.value = state.gpu;
    }

    function readBasics() {
      var p = Number(inParams.value), t = Number(inTokens.value), g = Number(inGpus.value);
      if (inParams.value !== "") state.paramsB = p;
      if (inTokens.value !== "") state.tokensT = t;
      if (inGpus.value !== "") state.gpus = g;
      state.gpu = selGpu.value;
    }
    [inParams, inTokens, inGpus].forEach(function (i) { i.addEventListener("input", function () { readBasics(); update(); }); });
    selGpu.addEventListener("change", function () { readBasics(); update(); });

    // ---- build the numeric inputs for the model
    function currentInputs() {
      var gpu = model.gpus[state.gpu];
      var vals = {}, tags = {};
      vals.params = state.paramsB * 1e9; tags.params = model.tags.user;
      vals.tokens = state.tokensT * 1e12; tags.tokens = model.tags.user;
      vals.n_gpus = state.gpus; tags.n_gpus = model.tags.user;
      vals.peak_flops = gpu.peak_flops; tags.peak_flops = model.tags.spec;
      vals.tdp_w = gpu.tdp_w; tags.tdp_w = model.tags.spec;
      model.inputs.forEach(function (spec) {
        if (spec.id in vals) return;
        var typed = state.adv[spec.id];
        if (typed !== undefined) {
          vals[spec.id] = typed / (scale[spec.id] || 1);
          tags[spec.id] = model.tags.user;
        } else if (spec.id === "gpu_price") {
          vals[spec.id] = gpu.price_usd; tags[spec.id] = model.tags.assumption;
        } else {
          vals[spec.id] = spec.default; tags[spec.id] = spec.tag;
        }
      });
      return { vals: vals, tags: tags, gpu: gpu };
    }

    function validate(v) {
      if (!(v.params > 0)) return "Model size must be above zero.";
      if (!(v.tokens > 0)) return "Training data must be above zero.";
      if (!(v.n_gpus >= 1)) return "You need at least one GPU.";
      if (!(v.mfu > 0 && v.mfu <= 1)) return "GPU speed achieved (MFU) must be between 1% and 100%.";
      if (!(v.pue >= 1)) return "Datacenter overhead (PUE) cannot be below 1.";
      if (!(v.useful_life_years > 0)) return "Years of use must be above zero.";
      if (!(v.residual_fraction >= 0 && v.residual_fraction < 1)) return "Resale value must be between 0% and 99%.";
      var nonneg = ["electricity_price", "gpu_price", "other_hardware_fraction", "gpu_power_fraction", "server_power_fraction"];
      for (var i = 0; i < nonneg.length; i++) if (!(v[nonneg[i]] >= 0)) return "Values cannot be negative.";
      return "";
    }

    var lastResult = null;

    function update() {
      var cur = currentInputs();
      // advanced fields: show typed or default, with a tag chip
      advInputs.forEach(function (spec) {
        var e = advEls[spec.id];
        var shown = cur.vals[spec.id] * (scale[spec.id] || 1);
        if (state.adv[spec.id] === undefined && document.activeElement !== e.input) {
          e.input.value = String(Number(shown.toPrecision(6)));
        }
        e.chip.textContent = "";
        e.chip.appendChild(tagChip(model, cur.tags[spec.id]));
      });
      specNote.textContent = model.gpus[state.gpu].label + ": " + si(cur.gpu.peak_flops, "FLOP/s") +
        " peak (dense BF16), " + cur.gpu.tdp_w + " W power rating, " + cur.gpu.memory_gb + " GB memory. " +
        "Hardware spec (cited): " + cur.gpu.cite + " Price: " + cur.gpu.price_note;
      var err = validate(cur.vals);
      if (err) {
        errBox.textContent = err;
        errBox.hidden = false;
        lastResult = null;
        Object.keys(cards).forEach(function (oid) { cards[oid].big.textContent = "-"; cards[oid].small.textContent = ""; });
        panel.hidden = true;
        return;
      }
      errBox.hidden = true;
      var res = evaluate(model, cur.vals);
      lastResult = { res: res, cur: cur };
      render(lastResult);
    }

    function render(r) {
      if (!r) return;
      model.output_order.forEach(function (oid) {
        var h = headline(oid, r.res.outputs[oid]);
        cards[oid].big.textContent = h.big;
        cards[oid].small.textContent = h.small;
        var open = state.open === oid;
        cards[oid].btn.setAttribute("aria-expanded", open ? "true" : "false");
        cards[oid].btn.classList.toggle("is-open", open);
      });
      panel.textContent = "";
      if (!state.open) { panel.hidden = true; return; }
      var oid = state.open;
      var spec = model.outputs[oid];
      var steps = r.res.steps[oid];
      panel.hidden = false;
      panel.appendChild(el("h3", { class: "gsc-panel-title", text: spec.label + ": what this is made of" }));
      panel.appendChild(el("p", { class: "gsc-panel-intro", text:
        "Read from the top. Each line is one step of the calculation, using the lines above it and the inputs listed below." }));
      var ol = el("ol", { class: "gsc-chain" + (state.allSteps ? "" : " is-compact") });
      var nMinor = 0;
      steps.forEach(function (s) {
        var kindText = s.kind === "graph equation" ? "equation in the model" : (s.kind === "setting" ? "setting chosen by the calculator" : "unit conversion");
        var minor = MINOR_STEPS.indexOf(s.variable) >= 0;
        if (minor) nMinor++;
        var li = el("li", { class: "gsc-step gsc-step-" + s.kind.split(" ")[0] + (minor ? " is-minor" : "") }, [
          el("span", { class: "gsc-step-label", text: s.label }),
          el("span", { class: "gsc-step-value", text: formatValue(s.value, s.unit) }),
          el("span", { class: "gsc-step-formula", text: "= " + s.formula }),
          el("span", { class: "gsc-step-kind", title: s.equation || "", text: kindText })
        ]);
        ol.appendChild(li);
      });
      if (nMinor > 0) {
        var tog = el("button", { type: "button", class: "gsc-reset gsc-toggle-steps",
          text: state.allSteps ? "Show only the key steps" : "Show the " + nMinor + " small steps in between" });
        tog.addEventListener("click", function () { state.allSteps = !state.allSteps; render(lastResult); });
        panel.appendChild(tog);
      }
      panel.appendChild(ol);
      panel.appendChild(el("h4", { class: "gsc-panel-sub", text: "Inputs used" }));
      var ul = el("ul", { class: "gsc-inputs-used" });
      spec.inputs.forEach(function (iid) {
        var s = byId[iid];
        var li = el("li", {}, [
          el("span", { class: "gsc-in-label", text: s.label }),
          el("span", { class: "gsc-in-value", text: formatValue(r.cur.vals[iid], s.unit) }),
          tagChip(model, r.cur.tags[iid])
        ]);
        ul.appendChild(li);
      });
      panel.appendChild(ul);
      var neutral = el("details", { class: "gsc-neutral" }, [
        el("summary", { text: "Other settings held at neutral values" })
      ]);
      var nl = el("ul");
      model.neutral_settings.forEach(function (n) { nl.appendChild(el("li", { text: n.text })); });
      neutral.appendChild(nl);
      panel.appendChild(neutral);
    }

    syncBasics();
    update();
    return { update: update, state: state };
  }

  function loadModel(opts) {
    if (opts && opts.model) return Promise.resolve(opts.model);
    var url = (opts && opts.modelUrl) || (SCRIPT_SRC ? new URL("data/calculator-model.json", SCRIPT_SRC).href : "data/calculator-model.json");
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error("Could not load " + url + " (" + r.status + ")");
      return r.json();
    });
  }

  function mount(element, opts) {
    if (!element) throw new Error("GPUStackCalculator.mount needs an element");
    element.classList.add("gsc");
    element.textContent = "Loading the calculator...";
    return loadModel(opts).then(function (model) {
      return build(element, model);
    }).catch(function (err) {
      element.textContent = "";
      element.appendChild(el("p", { class: "gsc-error", text: "The calculator could not load its data. " + err.message }));
      throw err;
    });
  }

  var api = { mount: mount, evaluate: evaluate, evalTree: evalTree, formatValue: formatValue };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.GPUStackCalculator = api;
})(typeof window !== "undefined" ? window : null);
