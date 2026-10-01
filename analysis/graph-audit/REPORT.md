# Equation graph audit

Date: 2026-10-01. Base commit: `7a58388`. Scripts and raw outputs are in this
folder; every number below comes from one of the `*.out.txt` files or
`sample_verdicts.csv`. Rerun any script with
`PYTHONPATH=. python analysis/graph-audit/<script>.py`.

## Short version

- The parts of the graph that the shipped scenarios actually run are mostly
  right. The two Pythia cost packs reproduce by hand to 4 digits. 6ND FLOPs for
  GPT-3 and Llama-3-405B match published values. Unit conversions on the
  economics path (kWh to W·s, carbon, demand charge, maintenance) check out
  numerically.
- Most of the graph is not on any path to a headline number. 538 of 950
  equations (57%) reach none of `econ.cost.per_token`,
  `training.tokens_per_sec`, `econ.job.dc_power` or `gpu.peak_flops`. The
  shipped scenarios execute 78 equations (8%).
- Four equations are wrong and one cites a source it does not follow. Three of
  the wrong ones are in pipeline and collective math that a reader would
  reasonably trust.
- The nuclear and quark layer has no numeric effect on anything. The
  lithography layer can only matter through pinned inputs that no preset
  drives.

## Where the graph is used (inventory.out.txt)

| Family | Equations | Feed a headline target |
|---|---:|---:|
| economics | 44 | 35 |
| training | 49 | 32 |
| gpu | 51 | 21 |
| architecture | 55 | 18 |
| parallelism | 32 | 15 |
| thermal | 42 | 24 |
| cluster | 66 | 9 |
| memory | 65 | 4 |
| kernel | 42 | 0 |
| collective | 23 | 0 |
| optimizer | 38 | 0 |
| precision | 47 | 0 |
| lithography (all layers) | 258 | 194 structurally, 0 numerically at any preset |
| **total** | **950** | **412** |

Kernel, collective, optimizer and precision equations feed nothing. The
training step time uses its own ring all-reduce (`training.eq.t_comm_dp`)
instead of the collective family, so `col.*` is a parallel copy.

Only 36 of the 412 headline-path equations cite an external work. The rest
carry a prose reference. "Every equation has a reference" is true by count but
mostly means a sentence, not a citation.

## Verdicts on a sample of 130 equations (69 on a headline path)

| Verdict | Count |
|---|---:|
| Correct | 71 |
| Correct but simplified (regime stated in csv) | 37 |
| Suspect | 17 |
| Wrong | 4 |
| Reference mismatch | 1 |

### Wrong

1. `gpu_stack/scopes/training_overheads.py:111` `training.eq.t_bubbles`. The
   pipeline bubble fraction phi = (p-1)/(p+m-1) is bubble time over *total*
   time, but it is applied as overhead over *nominal* time. At p = m = 8 the
   step-time multiplier is 1.47 instead of Narayanan et al. 2021's 1.875. Fix:
   `T_nominal * phi / (1 - phi)`. This is on the tokens-per-second path.
2. `gpu_stack/scopes/collective_gather_scatter.py:86` `col.eq.allgather_hier`.
   The inter-node bandwidth term lacks the `/ranks_per_node` factor that its
   sibling `reducescatter_hier` has, so hierarchical all-reduce is not equal to
   reduce-scatter plus all-gather inside the graph itself. It is 4.7x too
   large in the test case. Not on a headline path.
3. `gpu_stack/scopes/architecture_attention_core.py:225` `arch.eq.kv_mla`.
   DeepSeek-V2 caches one shared latent plus a decoupled RoPE key, so bytes
   per token per layer are `(d_c + d_R) * bytes`, not `2 * d_latent * bytes`.
   1.78x too large in the test case.
4. `gpu_stack/scopes/parallelism_pipeline.py:156` `par.eq.bubble_interleaved`.
   Uses an effective depth of p/v - 1 instead of (p-1)/v. Against Narayanan's
   interleaved overhead (p-1)/(v·m) it gives 0.27 vs 0.44 at p = m = 8, v = 2.
   Part of that gap is the same total-vs-overhead definition mix as item 1;
   the depth term is wrong either way.

### Reference mismatch

`gpu_stack/scopes/architecture_ffn.py:105` `flops_step_dense` cites Kaplan et
al. but uses total parameters including embeddings and no attention term. On
Pythia-70M this is 23% high; on models above ~1B parameters the difference is
under 3%.

### Suspect equations (details in sample_verdicts.csv)

- `architecture_moe.py:224, :256` active parameters omit attention and embeddings.
- `parallelism_pipeline.py:146` GPipe and 1F1B get different bubbles; Narayanan gives them the same one.
- `parallelism_batching.py:366` recompute multiplier as 1 + rho.
- `interconnect_link.py:244` queueing delay summed over packets.
- `cluster_reliability.py:279` availability output is used by nothing, though the docstring says training uses it.
- `cluster_site_aggregation.py:192` a second PUE-like constant.
- `physical_cmos_logic.py:310`, `physical_interconnect_equations.py:177`,
  `memory_dram.py:210`, `memory_sram_margin_equations.py:44`: textbook
  simplifications labeled more precisely than they are.
- Lithography: the EUV wavelength comes from a hydrogenic toy model that gives
  14.9 nm for Sn10+ (real emission is 13.5 nm).

### Suspect preset values

- `presets/hardware.py:58`, `presets/scenarios.py:123`,
  `presets/scenarios_cited_2026.py:100, 250`: training peak is the H100 FP32
  number (67 TFLOPS), not the BF16 tensor-core dense number (989 TFLOPS), and
  utilization is 100%. Effective throughput is about 6x below a realistic
  40% MFU on BF16 tensor cores, which inflates every derived time and cost.
- `presets/hardware.py:61`: NVLink 900 GB/s is the bidirectional total.
- `presets/hardware.py:62`: 80e9 bytes is 7% below 80 GiB.
- `presets/scenarios.py:127` (and cited 2026 packs): site power equals IT
  power, so PUE never enters.
- `presets/dgx_h100_tco.py:324`: demand charge added on top of an EIA average
  price that already includes it.
- `presets/dgx_h100_tco.py:213`: a 4-year life applied to the facility too.

## Lithography, nuclear and quark layers (lithography_sensitivity.out.txt)

- 260 variables and 258 equations. 194 equations sit in a headline cone
  structurally, but `gpu.peak_flops` needs 94 roots and presets assign 9 of them,
  so nothing below the pinned cut points is ever evaluated.
- Nuclear and quark terms have no numeric effect even when evaluated: medium
  mass cancels exactly in number density, and SEMF binding energy moves the
  reduced-mass factor by 4e-8. The 6 quark-count equations are in no cone.
- Recommendation: remove the 88-variable, 83-equation nuclear/quark family;
  move the plasma and atomic layers out of the core graph; keep the Rayleigh
  resolution relation k1·λ/NA with λ and NA as plain inputs.

## What to fix first

1. `training.eq.t_bubbles` (headline path, 20-30% error in pipelined runs).
2. The H100 FP32 peak in presets (changes every cited cost number).
3. `allgather_hier`, `kv_mla`, `bubble_interleaved`, the `flops_step_dense` citation.
4. Decide what to do with 538 unreachable equations: wire the collective
   family into training time, or say plainly that these are a reference
   library, not part of the model.
