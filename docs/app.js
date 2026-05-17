// Published guide data. Keep these values aligned with the README summaries.
const primerSteps = {
  target: {
    text: "Start with a human question, then follow the named dependencies upstream. Every hop should tell you whether you are looking at an equation, a scenario value, or an unresolved root input.",
    facts: [
      "The registry currently names 1517 variables and 959 equations.",
      "The target is easier to trust when its ancestry is still attached."
    ],
    statusTitle: "Target selected: start with the question.",
    statusBody: "The page keeps the output attached to the labels underneath it.",
    active: ["target"]
  },
  upstream: {
    text: "Walking upstream means refusing to let a final number float by itself. The graph keeps run cost, token count, power, throughput, units, and constraints in the same visible chain.",
    facts: [
      "799 equations are currently covered by unit checks.",
      "The gold highlight marks the part of the receipt you are inspecting."
    ],
    statusTitle: "Upstream selected: equations carry the number.",
    statusBody: "This is where a plain claim becomes a dependency cone.",
    active: ["target", "upstream"]
  },
  roots: {
    text: "Root inputs are not failure badges. They are the places where the model has reached a boundary: a scenario value, a source that needs better support, or physics that has not been decomposed yet.",
    facts: [
      "619 root inputs are still visible in the current summary.",
      "Root debt ranks which unknowns have the largest downstream blast radius."
    ],
    statusTitle: "Roots selected: unpaid assumptions stay named.",
    statusBody: "The point is to find the debt, not hide it under a cleaner-looking answer.",
    active: ["target", "upstream", "roots"]
  },
  fixture: {
    text: "A fixture is a reproducible set of explicit assignments. It can make a target resolve for testing and explanation, but it is not a claim that the outside world has that exact value.",
    facts: [
      "Synthetic fixtures are anchors for the resolver, not vendor truth.",
      "The trace panel below shows how representative fixture values are labeled."
    ],
    statusTitle: "Fixture selected: resolved does not mean calibrated.",
    statusBody: "Explicit assignments make the path testable without pretending the assumptions vanished.",
    active: ["target", "upstream", "roots", "fixture"]
  }
};

const layers = {
  datacenter: {
    text: "The visible machine is a building, but the model treats it as a constraint bundle: grid interconnect, substations, cooling loops, water, occupancy, capex, operations, and uptime.",
    facts: [
      "Inputs include power envelope, PUE, utilization, cooling load, and build cost.",
      "Outputs feed cluster capacity, cost allocation, emissions, and schedule pressure."
    ],
    stack: ["Grid", "Substation", "Cooling", "Power envelope", "Cluster capacity", "Cost per token"]
  },
  gpu: {
    text: "The GPU layer ties compute units, memory bandwidth, HBM capacity, interconnect, thermal limits, and board power to the throughput the training job actually sees.",
    facts: [
      "Peak FLOP/s is only one ceiling among several.",
      "Memory bandwidth, precision, and activation traffic can dominate."
    ],
    stack: ["SMs", "Tensor cores", "HBM", "Package power", "MFU", "Tokens per second"]
  },
  kernel: {
    text: "The kernel layer is where high-level operations become instructions, memory movement, occupancy, launch overhead, and numerical format choices.",
    facts: [
      "A model-level equation can hide several kernel-level bottlenecks.",
      "PTX, tiling, fusion, and quantization all change the usable machine."
    ],
    stack: ["Operation", "Tiling", "Fusion", "Memory traffic", "Occupancy", "Effective throughput"]
  },
  model: {
    text: "The model layer asks how parameters, sequence length, batch size, optimizer state, activation storage, and data schedule become compute and memory demand.",
    facts: [
      "Training cost is not one equation. It is a stack of coupled choices.",
      "Context length and activation strategy reshape the memory problem."
    ],
    stack: ["Parameters", "Tokens", "Context", "Batch", "Optimizer", "Compute demand"]
  },
  physics: {
    text: "The physical-floor layer is the north star: keep decomposing until a number is grounded in a measured property, a derivable relation, or an honestly marked scenario assumption.",
    facts: [
      "Thermal, electrical, optical, and material limits are not background color.",
      "Universal constants are the preferred hard numerical floor."
    ],
    stack: ["Geometry", "Materials", "Heat", "Charge", "Constants", "Constraint floor"]
  },
  economics: {
    text: "The economic layer is where hardware, power, time, reliability, labor, utilization, financing, and token demand meet inside outputs like cost per token.",
    facts: [
      "A price is not a primitive number. It has upstream machinery.",
      "Root debt is especially useful here because economics tempts hand-waving."
    ],
    stack: ["Capex", "Opex", "Utilization", "Amortization", "Throughput", "Cost per token"]
  }
};

const traces = {
  cost: {
    summary: "Cost per token is not a lone price. It depends on run cost, token count, facility power, throughput, utilization, hardware choices, and root assumptions that still need better evidence.",
    facts: [
      "The dense cost fixture resolves 4 of 4 advertised targets.",
      "The representative fixture value is 3.000078e-06, and the README marks it synthetic."
    ],
    note: "This path is why the project keeps economics attached to physics. A price can inherit assumptions from power, cooling, utilization, kernels, and lower physical boundaries.",
    meterLabel: "scenario-report resolves 4 of 4 targets",
    meterFoot: "status: ok, issue_count: 0",
    meterWidth: "100%",
    path: [
      ["econ.cost.per_token", "target", "What does one token cost?"],
      ["econ.run.power_cost", "equation", "Power has to be paid for."],
      ["econ.job.dc_power", "scenario", "Fixture value: 5200.0."],
      ["training.tokens_per_sec", "scenario", "Fixture value: 6666666.66666667."],
      ["cluster and cooling", "constraint", "PUE and facility overhead enter here."],
      ["physical roots", "root", "Unresolved assumptions stay named."]
    ]
  },
  throughput: {
    summary: "Tokens per second is the visible training speed, but the graph treats it as the result of model math, kernels, communication, bubbles, memory traffic, and available hardware.",
    facts: [
      "MFU means Model FLOPs Utilization.",
      "HBM bandwidth and communication can matter as much as raw peak FLOP/s."
    ],
    note: "The trace view keeps the easy phrase, faster training, connected to the things that actually move it: tensors, kernels, collectives, memory, topology, and utilization.",
    meterLabel: "representative fixture: 6666666.66666667 tokens/s",
    meterFoot: "synthetic anchor, not vendor truth",
    meterWidth: "82%",
    path: [
      ["training.tokens_per_sec", "target", "How fast do tokens move?"],
      ["training.step_time", "equation", "Compute plus comms plus bubbles."],
      ["kernel throughput", "equation", "Tiling, fusion, occupancy."],
      ["gpu.peak_flops", "variable", "Ceiling, not guarantee."],
      ["memory and HBM", "constraint", "Traffic can become the bottleneck."],
      ["process roots", "root", "Device limits need physical support."]
    ]
  },
  power: {
    summary: "Datacenter power is a rollup, not a wall-plug vibe. IT load, cooling, racks, auxiliary systems, PUE, utilization, and scenario boundaries all feed the number.",
    facts: [
      "PUE means Power Usage Effectiveness.",
      "The representative dense fixture reports econ.job.dc_power = 5200.0."
    ],
    note: "This is the layer where non-experts can see why cooling and facility assumptions are part of model training, not an external footnote.",
    meterLabel: "representative fixture: econ.job.dc_power = 5200.0",
    meterFoot: "explicit fixture assignment path",
    meterWidth: "68%",
    path: [
      ["econ.job.dc_power", "target", "What power does the job imply?"],
      ["cluster.site.power_it", "equation", "GPU and infrastructure load."],
      ["thermal.dc.pue", "scenario", "Facility overhead multiplier."],
      ["cooling plant", "constraint", "Heat has to leave the building."],
      ["racks and nodes", "variable", "Topology sets the rollup."],
      ["thermal roots", "root", "Local behavior stays inspectable."]
    ]
  }
};

// Static DOM hooks for the three interactive panels.
const primerTabs = document.querySelectorAll("[data-primer]");
const primerNodes = document.querySelectorAll("[data-primer-node]");
const primerText = document.getElementById("primer-text");
const primerFacts = document.getElementById("primer-facts");
const primerStatusTitle = document.getElementById("primer-status-title");
const primerStatusBody = document.getElementById("primer-status-body");
const tabs = document.querySelectorAll("[data-layer]");
const targetTabs = document.querySelectorAll("[data-target]");
const layerText = document.getElementById("layer-text");
const layerFacts = document.getElementById("layer-facts");
const stack = document.getElementById("dependency-stack");
const traceSummary = document.getElementById("trace-summary");
const traceFacts = document.getElementById("trace-facts");
const tracePath = document.getElementById("trace-path");
const traceNote = document.getElementById("trace-note");
const traceMeterLabel = document.getElementById("trace-meter-label");
const traceMeterFoot = document.getElementById("trace-meter-foot");
const traceMeter = document.getElementById("trace-meter");
const clock = document.getElementById("clock");

// Render helpers replace only panel content, preserving the surrounding markup.
function renderPrimer(key) {
  const step = primerSteps[key];
  primerText.textContent = step.text;
  primerFacts.replaceChildren(...step.facts.map((fact) => {
    const item = document.createElement("li");
    item.textContent = fact;
    return item;
  }));
  primerStatusTitle.textContent = step.statusTitle;
  primerStatusBody.textContent = step.statusBody;
  primerNodes.forEach((node) => {
    const active = step.active.includes(node.dataset.primerNode);
    node.classList.toggle("is-lit", active);
    node.classList.toggle("is-active", node.dataset.primerNode === key);
  });
  primerTabs.forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.dataset.primer === key));
  });
}

function renderLayer(key) {
  const layer = layers[key];
  layerText.textContent = layer.text;
  layerFacts.replaceChildren(...layer.facts.map((fact) => {
    const item = document.createElement("li");
    item.textContent = fact;
    return item;
  }));
  stack.replaceChildren(...layer.stack.map((item, index) => {
    const row = document.createElement("div");
    row.className = `dependency-row${index === layer.stack.length - 1 ? " active" : ""}`;
    const label = document.createElement("span");
    label.textContent = item;
    const depth = document.createElement("span");
    depth.textContent = index === layer.stack.length - 1 ? "output" : `depth ${index + 1}`;
    row.append(label, depth);
    return row;
  }));
  tabs.forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.dataset.layer === key));
  });
}

function renderTrace(key) {
  const trace = traces[key];
  traceSummary.textContent = trace.summary;
  traceFacts.replaceChildren(...trace.facts.map((fact) => {
    const item = document.createElement("li");
    item.textContent = fact;
    return item;
  }));
  tracePath.replaceChildren(...trace.path.map(([labelText, role, detail], index) => {
    const node = document.createElement("div");
    node.className = `trace-node${index === trace.path.length - 1 ? " active" : ""}`;
    const roleLabel = document.createElement("small");
    roleLabel.textContent = role;
    const label = document.createElement("b");
    label.textContent = labelText;
    const text = document.createElement("span");
    text.textContent = detail;
    node.append(roleLabel, label, text);
    return node;
  }));
  traceNote.textContent = trace.note;
  traceMeterLabel.textContent = trace.meterLabel;
  traceMeterFoot.textContent = trace.meterFoot;
  traceMeter.style.setProperty("--meter-width", trace.meterWidth);
  targetTabs.forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.dataset.target === key));
  });
}

function updateClock() {
  const now = new Date();
  const h = now.getHours() % 12 || 12;
  const m = now.getMinutes().toString().padStart(2, "0");
  clock.textContent = `${h}:${m} ${now.getHours() >= 12 ? "PM" : "AM"}`;
}

// Wire controls after the static page has parsed.
primerTabs.forEach((tab) => {
  tab.addEventListener("click", () => renderPrimer(tab.dataset.primer));
});

tabs.forEach((tab) => {
  tab.addEventListener("click", () => renderLayer(tab.dataset.layer));
});

targetTabs.forEach((tab) => {
  tab.addEventListener("click", () => renderTrace(tab.dataset.target));
});

renderPrimer("target");
renderLayer("datacenter");
renderTrace("cost");
updateClock();
setInterval(updateClock, 1000);
