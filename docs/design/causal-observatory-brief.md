# Causal Observatory design brief

Status: implementation brief, July 12, 2026.

## Product job

The observatory lets one person move from a plain question to the complete
research record without changing the underlying answer. The first implemented
surface is E001, Beyond One Datacenter:

> Can one training run use three intermittently powered datacenters without
> giving up the learning efficiency of one tightly synchronized cluster?

The surface must make three boundaries impossible to miss:

1. the current output is a **virtual screen**, not a real-cluster result;
2. the timing, traffic, power, and failure traces come from the virtual
   datacenter engine;
3. the learning-delay response is a wide prior seeded by one-step-delay
   observations and has no held-out multi-site validation yet.

## Primary screen

The native desktop concept is a complete 1600 by 1000 application surface,
not a marketing page and not a grid of unrelated dashboard cards.

### Quiet header

- `GPUSTACK / Virtual Datacenter`
- navigation: `Observatory`, `Experiments`, `Evidence`
- experiment selector: `E001 · Beyond One Datacenter`
- semantic-depth control: `Freshman`, `Researcher`, `Full trace`
- share control that preserves the selected experiment, policy, event, time,
  uncertainty mode, and depth in the URL

### Question and evidence boundary

- heading: `Can one training run survive across three datacenters?`
- immediate state: `Virtual screening · held-out validation absent`
- one short answer generated only after a result artifact exists
- no success language when the experiment is merely designed or unvalidated

### Causal field

The center is one open causal canvas, not a set of cards. It contains:

- West, Central, and East sites with accelerator count and allocated power;
- WAN links with 25 Gbit/s assumed payload bandwidth and 20 ms latency;
- the selected Central-site curtailment event;
- causal flow from site availability to mechanical delay, and from completed
  communication-cycle pressure to sync cadence, collective payload, and
  elapsed time;
- membership response, learning progress, and held-out time to target shown as
  explicit unmeasured branches rather than simulated outcomes;
- observed, modeled, assumed, and unmeasured marks encoded by shape and text in
  addition to color;
- direct labels for essential values so hover is never required.

The causal reading order is visible as a restrained numbered spine:

1. an assumed site interruption delays a modeled operation;
2. reactive membership remains unimplemented and visibly unmeasured;
3. after a completed sync cycle, the cadence policy can change the next cycle;
4. modeled collective payload and elapsed time change;
5. an unfitted learning prior is shown only as sensitivity;
6. the WAN falsifier can be computed while learning and time falsifiers stay
   unresolved, leaving the experiment conclusion inconclusive.

### Evidence inspector

Selecting any site, link, event, decision, metric, or falsifier opens one fixed
inspector on desktop and a bottom sheet on mobile. It contains:

- plain-language meaning;
- exact value and unit;
- evidence class: observed, modeled, assumed, or unmeasured;
- uncertainty interval and what it means;
- equation or policy rule;
- source observation IDs and provenance links;
- known transfer limits;
- residual attribution when a held-out observation exists.

For the first scenario, the default inspector selects
`central-curtailment-1` and states that the 30-second interruption is a
screening assumption.

### Aligned experiment timeline

The lower third aligns the synchronous, fixed-local, and adaptive policy tracks
against shared time. It includes compute, collective, checkpoint, failure, and
recovery records plus their modeled resource allocations. Scrubbing the
timeline updates the causal field and inspector. The selected time remains
readable and keyboard accessible.

### Policy and falsifier comparison

The comparison is a compact open table aligned to the timeline, not a row of
score cards. Columns are:

- policy;
- local steps or policy decision;
- progress per FLOP, labeled `unmeasured`, with the separate prior sensitivity
  visible only at deeper levels;
- inter-site bytes;
- time to target, labeled `unmeasured`, with a separate prior projection;
- site base plus accelerator compute energy, with dynamic network, checkpoint,
  storage, host, and cooling energy explicitly excluded;
- falsifier status.

Every number carries `modeled`, `observed`, `assumed`, `prior`, or
`unmeasured`. An individual computable virtual threshold may say `survived`,
but E001 remains `inconclusive` while required falsifiers and mechanisms are
missing. It may not say `validated`, `proved`, or `works`.

## Semantic depth

The depth control changes explanatory density, not the answer.

- **Freshman:** one sentence per mechanism, human units, causal spine, no
  symbols unless selected.
- **Researcher:** policy decisions, intervals, baselines, bottlenecks,
  counterfactuals, and falsifiers.
- **Full trace:** event IDs, nanosecond timestamps, resource reservations,
  equations, assumptions, observation IDs, provenance, and raw JSON links.

## Visual direction

Evolve the existing GPUSTACK illustration world rather than replacing it with
generic SaaS chrome:

- scientific field notebook crossed with a precise mission-control instrument;
- true warm paper canvas, graphite text, oxidized teal for modeled flow, burnt
  orange for interventions, cobalt for observed evidence, and restrained red
  only for falsification or unavailable state;
- fine technical line work and sparse graph-paper registration marks;
- IBM Plex Sans for reading, IBM Plex Mono for values and evidence, and a
  restrained Pixelify Sans carryover only for the CuperOS/GPUSTACK identity;
- square or very lightly rounded geometry, thin borders, no glassmorphism,
  neon glow, decorative particles, gradient blobs, or default card grid;
- one high-information canvas with generous outer whitespace and strong type
  hierarchy.

## Mobile continuation

At 390 by 844, the reading order becomes:

1. question and evidence boundary;
2. semantic-depth tabs;
3. horizontally pannable causal field with an explicit overview map;
4. selected-event evidence sheet;
5. vertically stacked policy comparison;
6. horizontally scrubbed timeline.

All hover interactions have tap, focus, and keyboard equivalents. Essential
values stay on-screen. Dense raw trace content can expand, but it cannot be the
only route to the conclusion.

## Copy and data lock

The implemented screen consumes generated experiment artifacts. It must not
invent metric values in HTML or JavaScript. Until a verified E001 artifact is
generated, result cells display `not run` or `unmeasured`. Scenario facts that
are safe to display before execution are:

- three sites, 256 H100 accelerators per site;
- assumed sustained rate of 500 TFLOP/s per accelerator;
- two assumed 25 Gbit/s WAN links with 20 ms latency;
- 120 global steps, 140 GB gradient payload, and 1.12 TB checkpoint state;
- one assumed 30-second Central-site curtailment;
- three published 360M Muon observations at one-step delay;
- no evaluation observations for the multi-site transfer claim.
