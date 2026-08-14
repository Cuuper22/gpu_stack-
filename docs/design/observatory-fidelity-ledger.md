# Causal Observatory fidelity ledger

This ledger records how faithfully the built observatory follows its design
concepts, commitment by commitment. Verified 2026-07-12 in the Codex in-app
browser against the persisted E001 observatory artifact.

## Review sources

- Desktop concept: `observatory-desktop-v1.png`
- Mobile concept: `observatory-mobile-v1.png`
- Verified desktop build: `observatory-desktop-implementation-v2.png`
- Verified mobile build: `observatory-mobile-implementation-v3.png`
- Verified mobile evidence drawer: `observatory-mobile-drawer-v1.png`
- Verified mobile seed-evidence table: `observatory-mobile-evidence-v1.png`

## Comparison ledger

| Design commitment | Concept | Implemented build | Fidelity decision |
|---|---|---|---|
| Scientific-instrument visual language | Warm paper field, restrained teal/orange/cobalt/red, mono values, thin rules | Same palette, type hierarchy, evidence glyphs, rules, and low-noise surface treatment | Kept |
| Freshman-to-trace semantic depth | Three explicit depth controls | Freshman, Researcher, and Full trace alter causal prose, labels, tables, and trace exposure while preserving the same artifact | Kept and made stateful |
| Three-datacenter mental model | West, central, and east cards connected by assumed WAN links | Pannable artifact-derived site rail with exact accelerator count, power cap, bandwidth, latency, and assumption labels | Kept; decorative server imagery was replaced by schematic racks so the UI does not imply observed hardware |
| Causal story | Multi-lane field converging on learning and time-to-target | Seven canonical nodes distinguish assumed availability, unmeasured membership, modeled cadence/payload/time, an unfitted learning prior, and an unmeasured target | Strengthened; the build removes concept detail that would falsely imply implemented per-site membership control |
| Evidence inspector | Persistent desktop panel and mobile bottom sheet | Exact event/node panel with evidence class, plain meaning, controller boundary, and a closeable mobile drawer | Kept and wired to every causal target |
| Policy timeline | Compact 0 to 250 second comparison | Full artifact horizon with 1,395 event records, event-type legend, time scrubber, previous/next navigation, and accessible event lists | Expanded for research truth; the concept crop would hide most synchronous execution |
| Policy comparison | Compact mechanics/learning/falsifier matrix | Artifact-derived local-step decisions, learning-prior range or point view, inter-site bytes, projected time, partial-energy boundary, and scalar plus structured gate counts | Expanded without upgrading priors or modeled quantities into measurements |
| Uncertainty communication | Evidence classes separated visually | Toggle between intervals/limits and reported points; rounding intervals, unfitted sensitivity spans, and missing confidence intervals retain distinct language | Strengthened |
| Mobile interaction | Pannable sites, stacked causal cards, drawer, compact comparison | Site rail pans without moving the page, causal nodes open a bottom drawer, and seed observations reflow to viewport width | Kept; verified at a 390 by 844 viewport |
| Shareable state | Share control in shell | Experiment, policy, node, event, time, depth, and uncertainty persist in the URL; copy success is visibly acknowledged for five seconds and announced to assistive technology | Strengthened |
| Honest research boundary | Learning validation shown as absent | Loaded state remains `inconclusive`; held-out learning transfer, outage membership, complete energy, and mandatory evidence gates remain explicit | Kept as a non-negotiable scientific constraint |

## Human interaction checks

- Changed Freshman to Researcher to Full trace and verified the explanatory layer and URL changed together.
- Changed uncertainty from intervals to reported points and verified the comparison values collapsed from spans to points.
- Selected adaptive cadence and verified the selected policy persisted after reload.
- Used Share state and verified visible and assistive copy confirmation.
- Panned the mobile datacenter rail while the page root remained at horizontal offset zero.
- Opened Site availability into the mobile evidence drawer and closed it through the visible close control.
- Checked the mobile seed-observation table after removing document-level horizontal overflow.
